# Phase2Manager Refactoring Plan

## Executive Summary

The current `Phase2Manager` is a 2000+ line monolithic class that violates the Single Responsibility Principle and suffers from reduced readability, high regression risk, and poor unit testability. This plan details a comprehensive refactoring approach to break it into focused, testable modules while maintaining all existing functionality.

## Current State Analysis

### Identified Responsibilities

The current `Phase2Manager` handles 11 distinct responsibilities:

1. **Topic/Discussion Prompts** (`_build_discussion_prompt`, `_build_internal_reasoning_prompt` - Lines 1537-1567)
2. **Retry Logic & Exponential Backoff** (`_get_participant_statement_with_retry` - Lines 196-336) 
3. **Input Validation** (Statement/constraint validation - Lines 139-195)
4. **Speaking Order Strategy** (`_generate_speaking_order` - Lines 759-835)
5. **Voting Initiation Prompts** (`_prompt_for_vote_initiation` - Lines 917-1019)
6. **Confirmation Phase Management** (`_conduct_confirmation_phase` - Lines 1646-1801) 
7. **Secret Ballot Coordination** (`_conduct_secret_ballot_phase` - Lines 1803-1897)
8. **Consensus Detection Orchestration** (`_handle_complex_voting_mode` - Lines 1570-1644)
9. **Logging & Statistics** (Various logging methods - Lines 63-194)
10. **Counterfactual Calculation** (`_calculate_phase2_counterfactuals` - Lines 1214-1258)
11. **Memory Management & Updates** (`_collect_final_rankings`, memory operations - Lines 1360-1464)

### Key Problems

- **Readability**: 2000+ line file difficult to navigate and understand
- **Regression Risk**: Changes to one concern can break unrelated functionality
- **Testing**: Impossible to unit test individual concerns in isolation
- **Maintenance**: Bug fixes and enhancements require modifying a massive class
- **Performance**: Loading and instantiating a huge class impacts startup time

## Target Architecture: Focused Services

### Core Principle: Cohesive Services, Not Over-Fragmentation

Based on critical feedback, we target **5 new services** plus composition of the existing `TwoStageVotingManager` instead of 11 fragmented classes. This reduces integration complexity while achieving 80% of the benefits with much lower risk.

### Revised Service Structure

**5 new services** that compose the existing `TwoStageVotingManager`:

```
Phase2Manager (Orchestrator - ~200 lines)
├── DiscussionService (prompts, statements, validation, retry)
├── VotingService (initiation, confirmation, composes TwoStageVotingManager)  
├── SpeakingOrderService (all order strategies and finisher rules)
├── MemoryService (discussion/vote/result deltas, uniform updates)
└── CounterfactualsService (payoffs, alternatives, detailed results)

Composed dependency:
└── TwoStageVotingManager (existing - no changes needed)
```

### Service Specifications with Precise Interfaces

#### 1. DiscussionService
**Responsibility**: Discussion prompts, statement collection with validation/retry
```python
class DiscussionService:
    def __init__(self, language_manager: LanguageProvider, settings: Phase2Settings):
        self.language_manager = language_manager
        self.settings = settings
    
    def build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int, 
                               max_rounds: int, internal_reasoning: str = "") -> str:
        """Build localized discussion prompt with history and group composition."""
    
    def build_internal_reasoning_prompt(self, discussion_state: GroupDiscussionState, round_num: int, 
                                      max_rounds: int) -> str:
        """Build prompt for internal reasoning before public statement."""
    
    def get_participant_statement_with_retry(self, participant: ParticipantAgent, context: ParticipantContext,
                                           discussion_state: GroupDiscussionState, agent_config: AgentConfiguration,
                                           max_retries: int = None) -> tuple[str, str, dict]:
        """
        Get statement with exponential backoff retry.
        Returns: (statement, internal_reasoning, tool_call_metadata)
        Reuses existing timeout/backoff policy from settings.
        """
    
    def validate_statement(self, statement: str, participant_name: str, language: str) -> bool:
        """Reuses existing _validate_statement logic with language-aware min length."""
    
    def format_group_composition(self, participant_names: List[str]) -> str:
        """Format localized group composition message."""
```
**Realistic Size**: ~350 lines (prompt building + retry logic + validation + i18n)

