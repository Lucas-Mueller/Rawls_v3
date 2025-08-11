# Logging System Overhaul Implementation Plan

## Executive Summary

The target state represents a fundamental shift from **experiment-centric** to **agent-centric** logging, capturing the complete journey of each agent through both phases with granular detail at every interaction point.

## Current vs Target State Analysis

### Current State Issues
- **High-level aggregation**: Focuses on experiment summary rather than detailed agent interactions
- **Missing granular memory tracking**: No capture of memory state changes between rounds
- **Limited Phase 2 detail**: Minimal tracking of discussion rounds and internal reasoning
- **Experiment-centric structure**: Data organized by phases, not by individual agent experiences
- **No confidence tracking**: Missing confidence levels throughout the experiment
- **Limited round-by-round state**: Bank balances and outcomes not captured at each step

### Target State Benefits
- **Agent-centric perspective**: Complete individual agent journey from start to finish
- **Memory state tracking**: Captures `memory_coming_in_this_round` at every interaction
- **Internal vs Public separation**: Distinguishes internal reasoning from public messages in Phase 2
- **Granular confidence tracking**: Captures confidence levels at each decision point
- **Round-by-round state preservation**: Bank balances, payoffs, and outcomes at every step
- **Enhanced Phase 2 detail**: Discussion rounds with speaking order, voting mechanics

## Implementation Strategy

### Phase 1: Data Model Enhancement

#### 1.1 Create New Logging Models (`models/logging_types.py`)
```python
# Agent-centric logging structures matching target_state.json
class AgentPhase1Logging(BaseModel):
    initial_ranking: InitialRankingLog
    detailed_explanation: DetailedExplanationLog  
    ranking_2: PostExplanationRankingLog
    demonstrations: List[DemonstrationRoundLog]
    ranking_3: FinalRankingLog

class AgentPhase2Logging(BaseModel):
    rounds: List[DiscussionRoundLog]
    post_group_discussion: PostDiscussionLog

class AgentExperimentLog(BaseModel):
    name: str
    model: str
    temperature: float
    personality: str
    reasoning_enabled: bool
    phase_1: AgentPhase1Logging
    phase_2: AgentPhase2Logging
```

#### 1.2 Round-Level Logging Models
```python
class BaseRoundLog(BaseModel):
    memory_coming_in_this_round: str
    bank_balance: float

class DemonstrationRoundLog(BaseRoundLog):
    number_demonstration_round: int
    choice_principal: str
    class_put_in: str
    payoff_received: float
    payoff_if_other_principles: str
    bank_balance_after_round: float

class DiscussionRoundLog(BaseRoundLog):
    number_discussion_round: int
    speaking_order: int
    internal_reasoning: str
    public_message: str
    initiate_vote: str
    favored_principle: str
```

### Phase 2: Logging Infrastructure Replacement

#### 2.1 Agent-Centric Logger (`utils/agent_centric_logger.py`)
- Replace `ExperimentLogger` with `AgentCentricLogger`
- Implement incremental logging during experiment execution
- Maintain in-memory agent logs during experiment run
- Serialize to target JSON structure at completion

#### 2.2 Memory State Capture Enhancement
```python
class MemoryStateCapture:
    @staticmethod
    async def capture_pre_round_state(
        participant: ParticipantAgent,
        context: ParticipantContext,
        round_type: str
    ) -> str:
        """Capture memory state coming into each round"""
        return context.memory
    
    @staticmethod
    async def log_round_completion(
        agent_log: AgentExperimentLog,
        round_data: BaseRoundLog
    ):
        """Log completed round data to agent's log"""
```

### Phase 3: Phase Manager Integration

#### 3.1 Phase 1 Manager Logging Enhancement (`core/phase1_manager.py`)
**Key Changes:**
- Initialize agent logging structure at start of Phase 1
- Capture memory state before each major step
- Log detailed outcomes for each demonstration round
- Separate initial ranking, post-explanation ranking, and final ranking logs

**Implementation Points:**
- `_step_1_1_initial_ranking()`: Log initial ranking with confidence and memory state
- `_step_1_2_detailed_explanation()`: Log explanation processing and memory update
- `_step_1_3_principle_application()`: Log each demonstration round with full detail
- `_step_1_4_final_ranking()`: Log final ranking with experience-based reasoning