#### 2. VotingService  
**Responsibility**: Vote initiation, confirmation, ballot coordination via TwoStageVotingManager
```python
class VotingService:
    def __init__(self, language_manager: LanguageProvider, utility_agent: UtilityAgent, 
                 settings: Phase2Settings):
        self.two_stage_manager = TwoStageVotingManager(...)  # Compose existing
    
    def prompt_for_vote_initiation(self, participant: ParticipantAgent, context: ParticipantContext,
                                  recent_statement: str = None, max_retries: int = 3) -> bool:
        """Enhanced vote initiation with statement context and numeric detection."""
    
    def conduct_confirmation_phase(self, initiator_name: str, initiation_statement: str,
                                  contexts: List[ParticipantContext]) -> bool:
        """Public confirmation phase - all must agree to proceed to ballot."""
    
    def conduct_voting_process(self, initiator: ParticipantAgent, contexts: List[ParticipantContext],
                              discussion_state: GroupDiscussionState) -> bool:
        """
        Complete voting: confirmation → secret ballot → consensus detection.
        Returns: True if consensus reached.
        Updates: discussion_state.vote_history, discussion_state._consensus_result
        Writes: Formatted messages to discussion_state.public_history
        """
    
    def announce_consensus_result(self, vote_result: VoteResult, discussion_state: GroupDiscussionState) -> None:
        """Format and append localized consensus/no-consensus message to public history."""
```
**Realistic Size**: ~550 lines (initiation + confirmation + coordination + error handling)

#### 3. SpeakingOrderService
**Responsibility**: All speaking order strategies with deterministic finisher rules  
```python
class SpeakingOrderService:
    def __init__(self, seed_manager: Optional[SeedManager] = None):
        self.seed_manager = seed_manager  # For reproducible randomness
    
    def generate_speaking_order(self, round_num: int, num_participants: int, strategy: str,
                               last_round_finisher: Optional[int] = None) -> List[int]:
        """
        Generate speaking order with finisher restriction.
        Strategy: 'fixed', 'random', 'conversational'
        Returns: List of participant indices (0-based)
        """
    
    def apply_finisher_restriction(self, order: List[int], last_finisher: int, 
                                  num_participants: int) -> List[int]:
        """Apply restriction: if round N ends with Agent X, round N+1 cannot start with Agent X."""
```
**Realistic Size**: ~120 lines (strategies + finisher logic + edge cases)

#### 4. MemoryService
**Responsibility**: Unified memory management with truncation and consistent guidance
```python  
class MemoryService:
    def __init__(self, language_manager: LanguageProvider, utility_agent: UtilityAgent,
                 config: ExperimentConfiguration):
        self.config = config
        self.statement_max_chars = 300  # Hard truncation limit
        self.reasoning_max_chars = 200   # Hard truncation limit
    
    def update_memory_selective(self, agent: ParticipantAgent, context: ParticipantContext,
                               content: str, event_type: MemoryEventType, 
                               event_metadata: dict = None) -> str:
        """
        Single entry point replacing SelectiveMemoryManager.update_memory_selective.
        Handles pre-truncation and consistent guidance style application.
        """
    
    def update_all_memories_for_voting_phase(self, contexts: List[ParticipantContext], 
                                            phase_name: str, additional_info: str = "",
                                            initiator_name: str = None) -> None:
        """Update all participant memories for voting phase transitions."""
    
    def apply_content_truncation(self, content: str, content_type: str) -> str:
        """Apply truncation: statements ≤300 chars, reasoning ≤200 chars."""
```
**Realistic Size**: ~280 lines (unified updates + truncation + error handling)

#### 5. CounterfactualsService
**Responsibility**: Payoff application and counterfactual analysis
```python
class CounterfactualsService:  
    def __init__(self, language_manager: LanguageProvider):
        self.language_manager = language_manager
    
    def apply_group_principle_and_calculate_payoffs(self, discussion_result: GroupDiscussionResult,
                                                   config: ExperimentConfiguration) -> tuple[Dict[str, float], Dict[str, str], Dict[str, Dict[str, float]]]:
        """
        Exact contract match: returns (payoffs, assigned_classes, alternative_earnings_by_agent)
        Handles consensus vs random assignment logic.
        """
    
    def calculate_phase2_counterfactuals(self, distribution_set, assigned_classes: Dict[str, str],
                                        consensus_principle: Optional[PrincipleChoice] = None,
                                        constraint_amount: Optional[int] = None) -> Dict[str, Dict[str, float]]:
        """Calculate alternative earnings under all 4 principles for transparency."""
    
    def build_detailed_results(self, participant_name: str, final_earnings: float, assigned_class: str,
                              alternative_earnings: Dict[str, float], consensus_result: GroupDiscussionResult) -> str:
        """Build Phase 2 results with counterfactual table (matching Phase 1 transparency)."""
    
    def collect_final_rankings(self, contexts: List[ParticipantContext], discussion_result: GroupDiscussionResult,
                              payoff_results: Dict[str, float], assigned_classes: Dict[str, str],
                              alternative_earnings: Dict[str, Dict[str, float]], config: ExperimentConfiguration,
                              logger: AgentCentricLogger = None) -> Dict[str, PrincipleRanking]:
        """Collect final rankings with enhanced transparency handling."""
```
**Realistic Size**: ~380 lines (payoff logic + counterfactuals + detailed formatting + final rankings)

### Interface Implementation Notes

**Truncation Policy**: 
- Applied **pre-translation** in MemoryService.apply_content_truncation()  
- Statement truncation: 300 chars (preserves meaning while preventing memory bloat)
- Reasoning truncation: 200 chars (internal reasoning less critical for memory continuity)

**Determinism & Reproducibility**:
- SpeakingOrderService uses seed_manager.random for reproducible randomness
- Finisher restriction applied consistently: round N finisher cannot start round N+1
- Conversational order uses weighted selection excluding last finisher

**VotingService Public History Management**:  
- VotingService **directly writes** formatted messages to discussion_state.public_history
- Uses language_manager for localized consensus/no-consensus announcements
- No separate announcer helper - keeps voting logic consolidated

**MemoryService API Design**:
- Single entry point: update_memory_selective() replaces all SelectiveMemoryManager calls
- Handles event_type routing internally (MemoryEventType.DISCUSSION_STATEMENT, etc.)
- Applies truncation + guidance style consistently across all memory updates

**CounterfactualsService Contract Preservation**:
- apply_group_principle_and_calculate_payoffs() maintains exact return signature: 
  tuple[Dict[str, float], Dict[str, str], Dict[str, Dict[str, float]]]
- No ripple effects to existing payoff handling in Phase2Results
- DistributionSet input/output contracts preserved

### Refactored Phase2Manager (Orchestrator)

The new `Phase2Manager` will be a lean orchestrator (~200 lines) that:

```python
class Phase2Manager:
    def __init__(self, participants, utility_agent, config, language_manager, error_handler, seed_manager):
        # Initialize focused services with minimal interfaces
        self.discussion_service = DiscussionService(language_manager, config.phase2_settings)
        self.voting_service = VotingService(language_manager, utility_agent, config.phase2_settings)
        self.speaking_order_service = SpeakingOrderService(seed_manager)
        self.memory_service = MemoryService(language_manager, utility_agent, config)
        self.counterfactuals_service = CounterfactualsService(language_manager)
        
        # Keep existing integrations
        self.participants = participants
        self.utility_agent = utility_agent
        self.error_handler = error_handler
        
    async def run_phase2(self, config, phase1_results, logger) -> Phase2Results:
        # Clean orchestration - delegate to services
        contexts = self._initialize_phase2_contexts(phase1_results, config)
        discussion_result = await self._run_group_discussion(config, contexts, logger)
        payoffs = await self.counterfactuals_service.apply_group_principle_and_calculate_payoffs(discussion_result, config)
        final_rankings = await self.counterfactuals_service.collect_final_rankings(contexts, discussion_result, payoffs, config, logger)
        return Phase2Results(discussion_result, payoffs, final_rankings)
    
    async def _run_group_discussion(self, config, contexts, logger) -> GroupDiscussionResult:
        # Orchestrate discussion rounds using services
        for round_num in range(1, config.phase2_rounds + 1):
            speaking_order = self.speaking_order_service.generate_speaking_order(round_num, contexts, config, last_finisher)
            
            for participant_idx in speaking_order:
                # Get statement via DiscussionService
                statement, reasoning, tool_info = await self.discussion_service.get_participant_statement_with_retry(
                    self.participants[participant_idx], contexts[participant_idx], discussion_state, config.agents[participant_idx]
                )
                
                # Update memory via MemoryService  
                contexts[participant_idx].memory = await self.memory_service.update_discussion_memory(
                    self.participants[participant_idx], contexts[participant_idx], statement, round_num
                )
                
                # Check for voting via VotingService
                consensus_reached = await self.voting_service.conduct_voting_process(
                    self.participants[participant_idx], contexts, discussion_state
                )
                if consensus_reached:
                    return discussion_state._consensus_result
```