#### 3.2 Phase 2 Manager Logging Enhancement (`core/phase2_manager.py`)
**Key Changes:**
- Log each discussion round with speaking order
- Separate internal reasoning from public messages  
- Track vote initiation and favored principles
- Capture post-group discussion state

**Implementation Points:**
- `_get_participant_statement()`: Split internal reasoning from public message
- `_conduct_group_vote()`: Log voting process and outcomes
- `_collect_final_rankings()`: Log post-discussion state and final rankings

### Phase 4: Experiment Manager Integration

#### 4.1 Replace Logging System (`core/experiment_manager.py`)
```python
class FrohlichExperimentManager:
    def __init__(self, config: ExperimentConfiguration):
        # Replace ExperimentLogger with AgentCentricLogger
        self.agent_logger = AgentCentricLogger()
        
    async def run_complete_experiment(self) -> ExperimentResults:
        # Initialize agent logs at experiment start
        self.agent_logger.initialize_experiment(self.participants, self.config)
        
        # Phase execution with integrated logging
        phase1_results = await self.phase1_manager.run_phase1_with_logging(
            self.config, self.agent_logger
        )
        phase2_results = await self.phase2_manager.run_phase2_with_logging(
            self.config, phase1_results, self.agent_logger
        )
        
        # Generate target state JSON structure
        return self.agent_logger.generate_final_results()
```

### Phase 5: Output Format Transformation

#### 5.1 Target JSON Structure Generator
```python
class TargetStateGenerator:
    @staticmethod
    def generate_target_structure(
        agent_logs: List[AgentExperimentLog],
        general_info: GeneralExperimentInfo
    ) -> Dict[str, Any]:
        """Convert agent logs to target_state.json format"""
        return {
            "general_information": {
                "consensus_reached": general_info.consensus_reached,
                "consensus_principle": general_info.consensus_principle,
                "public_conversation_phase_2": general_info.public_conversation,
                "final_vote_results": general_info.final_vote_results,
                "config_file_used": general_info.config_file_used
            },
            "agents": [
                agent_log.to_target_format() for agent_log in agent_logs
            ]
        }
```

## Implementation Timeline & Dependencies

### Week 1: Foundation
- [ ] Create new logging data models (`models/logging_types.py`)
- [ ] Implement `AgentCentricLogger` class
- [ ] Create memory state capture utilities
- [ ] Update core dependencies and imports

### Week 2: Phase Manager Integration  
- [ ] Enhance Phase 1 Manager with granular logging
- [ ] Enhance Phase 2 Manager with discussion round logging
- [ ] Implement internal reasoning vs public message separation
- [ ] Add confidence level tracking throughout

### Week 3: Experiment Manager & Output
- [ ] Replace experiment manager logging system
- [ ] Implement target JSON structure generation
- [ ] Create backward compatibility layer (optional)
- [ ] Update result serialization and file output

### Week 4: Testing & Validation
- [ ] Unit tests for new logging models
- [ ] Integration tests comparing old vs new output structures
- [ ] Performance testing with memory state capture
- [ ] End-to-end validation of target JSON format

## Risk Mitigation

### Performance Considerations
- **Memory overhead**: Storing detailed memory states for each round may increase memory usage
- **Solution**: Implement configurable logging levels (minimal, standard, detailed)

### Backward Compatibility
- **Breaking changes**: New JSON structure incompatible with existing analysis tools
- **Solution**: Maintain dual output option during transition period

### Data Validation
- **Schema validation**: Ensure target JSON structure matches expected format
- **Solution**: Implement Pydantic validators and comprehensive test coverage

## Success Criteria

1. **Structural Match**: Output JSON exactly matches target_state.json structure
2. **Data Completeness**: All agent interactions captured with full context
3. **Memory Continuity**: Memory states properly tracked across phases
4. **Performance**: <10% performance degradation from enhanced logging
5. **Test Coverage**: >90% test coverage for new logging system

## Post-Implementation Benefits

1. **Enhanced Analysis**: Agent-centric view enables deeper behavioral analysis
2. **Memory Research**: Detailed memory tracking supports memory management studies  
3. **Process Transparency**: Complete audit trail of agent decision-making
4. **Debugging Capability**: Granular logging improves troubleshooting
5. **Research Extensibility**: Rich data structure supports future research directions

---

*This plan provides a systematic approach to transform the current experiment-centric logging into the desired agent-centric detailed logging system while maintaining system stability and performance.*