### Key Improvements Over Original Plan

**Reduced Complexity**: 6 cohesive services instead of 11 fragmented classes
**Clear Ownership**: Each service owns a complete concern area  
**Existing Integration**: Composes `TwoStageVotingManager` instead of replacing it
**Minimal Interfaces**: Services receive only what they need, not entire Phase2Manager
**Practical Sizing**: Services range 100-400 lines each - manageable and testable

## Practical Implementation Strategy (MVP Approach)

### Migration Toggle & Acceptance Criteria

**Configuration Flag**: `phase2.refactored_services_enabled = {false|true}` (default: false)
**Performance Thresholds**: 
- Wall-clock time: max +25% increase 
- LLM calls: max +30% increase in full-memory mode
- Memory updates: max +20% increase

**Metrics to Add**:
- `memory_update_calls_phase2_total`
- `memory_update_seconds_total` 
- `memory_update_failures_total`

### Iteration 1: Foundation (1-2 days)
**Focus**: Pure, low-risk extractions
1. Extract `SpeakingOrderService` (pure logic, ~100 lines)
2. Create `DiscussionService` with prompt building methods
3. Add retry utility functions (not a class)
4. Fix backoff logging bug: log before multiplying delay
5. Add statement/reasoning truncation (300/200 chars) in memory deltas

**Validation**: Golden test for prompts across EN/ES/ZH languages

### Iteration 2: Voting Consolidation (2-3 days)  
**Focus**: Unify all voting logic in one service
1. Create `VotingService` that owns:
   - Vote initiation prompts with numeric detection
   - Confirmation phase logic  
   - Composition of existing `TwoStageVotingManager`
   - Consensus result announcement
2. Add metrics around voting flow (initiation attempts, confirmation retries)
3. Remove voting prompts from Phase2Manager

**Validation**: Contract tests for voting inputs/outputs including edge cases

### Iteration 3: Memory Unification (2-3 days)
**Focus**: Single consistent memory handling
1. Create `MemoryService` that handles:
   - Discussion memory updates with consistent guidance style
   - Vote initiation/confirmation memory updates  
   - Final results memory updates
   - Truncation rules and error handling
2. Add config: `phase2.memory_updates_mode = {selective|full}` (default: selective)
3. Replace all SelectiveMemoryManager calls with MemoryService

**Validation**: Memory content consistency tests with current behavior

### Iteration 4: Payoffs & Finalization (2-3 days)
**Focus**: Complete remaining extraction
1. Create `CounterfactualsService` for:
   - Payoff application logic
   - Alternative earnings calculations  
   - Detailed results formatting
   - Final rankings collection
2. Update Phase2Manager to orchestrator pattern using services
3. Full regression testing and performance validation

**Validation**: End-to-end tests with consensus and non-consensus scenarios

## Risk Mitigation & Dependencies

### Avoiding Over-Engineering Pitfalls

**No Circular Dependencies**: Services never reference Phase2Manager or each other directly
**Minimal Interfaces**: Use Protocol types for language_manager, utility_agent dependencies
**Keep Retry Simple**: Use utility functions, not a RetryStrategyManager class
**Preserve TwoStageVotingManager**: Compose, don't replace existing working components

### Dependency Management with Protocol Interfaces

```python
from typing import Protocol, Optional, List, Dict, Any

# Minimal interface contracts to reduce coupling
class LanguageProvider(Protocol):
    def get(self, key: str, **kwargs) -> str

class UtilityProvider(Protocol):  
    def detect_numerical_agreement(self, response: str) -> tuple[bool, Optional[str]]
    def parse_principle_ranking_enhanced(self, text_response: str) -> PrincipleRanking

class VotingBackend(Protocol):
    def conduct_full_voting_process(self, contexts: List[ParticipantContext], 
                                   state: GroupDiscussionState) -> Optional[VoteResult]

class MemoryUpdater(Protocol):
    def update_memory_selective(self, agent: ParticipantAgent, context: ParticipantContext,
                               content: str, event_type: MemoryEventType, **kwargs) -> str

# Services depend on protocols, not concrete classes  
class VotingService:
    def __init__(self, language_manager: LanguageProvider, utility_agent: UtilityProvider,
                 voting_backend: VotingBackend, settings: Phase2Settings):
        # Clean dependency injection
```

### Technical Risks

**Risk**: Breaking existing functionality during refactoring
- **Mitigation**: Feature flag allows instant rollback to current implementation
- **Mitigation**: Contract tests validate inputs/outputs match current behavior  
- **Mitigation**: Golden tests for prompts prevent i18n drift

**Risk**: Performance degradation
- **Mitigation**: Hard performance thresholds with automated monitoring
- **Mitigation**: Focus on runtime behavior (LLM calls, timeouts) not startup time
- **Mitigation**: Memory service reduces SelectiveMemoryManager overhead

**Risk**: Integration complexity with 5 services
- **Mitigation**: Services initialized once in Phase2Manager.__init__
- **Mitigation**: Clear data flow: contexts flow through services, no sharing
- **Mitigation**: Each service 100-400 lines - manageable and testable

## Testing Strategy

### Service-Level Unit Tests

Each service gets focused unit tests for its core responsibilities:

```python
# test_discussion_service.py
class TestDiscussionService:
    def test_build_discussion_prompt_with_history(self):
        # Test prompt building with previous discussion
        
    def test_validate_statement_cjk_languages(self):  
        # Test CJK minimum length validation
        
    def test_retry_with_exponential_backoff(self):
        # Test retry logic with proper delay calculation

# test_voting_service.py  
class TestVotingService:
    def test_initiation_prompt_with_recent_statement(self):
        # Test vote prompting with context
        
    def test_confirmation_phase_auto_confirm_initiator(self):
        # Test initiator auto-confirmation logic
        
    def test_compose_two_stage_voting_manager(self):
        # Test integration with existing TwoStageVotingManager

# test_memory_service.py
class TestMemoryService:
    def test_unified_memory_updates_selective_mode(self):
        # Test memory updates in selective mode
        
    def test_memory_truncation_character_limits(self):
        # Test truncation with statement/reasoning limits
```

### Golden Tests & Contract Testing

Prevent regression in key areas:

```python
class TestPhase2Contracts:
    def test_prompt_content_across_languages(self):
        # Golden test: snapshot prompts for EN/ES/ZH
        
    def test_memory_delta_format_consistency(self):
        # Contract test: memory delta format matches current
        
    def test_voting_result_structure(self):
        # Contract test: vote results match current GroupDiscussionResult
```

### Integration & Performance Testing

```python
class TestPhase2Integration:
    def test_full_phase2_with_feature_flag_disabled(self):
        # Test current implementation still works
        
    def test_full_phase2_with_feature_flag_enabled(self):  
        # Test refactored implementation matches behavior
        
    def test_performance_within_thresholds(self):
        # Validate <25% wall-clock, <30% LLM calls increase
```

## What Remains in Phase2Manager

After refactoring, Phase2Manager becomes a focused orchestrator handling only:

- **Service initialization and dependency injection**
- **High-level flow orchestration**: init contexts → discussion rounds → payoffs → final rankings  
- **Cross-service coordination**: passing contexts and results between services
- **Error handling and logging coordination** at the orchestration level

**No longer contains**:
- Prompt building logic (DiscussionService)
- Statement validation or retry logic (DiscussionService)  
- Voting prompts or confirmation logic (VotingService)
- Memory update implementations (MemoryService)
- Payoff calculations (CounterfactualsService)
- Speaking order strategies (SpeakingOrderService)

## Small Fixes to Carry Along

**Translation Issues**:
- Add missing English key for no-consensus: `"phase2_no_consensus"`
- Fix income class labels to use `common.income_classes.*` consistently

**Logging Issues**: 
- Fix backoff logging: log delay before multiplying by factor
- Remove tool-call remnants where no longer applicable

**Memory Issues**:
- Add statement truncation (≤300 chars) in memory deltas
- Add reasoning truncation (≤200 chars) in memory deltas

## Benefits of Revised Architecture

### Practical Benefits
- **5 focused services** (120-550 lines each) instead of 1 monolithic class (2000+ → 200 lines orchestrator)
- **Clear ownership** of concerns with no cross-cutting dependencies
- **Existing integration preserved** - composes TwoStageVotingManager without changes
- **Incremental rollout** via feature flag with performance monitoring
- **Precise contracts** - exact return types prevent integration issues

### Development Benefits  
- **Unit testable components** - mock interfaces instead of entire Phase2Manager
- **Isolated bug fixes** - voting issues don't require touching memory logic
- **Faster onboarding** - developers can understand one service at a time
- **Parallel development** - different services can be worked on independently

## Implementation Timeline (Revised)

**Total Duration**: 10-12 days (adjusted for realistic service sizing)
**Resource Requirements**: 1 developer with Phase 2 domain knowledge

| Iteration | Duration | Focus Area | Lines Changed | Success Criteria |
|-----------|----------|------------|---------------|-----------------|
| 1 | 2-3 days | Foundation | ~470 lines | SpeakingOrderService (120) + DiscussionService (350) + retry utilities |
| 2 | 3-4 days | Voting consolidation | ~550 lines | VotingService with TwoStageVotingManager composition + contract tests |  
| 3 | 2-3 days | Memory unification | ~280 lines | MemoryService replacing SelectiveMemoryManager calls + truncation |
| 4 | 3-4 days | Payoffs + orchestration | ~580 lines | CounterfactualsService (380) + Phase2Manager refactor (200) |

**Note**: Timeline extended to account for realistic service complexity based on actual code analysis.

## Conclusion

This revised refactoring plan addresses all identified issues with the overloaded `Phase2Manager` through a **pragmatic 5-service architecture** that avoids over-engineering while delivering substantial benefits.

### Key Plan Improvements Based on Feedback

**Reduced Complexity**: 5 new services + composition of existing TwoStageVotingManager (not 11 fragmented classes)
**Realistic Sizing**: Services accurately sized at 120-550 lines each based on actual code analysis
**Focused Scope**: 8-10 days implementation (not 7 weeks)  
**Practical Approach**: Feature flag + performance thresholds + incremental validation
**Preserved Integration**: Composes existing TwoStageVotingManager instead of replacing
**Precise Interfaces**: Type-safe contracts with exact return types and parameter specifications

### Expected Outcomes

**Immediate Benefits**:
- Phase2Manager: 2000+ lines → 200 lines clean orchestrator
- Isolated testing: Mock service interfaces vs entire monolith
- Parallel development: Services can be worked on independently
- Faster debugging: Bug isolation within service boundaries

**Long-term Benefits**:
- Reduced regression risk from changes
- Easier feature development and maintenance  
- Better onboarding for new developers
- Foundation for future Phase 2 enhancements

### Risk Management

The plan emphasizes **risk reduction** through:
- Feature flag for instant rollback capability
- Hard performance thresholds with automated monitoring
- Contract tests to prevent behavior regression
- Incremental validation at each iteration step

This pragmatic approach delivers **80% of the architectural benefits** with **20% of the risk** compared to a comprehensive rewrite, making it an ideal candidate for implementation.