# Transcript Logging Feature - Implementation Plan

## Document Status

**Status**: APPROVED - Implementation Ready
**Last Review**: 2025-01-07
**Estimated Effort**: 17-24 hours of focused development
**Reviewer**: plan-reviewer agent (architectural review)

## Overview

This document outlines the design and implementation plan for a new optional **transcript logging** feature. The transcript logs will capture the exact prompts (both system instructions and user input) sent to each participant agent at every interaction point during an experiment.

### Key Design Decisions

Following architectural review, the following key decisions were made:

1. **Instruction Capture**: ✅ KEEP with performance tradeoffs
   - Default: `include_instructions: false` (opt-in for performance)
   - When enabled: Accept 5-15% overhead for research/debugging use cases
   - User requirement explicitly requested both instructions and prompts

2. **Security**: ✅ ADD path validation
   - Prevent directory traversal attacks via `@field_validator`
   - Validate path resolvability

3. **File I/O**: ❌ SKIP async writing (initial version)
   - Synchronous writing sufficient (saves at experiment end)
   - Noted as future enhancement if blocking becomes issue

4. **Integration Strategy**: ✅ WRAPPER pattern with explicit parameters
   - `run_with_transcript_logging()` wrapper around all `Runner.run()` calls
   - Explicit `interaction_type` parameter (no implicit context mutation)
   - Protocol-compatible service integration

5. **Edge Cases**: ✅ COMPREHENSIVE coverage
   - Memory update integration detailed (Task 6.1)
   - Service protocol integration patterns (Task 5.1)
   - TwoStageVotingManager refactoring (Task 5.5)

## Requirements

### Functional Requirements
1. **Optional Feature**: Off by default, enabled via configuration
2. **Capture Scope**: Record plain string prompts sent to participant agents only (exclude utility agents)
3. **Capture Points**: All interactions where `Runner.run()` is called with participant agents
4. **Output Format**: JSON file with hierarchical structure:
   ```json
   {
     "experiment_metadata": {
       "experiment_id": "uuid",
       "timestamp": "ISO-8601",
       "config_file": "path/to/config.yaml"
     },
     "transcripts": {
       "AgentName1": {
         "call_1": {
           "phase": "phase_1",
           "round": 1,
           "interaction_type": "initial_ranking",
           "timestamp": "ISO-8601",
           "instructions": "system instructions string...",
           "input_prompt": "user prompt string..."
         },
         "call_2": { ... },
         ...
       },
       "AgentName2": { ... }
     }
   }
   ```

### Non-Functional Requirements
- **Performance**: Minimal overhead (simple string recording, no LLM calls)
- **Simplicity**: Clean integration without disrupting existing code
- **Maintainability**: Single responsibility service that can be easily tested

### Performance Considerations

**⚠️ Important: Instruction Capture Performance Tradeoffs**

When `include_instructions: true` is enabled, the transcript logger must re-generate the system instructions for each agent interaction by calling `_generate_dynamic_instructions()`. This creates a performance tradeoff:

**Overhead Details:**
- **Instruction generation** involves: memory formatting, phase detection, language localization, context assembly
- **Double evaluation**: Instructions are generated once by the SDK during execution, and once by the transcript logger for capture
- **Estimated overhead**: ~5-15% increase in total experiment runtime (depends on memory size and prompt complexity)

**Mitigation Strategies:**
1. **Default to disabled**: `include_instructions` defaults to `False` - users must explicitly opt-in
2. **Clear documentation**: Config field includes performance warning
3. **Research tradeoff**: For experiments where full prompt inspection is critical, the overhead is acceptable
4. **Future optimization**: Potential caching of instructions when context hasn't materially changed

**Recommendation**:
- For production experiments or large-scale runs: keep `include_instructions: false`
- For debugging, prompt analysis, or research: enable `include_instructions: true` with awareness of the cost

## Current Architecture Analysis

### Agent Interaction Points (Runner.run calls)

Based on code analysis, participant agents interact with the system at these points:

1. **Phase 1 (core/phase1_manager.py)**:
   - Initial ranking
   - Detailed explanation response
   - Post-explanation ranking
   - Demonstration rounds (3-4 rounds)
   - Final ranking

2. **Phase 2 (core/phase2_manager.py + services)**:
   - Discussion rounds (internal reasoning + public statements)
   - Voting initiation prompts
   - Voting confirmation
   - Secret ballot voting
   - Final ranking after results

3. **Memory Updates (experiment_agents/participant_agent.py)**:
   - Memory consolidation calls (may or may not want to log these)

4. **Voting (core/two_stage_voting_manager.py)**:
   - Principle selection
   - Amount specification (for principles 3 & 4)

### Existing Logging Infrastructure

- **AgentCentricLogger** (`utils/logging/agent_centric_logger.py`):
  - Tracks structured experiment data (rankings, decisions, outcomes)
  - Outputs to main experiment results JSON

- **ProcessFlowLogger** (`utils/logging/process_flow_logger.py`):
  - Terminal output for experiment progress
  - Not relevant for transcript logging

### Configuration System

- **ExperimentConfiguration** (`config/models.py`):
  - Pydantic models with YAML loading
  - Already has `LoggingConfig` for terminal output settings
  - New transcript config should be added here

## Proposed Architecture

### 1. Configuration Schema

Add new configuration option to `config/models.py`:

```python
class TranscriptLoggingConfig(BaseModel):
    """Configuration for transcript logging."""
    enabled: bool = Field(default=False, description="Enable transcript logging of agent prompts")
    output_path: Optional[str] = Field(
        default=None,
        description="Custom output path for transcript (default: transcript_<experiment_id>.json)"
    )
    include_memory_updates: bool = Field(
        default=False,
        description="Include memory consolidation calls in transcript"
    )
    include_instructions: bool = Field(
        default=False,
        description="Include system instructions in transcript (WARNING: adds performance overhead due to instruction re-generation)"
    )
    include_input_prompts: bool = Field(
        default=True,
        description="Include user input prompts in transcript"
    )

    @field_validator('output_path')
    @classmethod
    def validate_output_path(cls, v):
        """Validate output path for security (prevent directory traversal)."""
        if v is not None:
            path = Path(v)
            # Prevent directory traversal attacks
            if '..' in path.parts:
                raise ValueError("Path traversal not allowed in output_path")
            # Ensure path is relative or absolute but not malicious
            try:
                resolved = path.resolve()
            except Exception as e:
                raise ValueError(f"Invalid output path: {e}")
        return v

class ExperimentConfiguration(BaseModel):
    # ... existing fields ...
    transcript_logging: Optional[TranscriptLoggingConfig] = Field(
        None,
        description="Transcript logging configuration"
    )
```

Example YAML configuration:
```yaml
language: English
agents:
  - name: Alice
    personality: "Pragmatic and analytical"
    model: "gpt-4o-mini"

# ... other config ...

transcript_logging:
  enabled: true
  include_memory_updates: false  # Exclude memory updates for cleaner transcript
  output_path: "transcripts/my_experiment_transcript.json"
```

### 2. TranscriptLogger Service

Create new service: `utils/logging/transcript_logger.py`

**Responsibilities**:
- Initialize transcript data structure
- Capture agent prompts at interaction points
- Track call sequence per agent
- Write transcript to JSON file on experiment completion

**Key Methods**:
```python
class TranscriptLogger:
    def __init__(self, config: TranscriptLoggingConfig, experiment_id: str):
        """Initialize transcript logger."""

    def record_interaction(
        self,
        agent_name: str,
        phase: str,
        round_number: int,
        interaction_type: str,
        instructions: Optional[str],
        input_prompt: Optional[str],
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record a single successful agent interaction."""

    def get_next_call_number(self, agent_name: str) -> int:
        """Get next sequential call number for agent."""

    def save_transcript(self, output_path: Optional[str] = None) -> str:
        """Save transcript to JSON file."""

    def is_enabled(self) -> bool:
        """Check if transcript logging is enabled."""
```

**Data Structure**:
```python
class TranscriptInteraction(BaseModel):
    """Single interaction transcript."""
    phase: str
    round: int
    interaction_type: str
    timestamp: str
    instructions: Optional[str] = None
    input_prompt: Optional[str] = None

class AgentTranscript(BaseModel):
    """All interactions for a single agent."""
    # Dictionary with string keys (call_1, call_2, etc.)
    interactions: Dict[str, TranscriptInteraction]

class ExperimentTranscript(BaseModel):
    """Complete experiment transcript."""
    experiment_metadata: Dict[str, Any]
    transcripts: Dict[str, AgentTranscript]
```

### 3. Integration Points

#### A. FrohlichExperimentManager Initialization

In `core/experiment_manager.py`:

```python
class FrohlichExperimentManager:
    def __init__(self, config: ExperimentConfiguration, ...):
        # ... existing init ...

        # Initialize transcript logger
        transcript_config = config.transcript_logging if config.transcript_logging else TranscriptLoggingConfig()
        self.transcript_logger = TranscriptLogger(
            config=transcript_config,
            experiment_id=self.experiment_id
        )
```

#### B. Wrapper for Runner.run Calls

Create helper function to intercept and log prompts:

In `utils/logging/transcript_logger.py` or as part of the service:

```python
async def run_with_transcript_logging(
    participant: ParticipantAgent,
    prompt: str,
    context: ParticipantContext,
    transcript_logger: Optional[TranscriptLogger],
    interaction_type: str
) -> Any:
    """
    Wrapper around Runner.run that logs transcript if enabled.

    Args:
        participant: Participant agent to run
        prompt: User input prompt
        context: Participant context (contains phase, round, etc.)
        transcript_logger: Transcript logger (None if disabled)
        interaction_type: Type of interaction (e.g., "initial_ranking", "statement")

    Returns:
        Result from Runner.run
    """
    # Log transcript if enabled
    instructions = None
    if transcript_logger and transcript_logger.is_enabled():
        if transcript_logger.config.include_instructions:
            try:
                instructions = participant.get_instructions_for_context(context)
            except Exception:
                instructions = None

    # Execute original Runner.run
    result = await Runner.run(participant.agent, prompt, context=context)

    if transcript_logger and transcript_logger.is_enabled():
        input_prompt = prompt if transcript_logger.config.include_input_prompts else None
        transcript_logger.record_interaction(
            agent_name=participant.name,
            phase=context.phase.value,
            round_number=context.round_number,
            interaction_type=interaction_type,
            instructions=instructions,
            input_prompt=input_prompt
        )

    return result
```

**Challenges with Instructions Extraction**:
- Instructions are dynamically generated by `_generate_dynamic_instructions()`
- This function is called internally by the Agents SDK when running
- We need to call it ourselves to capture the instructions (creates double evaluation overhead - see Performance Considerations section)
- **Synchronization concern**: Instructions are captured pre-execution. If context mutates between capture and execution, transcript may not reflect actual instructions used. However, in practice, context is not mutated within the wrapper function, so this risk is minimal.
- **Error handling**: Instructions are captured pre-run but recording happens post-run. If Runner.run fails, the interaction is not recorded (correct behavior).

**Solution**:
Add a method to ParticipantAgent to expose instruction generation:

```python
# In experiment_agents/participant_agent.py
class ParticipantAgent:
    def get_instructions_for_context(self, context: ParticipantContext) -> str:
        """
        Get the instructions that would be generated for this context.
        Used for transcript logging.
        """
        from agents import RunContextWrapper
        # Create a wrapper to simulate what the SDK does
        wrapper = RunContextWrapper(context=context)
        # Call the instruction generator
        return _generate_dynamic_instructions(
            wrapper,
            self.agent,
            self.config,
            self.experiment_config,
            self.language_manager
        )
```

#### C. Update All Runner.run Call Sites

Replace direct `Runner.run()` calls with the transcript-aware wrapper:

**Phase 1 Manager** (`core/phase1_manager.py`):
```python
# Before:
result = await Runner.run(agent.agent, prompt, context=context)

# After:
result = await run_with_transcript_logging(
    participant=participant,
    prompt=prompt,
    context=context,
    transcript_logger=self.transcript_logger,
    interaction_type="initial_ranking"  # or appropriate type
)
```

**Phase 2 Manager** (`core/phase2_manager.py`):
- Pass transcript_logger to all services that call Runner.run
- Services update their Runner.run calls similarly

**Interaction Types to Track** (mirror existing `context.interaction_type` values):
- Phase 1: set explicit labels before each call – `initial_ranking`, `explanation`, `post_explanation_ranking`, `demonstration`, `final_ranking`; use `constraint_retry` for targeted follow-up prompts when re-validating amounts
- Phase 2 reasoning & statements: `internal_reasoning`, `statement`
- Phase 2 voting: `vote_prompt`, `vote_confirmation`, `ballot`
- Memory: `memory_update` (if enabled)

#### D. Save Transcript on Completion

In `core/experiment_manager.py`, after experiment completes:

```python
async def run_complete_experiment(self, ...):
    # ... run experiment ...

    # Save transcript if enabled
    if self.transcript_logger.is_enabled():
        transcript_path = self.transcript_logger.save_transcript()
        logger.info(f"Transcript saved to: {transcript_path}")

    return results
```

### 4. File Organization

```
utils/logging/
├── agent_centric_logger.py      # Existing: structured experiment logs
├── process_flow_logger.py       # Existing: terminal output
└── transcript_logger.py         # NEW: prompt transcript logging

config/
└── models.py                    # Update: Add TranscriptLoggingConfig

experiment_agents/
└── participant_agent.py         # Update: Add get_instructions_for_context()

core/
├── experiment_manager.py        # Update: Initialize and save transcript
├── phase1_manager.py           # Update: Use transcript wrapper
├── phase2_manager.py           # Update: Pass transcript_logger to services
└── services/
    ├── discussion_service.py    # Update: Use transcript wrapper
    ├── voting_service.py        # Update: Use transcript wrapper
    └── counterfactuals_service.py  # Update: Use transcript wrapper
```

## Implementation Plan

### Phase 1: Core Infrastructure (Estimated: 2-3 hours)

#### Task 1.1: Configuration Schema
- [x] Add `TranscriptLoggingConfig` to `config/models.py`
- [x] Add `transcript_logging` field to `ExperimentConfiguration`
- [x] Add field validators for paths and boolean combinations
- [ ] Test: Verify config loads correctly from YAML
- [ ] Test: Verify defaults work correctly

**Files to modify**:
- `config/models.py`

**Testing**:
- Unit test for config parsing with transcript enabled/disabled
- Unit test for default values

---

#### Task 1.2: TranscriptLogger Service
- [x] Create `utils/logging/transcript_logger.py`
- [x] Implement `TranscriptLogger` class with all methods
- [x] Implement Pydantic models for transcript data structures
- [x] Implement JSON serialization with proper formatting
- [x] Test: Unit tests for all methods
- [x] Test: Verify JSON output format

**Files to create**:
- `utils/logging/transcript_logger.py`
- `tests/unit/test_transcript_logger.py`

**Testing**:
- Unit test `record_interaction()` with various parameters
- Unit test `get_next_call_number()` for sequential tracking
- Unit test `save_transcript()` with custom path
- Unit test JSON output structure matches specification

---

#### Task 1.3: Instruction Extraction Support
- [x] Add `get_instructions_for_context()` method to `ParticipantAgent`
- [x] Ensure method works with existing instruction generator
- [ ] Test: Verify instructions match what SDK generates
- [ ] Handle edge cases (None context, missing language manager)

**Files to modify**:
- `experiment_agents/participant_agent.py`

**Testing**:
- Unit test instruction extraction for Phase 1 contexts
- Unit test instruction extraction for Phase 2 contexts
- Unit test instruction extraction for memory update contexts

---

### Phase 2: Integration Wrapper (Estimated: 1-2 hours)

#### Task 2.1: Transcript-Aware Runner Wrapper
- [x] Create `run_with_transcript_logging()` function
- [x] Implement instruction extraction logic
- [x] Implement prompt capture logic
- [x] Add proper error handling (transcript failure shouldn't break experiment)
- [x] Test: Verify wrapper works with transcript enabled/disabled
- [ ] Test: Verify wrapper doesn't affect experiment results

**Files to modify**:
- `utils/logging/transcript_logger.py` (or separate module)

**Testing**:
- Unit test wrapper with mock agent and transcript logger
- Unit test wrapper with transcript_logger=None
- Unit test error handling (transcript failure doesn't propagate)

---

### Phase 3: Experiment Manager Integration (Estimated: 1 hour)

#### Task 3.1: Initialize TranscriptLogger
- [x] Update `FrohlichExperimentManager.__init__()` to create transcript_logger
- [x] Pass transcript_logger to Phase1Manager
- [x] Pass transcript_logger to Phase2Manager
- [ ] Test: Verify initialization with enabled/disabled config

**Files to modify**:
- `core/experiment_manager.py`
- `core/phase1_manager.py` (constructor signature)
- `core/phase2_manager.py` (constructor signature)

**Testing**:
- Integration test: experiment manager creates transcript_logger
- Integration test: managers receive transcript_logger instance

---

#### Task 3.2: Save Transcript on Completion
- [x] Update `run_complete_experiment()` to save transcript
- [x] Generate default path if not specified (`transcript_{experiment_id}.json`)
- [x] Log transcript save location
- [ ] Test: Verify transcript file is created
- [ ] Test: Verify transcript content matches interactions

**Files to modify**:
- `core/experiment_manager.py`

**Testing**:
- Integration test: full experiment with transcript enabled
- Integration test: verify JSON file created with correct structure
- Integration test: verify transcript disabled doesn't create file

---

### Phase 4: Phase 1 Integration (Estimated: 2 hours)

#### Task 4.1: Update Phase1Manager Runner.run Calls
- [x] Introduce helper `_invoke_phase1_interaction(participant, prompt, context, interaction_type)` that sets `context.interaction_type`, routes through `run_with_transcript_logging()`, and returns the `Runner.run` result
- [x] Update `_execute_ranking_with_retry()` to call the helper for the initial run and each retry callback while preserving existing retry control flow
- [x] Update `_step_1_2_detailed_explanation()` to call the helper with `interaction_type="explanation"`
- [x] Update `_step_1_3_principle_application()` (and its retry paths) to use `interaction_type="demonstration"`, switching to `constraint_retry` for validation re-prompts
- [x] Update Phase 1 ranking entry points to pass `initial_ranking`, `post_explanation_ranking`, and `final_ranking`
- [x] Add targeted unit coverage for the new helper (mocked transcript logger)
- [ ] Test: Verify all Phase 1 interactions are captured
- [ ] Test: Verify interaction_type labels are correct (including constraint retries)

**Files to modify**:
- `core/phase1_manager.py`

**Testing**:
- Component test: Run Phase 1 with transcript enabled
- Verify all 5+ interaction types are captured per agent
- Verify call numbering is sequential (call_1, call_2, ...)

---

### Phase 5: Phase 2 Integration (Estimated: 3-4 hours)

#### Task 5.1: Pass TranscriptLogger to Services

**Protocol-Based Dependency Injection**: Phase 2 services use Protocol-based dependency injection for clean boundaries. The transcript_logger needs to integrate cleanly without violating Protocol contracts.

**Implementation Strategy**:
- [x] Add `transcript_logger: Optional[TranscriptLogger]` to service constructors (concrete implementation, not Protocol)
- [x] Store as instance variable in each service
- [x] Pass transcript_logger from Phase2Manager during service initialization (`_initialize_services()`)
- [x] Services call `run_with_transcript_logging()` wrapper at Runner.run sites
- [x] Ensure Optional type allows services to work without transcript_logger (None case)

**Code Pattern in Phase2Manager**:
```python
def _initialize_services(self):
    # ... existing code ...

    self.discussion_service = DiscussionService(
        language_manager=self.language_manager,
        settings=self.settings,
        logger=logger,
        transcript_logger=self.transcript_logger  # NEW
    )

    self.voting_service = VotingService(
        language_manager=self.language_manager,
        utility_agent=self.utility_agent,
        settings=self.settings,
        logger=logger,
        memory_service=self.memory_service,
        agent_logger=self.agent_logger,
        phase2_rounds=self.config.phase2_rounds,
        transcript_logger=self.transcript_logger  # NEW
    )

    # ... other services ...
```

**Service Constructor Pattern**:
```python
class DiscussionService:
    def __init__(
        self,
        language_manager: LanguageProvider,
        settings: Optional[Phase2Settings] = None,
        logger: Optional[Logger] = None,
        transcript_logger: Optional[TranscriptLogger] = None  # NEW
    ):
        self.language_manager = language_manager
        self.settings = settings or Phase2Settings.get_default()
        self.logger = logger
        self.transcript_logger = transcript_logger  # Store for later use
```

**Protocol Compatibility**:
- TranscriptLogger is NOT added to Protocol definitions (it's not part of service contracts)
- It's an optional internal implementation detail
- Services remain testable with mock transcript_logger or None

**Files to modify**:
- `core/phase2_manager.py` - Update `_initialize_services()` to pass transcript_logger
- `core/services/discussion_service.py` - Add constructor parameter and store
- `core/services/voting_service.py` - Add constructor parameter and store
- `core/services/counterfactuals_service.py` - Add constructor parameter and store

**Testing**:
- Unit test: services initialize with transcript_logger=None (backward compatible)
- Unit test: services initialize with mock transcript_logger
- Unit test: services store transcript_logger correctly

---

#### Task 5.2: Update Discussion Service
- [x] Locate all `Runner.run()` calls for participant agents
- [x] Replace with `run_with_transcript_logging()` wrapper
- [x] Use appropriate interaction_type labels:
  - `internal_reasoning` for reasoning phase
  - `statement` for public statement phase
- [ ] Test: Verify discussion rounds are captured

**Files to modify**:
- `core/services/discussion_service.py`
- Possibly `core/phase2_manager.py` (if discussion calls are there)

**Testing**:
- Component test: Phase 2 discussion rounds captured
- Verify both reasoning and statement prompts captured

---

#### Task 5.3: Update Voting Service
- [x] Locate voting-related `Runner.run()` calls
- [x] Replace with transcript wrapper
- [x] Use interaction_type labels `vote_prompt`, `vote_confirmation`, and `ballot`
- [x] Pass `transcript_logger` through to `TwoStageVotingManager`
- [ ] Test: Verify voting interactions captured

**Files to modify**:
- `core/services/voting_service.py`
- `core/two_stage_voting_manager.py`

**Testing**:
- Component test: voting sequence captured
- Verify all voting phases logged

---

#### Task 5.4: Update Counterfactuals Service
- [x] Update final ranking calls
- [x] Use `final_ranking` interaction type (reuse existing semantics)
- [ ] Test: Verify final rankings captured

**Files to modify**:
- `core/services/counterfactuals_service.py`

**Testing**:
- Component test: final ranking captured

---

#### Task 5.5: Update Two-Stage Voting Manager Helper

**Background**: TwoStageVotingManager uses `_run_agent()` helper method (line 991-995) that wraps Runner.run calls for voting ballots. This needs to support transcript logging.

**Implementation Strategy**:
- [x] Add `transcript_logger` parameter to TwoStageVotingManager constructor
- [x] Store as instance variable
- [x] Refactor `_run_agent` to accept `ParticipantAgent` (not just agent.agent), `interaction_type`, and use stored `transcript_logger`
- [x] Ensure all call sites pass the participant wrapper and current interaction_type while preserving `asyncio.wait_for` timeouts
- [x] Within `_run_agent`, delegate to `run_with_transcript_logging()` for centralized instruction capture
- [x] Update VotingService to pass transcript_logger when instantiating TwoStageVotingManager
- [ ] Test: Verify secret ballot flows logged end-to-end and that retries work with existing timeout semantics

**Code Pattern for TwoStageVotingManager**:
```python
class TwoStageVotingManager:
    def __init__(
        self,
        principle_name_manager,
        language_manager,
        settings,
        transcript_logger: Optional[TranscriptLogger] = None  # NEW
    ):
        self.principle_name_manager = principle_name_manager
        self.language_manager = language_manager
        self.settings = settings
        self.transcript_logger = transcript_logger  # Store

    async def _run_agent(
        self,
        participant: ParticipantAgent,  # CHANGED: was agent.agent
        prompt: str,
        context: Any,
        interaction_type: str  # NEW: explicit parameter
    ) -> Any:
        """Helper to run agent with optional transcript logging."""
        if self.transcript_logger and self.transcript_logger.is_enabled():
            return await run_with_transcript_logging(
                participant=participant,
                prompt=prompt,
                context=context,
                transcript_logger=self.transcript_logger,
                interaction_type=interaction_type
            )
        else:
            return await Runner.run(participant.agent, prompt, context=context)
```

**VotingService Integration**:
```python
# In VotingService
voting_manager = TwoStageVotingManager(
    principle_name_manager=principle_name_manager,
    language_manager=self.language_manager,
    settings=self.settings,
    transcript_logger=self.transcript_logger  # Pass through
)
```

**Call Site Updates**:
- `_conduct_principle_selection_with_retry()`: Pass participant and interaction_type="ballot"
- `_conduct_amount_specification_with_retry()`: Pass participant and interaction_type="ballot"

**Files to modify**:
- `core/two_stage_voting_manager.py` - Add constructor param, refactor _run_agent
- `core/services/voting_service.py` - Pass transcript_logger to voting manager

**Testing**:
- Component test: voting sequence captured with transcript logger
- Unit test: _run_agent with transcript_logger=None (backward compatible)
- Unit test: _run_agent with mock transcript_logger
- Integration test: verify ballot interaction_type appears in transcript

---

### Phase 6: Memory Updates (Optional, Estimated: 1 hour)

#### Task 6.1: Handle Memory Update Calls

**Background**: Memory updates use a separate code path through `ParticipantAgent.update_memory()` (line 111-140 in participant_agent.py), which internally calls `Runner.run()` with a specialized context.

**Implementation Details**:
- [ ] Modify `ParticipantAgent.update_memory()` to accept optional `transcript_logger` parameter
- [ ] Check `transcript_logger.config.include_memory_updates` before logging
- [ ] Use `run_with_transcript_logging()` wrapper if transcript enabled
- [ ] Set `interaction_type="memory_update"` explicitly
- [ ] Ensure memory context (`role_description="MemoryUpdate"`) is preserved
- [ ] Test: Verify memory updates captured when enabled
- [ ] Test: Verify memory updates excluded when disabled

**Code Pattern**:
```python
# In ParticipantAgent.update_memory()
async def update_memory(
    self,
    prompt: str,
    current_bank_balance: float = 0.0,
    # ... other params ...
    transcript_logger: Optional[TranscriptLogger] = None
) -> str:
    # ... existing context setup ...

    if transcript_logger and transcript_logger.config.include_memory_updates:
        result = await run_with_transcript_logging(
            participant=self,
            prompt=prompt,
            context=temp_context,
            transcript_logger=transcript_logger,
            interaction_type="memory_update"
        )
    else:
        result = await Runner.run(self.agent, prompt, context=temp_context)

    return result.final_output
```

**Integration Points**:
- Phase1Manager must pass `transcript_logger` to `update_memory()` calls
- Phase2Manager services (MemoryService) must pass `transcript_logger`
- Requires threading transcript_logger through memory update call chains

**Files to modify**:
- `experiment_agents/participant_agent.py` - Add transcript_logger parameter and conditional logging
- `core/phase1_manager.py` - Pass transcript_logger to memory update calls
- `core/services/memory_service.py` - Pass transcript_logger to memory update calls

**Testing**:
- Unit test: memory updates captured when include_memory_updates=true
- Unit test: memory updates excluded when include_memory_updates=false
- Integration test: verify memory updates appear in transcript with correct interaction_type

---

### Phase 7: Testing & Validation (Estimated: 2-3 hours)

#### Task 7.1: End-to-End Integration Tests
- [ ] Create integration test with transcript enabled
- [ ] Run complete experiment (Phase 1 + Phase 2)
- [ ] Verify transcript JSON structure matches specification
- [ ] Verify all interaction types are present
- [ ] Verify call numbering is correct
- [ ] Verify timestamp ordering

**Files to create**:
- `tests/integration/test_transcript_logging.py`

**Test Cases**:
1. Full experiment with transcript enabled
2. Full experiment with transcript disabled
3. Custom transcript output path
4. Memory updates included/excluded
5. Verify no impact on experiment results (transcript is read-only)

---

#### Task 7.2: Documentation
- [ ] Add configuration examples to CLAUDE.md
- [ ] Document transcript JSON schema
- [ ] Add usage examples
- [ ] Document interaction types and their meanings

**Files to modify**:
- `CLAUDE.md`

---

#### Task 7.3: Sample Configuration
- [ ] Create example config with transcript enabled
- [ ] Add to `config/` directory as reference

**Files to create**:
- `config/sample_transcript_enabled.yaml`

---

### Phase 8: Edge Cases & Polish (Estimated: 1-2 hours)

#### Task 8.1: Error Handling
- [ ] Ensure transcript failures don't break experiment
- [ ] Add try/except around transcript calls
- [ ] Log warnings if transcript fails
- [ ] Gracefully handle file write errors

**Files to review**:
- All integration points

---

#### Task 8.2: Performance Validation
- [ ] Measure overhead of transcript logging
- [ ] Ensure minimal performance impact
- [ ] Test with large experiments (many rounds, many agents)

---

#### Task 8.3: Code Review & Cleanup
- [ ] Review all changes for consistency
- [ ] Ensure naming conventions followed
- [ ] Add docstrings to all new functions
- [ ] Clean up any debug code

---

## Summary of Files to Modify/Create

### Files to Create (3 new files)
1. `utils/logging/transcript_logger.py` - Core transcript logging service
2. `tests/unit/test_transcript_logger.py` - Unit tests
3. `tests/integration/test_transcript_logging.py` - Integration tests
4. `config/sample_transcript_enabled.yaml` - Example configuration

### Files to Modify (10 files)
1. `config/models.py` - Add TranscriptLoggingConfig
2. `experiment_agents/participant_agent.py` - Add instruction extraction method, transcript support in memory updates
3. `core/experiment_manager.py` - Initialize and save transcript
4. `core/phase1_manager.py` - Replace Runner.run calls and set interaction_type where missing
5. `core/phase2_manager.py` - Pass transcript_logger to services
6. `core/services/discussion_service.py` - Replace Runner.run calls
7. `core/services/voting_service.py` - Replace Runner.run calls
8. `core/services/counterfactuals_service.py` - Replace Runner.run calls
9. `core/two_stage_voting_manager.py` - Update to pass ParticipantAgent into `_run_agent`
10. `CLAUDE.md` - Add documentation

### Files to Potentially Modify (1 file)
1. `core/two_stage_voting_manager.py` - Replace Runner.run calls (if used directly)

## Testing Strategy

### Unit Tests
- Configuration loading with various transcript settings
- TranscriptLogger methods (record, save, call numbering)
- Instruction extraction from context
- Wrapper function with mocked agents

### Component Tests
- Phase 1 complete with transcript
- Phase 2 complete with transcript
- Voting sequences with transcript
- Memory updates with transcript

### Integration Tests
- Full experiment with transcript enabled
- Verify JSON structure
- Verify all agents captured
- Verify all interaction types captured
- Verify sequential call numbering

### Performance Tests
- Measure overhead of transcript logging
- Test with large experiments

## Open Questions & Decisions

### Q1: Should we log utility agent interactions?
**Decision**: No. Focus on participant agents only. Utility agents are internal validators/parsers.

### Q2: Should we log memory update calls?
**Decision**: Make it optional via `include_memory_updates` config. Default to false for cleaner transcripts.

### Q3: Should instructions and input prompts be separately configurable?
**Decision**: Yes. Add `include_instructions` and `include_input_prompts` flags for flexibility.

### Q4: What format for timestamps?
**Decision**: ISO-8601 format for universal compatibility.

### Q5: Should we log intermediate retry attempts?
**Decision**: No. `run_with_transcript_logging()` records entries only after a successful Runner call, so retries that still fail are excluded while still allowing the caller to handle errors normally.

### Q6: Should transcript logger be passed everywhere or made global?
**Decision**: Pass as parameter (dependency injection) for testability and avoiding global state.

### Q7: Should instruction capture use post-execution hooks or pre-execution extraction?
**Decision**: Pre-execution extraction via `get_instructions_for_context()`. Accept double evaluation overhead as documented tradeoff for opt-in feature. Post-execution hooks not available in OpenAI Agents SDK.

### Q8: Should we use async file I/O for transcript saving?
**Decision**: No (initial version). Synchronous writing is sufficient since transcript saves at experiment end. Async I/O would add external dependency (`aiofiles`) without significant benefit. Noted as future enhancement if blocking becomes an issue.

### Q9: How to handle Protocol-based service integration?
**Decision**: Add `transcript_logger` as optional concrete parameter to service constructors (not part of Protocol definitions). Services remain testable with `transcript_logger=None`. Maintains Protocol contract separation.

## Success Criteria

1. ✅ Transcript logging can be enabled/disabled via YAML config
2. ✅ All participant agent interactions are captured (Phase 1, Phase 2, voting, final ranking)
3. ✅ JSON output matches specified structure
4. ✅ Instructions and prompts are correctly captured
5. ✅ Call numbering is sequential per agent
6. ✅ No impact on experiment results (transcript is read-only)
7. ✅ Acceptable performance overhead:
   - With `include_instructions: false` (default): < 2% increase in runtime
   - With `include_instructions: true`: 5-15% increase in runtime (documented tradeoff)
8. ✅ Comprehensive test coverage (unit + component + integration)
9. ✅ Clear documentation in CLAUDE.md with performance warnings

## Implementation Priorities

### Critical Path Items (Must Have)
These are essential for the feature to work:

1. **Phase 1 - Core Infrastructure** (highest priority)
   - TranscriptLoggingConfig with path validation
   - TranscriptLogger service with JSON serialization
   - Instruction extraction method in ParticipantAgent

2. **Phase 2 - Integration Wrapper** (highest priority)
   - `run_with_transcript_logging()` wrapper function
   - Error handling (transcript failure doesn't break experiments)

3. **Phase 3 - Experiment Manager** (highest priority)
   - TranscriptLogger initialization
   - Save transcript on completion

4. **Phase 4 - Phase 1 Integration** (high priority)
   - All Runner.run calls in Phase1Manager
   - Correct interaction_type labels

5. **Phase 5 - Phase 2 Integration** (high priority)
   - Service integration (DiscussionService, VotingService, CounterfactualsService)
   - TwoStageVotingManager refactoring

### Optional Items (Should Have)
These enhance the feature but aren't essential:

6. **Phase 6 - Memory Updates** (medium priority)
   - Only needed if user wants complete interaction history
   - Can be added later if initial version excludes memory updates

### Nice to Have (Could Have)
Future enhancements not in initial scope:

- Async file I/O (if blocking becomes an issue)
- Transcript diff tools
- Transcript replay functionality
- Real-time transcript streaming
- Transcript compression

### Implementation Order Rationale

**Why this order?**
1. Core infrastructure must exist before any integration
2. Wrapper pattern centralizes logic, simplifying all integration points
3. Phase 1 integration is simpler (fewer call sites, no services)
4. Phase 2 integration is more complex (service protocols, voting manager)
5. Memory updates are optional and can be added last

**Risk Mitigation Strategy:**
- Build and test incrementally (phase by phase)
- Each phase should have passing tests before moving to next
- Integration tests should be added after Phase 5 (full experiment flow)

## Risk Assessment

### High-Impact Risks

#### Risk 1: Instruction Extraction Overhead
**Severity**: Medium | **Likelihood**: High | **Impact**: Performance degradation

**Description**: Double evaluation of `_generate_dynamic_instructions()` could cause 5-15% overhead when `include_instructions: true`.

**Mitigation**:
- ✅ Default `include_instructions: false` (opt-in only)
- ✅ Document performance warning in config
- ✅ Add performance validation tests
- ✅ Users explicitly accept tradeoff when enabling

**Acceptance Criteria**: Performance overhead within documented range (5-15%) when enabled.

---

#### Risk 2: Missing Runner.run Call Sites
**Severity**: High | **Likelihood**: Medium | **Impact**: Incomplete transcripts

**Description**: If any `Runner.run()` calls are missed during integration, transcript will be incomplete.

**Mitigation**:
- ✅ Code review of all files with `Runner.run` (grep analysis already done)
- ✅ Integration tests verify all expected interaction_types appear
- ✅ Phase-by-phase testing ensures coverage
- ✅ Document all known call sites in plan

**Acceptance Criteria**: Integration test verifies presence of all expected interaction_types in transcript.

---

#### Risk 3: Context Mutation Between Capture and Execution
**Severity**: Low | **Likelihood**: Low | **Impact**: Instructions mismatch

**Description**: If context is modified between instruction capture and Runner.run execution, transcript might not reflect actual instructions.

**Mitigation**:
- ✅ Wrapper function design minimizes mutation window
- ✅ Instructions captured immediately before Runner.run
- ✅ No code between capture and execution that modifies context
- ✅ Document this as a known limitation

**Acceptance Criteria**: Manual code review confirms no context mutation in wrapper.

---

#### Risk 4: Service Protocol Integration Complexity
**Severity**: Medium | **Likelihood**: Medium | **Impact**: Integration difficulties

**Description**: Protocol-based service integration might break if transcript_logger changes Protocol contracts.

**Mitigation**:
- ✅ transcript_logger not added to Protocol definitions (concrete only)
- ✅ Optional parameter with None default maintains backward compatibility
- ✅ Services remain testable with mock transcript_logger
- ✅ Unit tests verify services work with and without transcript_logger

**Acceptance Criteria**: All existing service tests pass without modification.

---

### Medium-Impact Risks

#### Risk 5: Transcript File Write Failures
**Severity**: Low | **Likelihood**: Low | **Impact**: Lost transcript data

**Description**: Filesystem issues (permissions, disk full) could prevent transcript save.

**Mitigation**:
- ✅ Path validation in configuration
- ✅ Try/except around file write with clear error messages
- ✅ Transcript failure doesn't break experiment
- ✅ Log warning if transcript save fails

**Acceptance Criteria**: Experiment continues successfully even if transcript save fails.

---

#### Risk 6: Large Memory Usage for Long Experiments
**Severity**: Low | **Likelihood**: Medium | **Impact**: Memory exhaustion

**Description**: Storing all transcripts in memory before final save could exhaust memory in very long experiments.

**Mitigation**:
- ✅ Document as limitation for extremely long experiments
- ✅ Future enhancement: streaming writes
- ✅ For initial version, acceptable for typical experiment sizes (< 100 rounds)

**Acceptance Criteria**: Typical experiments (10-20 rounds, 5 agents) complete without memory issues.

---

### Low-Impact Risks

#### Risk 7: Timestamp Inconsistencies
**Severity**: Low | **Likelihood**: Low | **Impact**: Minor data quality issue

**Description**: System clock changes or timezone issues could create confusing timestamps.

**Mitigation**:
- ✅ Use UTC timestamps consistently
- ✅ ISO-8601 format for universal compatibility
- ✅ Document timestamp format in JSON schema

**Acceptance Criteria**: All timestamps are valid ISO-8601 UTC format.

## Timeline Estimate

**Revised timeline based on plan-reviewer feedback and additional clarifications:**

- **Phase 1 (Core Infrastructure)**: 3-4 hours
  - Configuration schema with path validation
  - TranscriptLogger service implementation
  - Instruction extraction support

- **Phase 2 (Integration Wrapper)**: 1-2 hours
  - Transcript-aware Runner wrapper
  - Error handling and performance considerations

- **Phase 3 (Experiment Manager)**: 1 hour
  - TranscriptLogger initialization
  - Save transcript on completion

- **Phase 4 (Phase 1 Integration)**: 2-2.5 hours
  - Update Phase1Manager with helper function
  - Update all Runner.run call sites

- **Phase 5 (Phase 2 Integration)**: 4-5 hours
  - Pass transcript_logger to services (Protocol-based integration)
  - Update DiscussionService
  - Update VotingService
  - Update CounterfactualsService
  - Refactor TwoStageVotingManager

- **Phase 6 (Memory Updates)**: 1.5-2 hours
  - Update ParticipantAgent.update_memory()
  - Thread transcript_logger through memory update call chains

- **Phase 7 (Testing & Validation)**: 3-4 hours
  - End-to-end integration tests
  - Unit tests for all new components
  - Documentation updates

- **Phase 8 (Edge Cases & Polish)**: 1-2 hours
  - Error handling review
  - Performance validation
  - Code review and cleanup

**Total Estimated Time**: 17-24 hours of focused development

**Note**: This is higher than the initial estimate (13-18 hours) due to:
1. Added security validation (path traversal prevention)
2. More complex service protocol integration
3. More thorough memory update integration
4. Additional documentation of performance tradeoffs
5. More comprehensive test coverage requirements

## Notes on Simplicity

This design follows the principle of simplicity:
- **Single Responsibility**: TranscriptLogger only logs prompts
- **Minimal Changes**: Uses wrapper pattern to avoid modifying core logic
- **No Overengineering**: Simple JSON output, no complex analytics
- **Optional Feature**: Zero impact when disabled
- **Clean Separation**: Transcript independent of existing AgentCentricLogger

## Quick Reference for Developers

### Files to Create (4 new files)
1. `utils/logging/transcript_logger.py` - Core service (TranscriptLogger class + wrapper function)
2. `tests/unit/test_transcript_logger.py` - Unit tests
3. `tests/integration/test_transcript_logging.py` - Integration tests
4. `config/sample_transcript_enabled.yaml` - Example configuration

### Files to Modify (10 files)
1. `config/models.py` - Add TranscriptLoggingConfig with path validator
2. `experiment_agents/participant_agent.py` - Add `get_instructions_for_context()` + transcript support in `update_memory()`
3. `core/experiment_manager.py` - Initialize transcript_logger, save on completion
4. `core/phase1_manager.py` - Replace Runner.run calls with wrapper
5. `core/phase2_manager.py` - Pass transcript_logger to services
6. `core/services/discussion_service.py` - Add transcript_logger param, replace Runner.run
7. `core/services/voting_service.py` - Add transcript_logger param, replace Runner.run
8. `core/services/counterfactuals_service.py` - Add transcript_logger param, replace Runner.run
9. `core/two_stage_voting_manager.py` - Add transcript_logger param, refactor `_run_agent()`
10. `CLAUDE.md` - Add documentation and usage examples

### Key Classes and Functions

**TranscriptLogger** (`utils/logging/transcript_logger.py`):
- `__init__(config, experiment_id)` - Initialize logger
- `record_interaction(agent_name, phase, round, interaction_type, instructions, input_prompt)` - Log interaction
- `save_transcript(output_path)` - Save to JSON file
- `is_enabled()` - Check if logging enabled

**run_with_transcript_logging()** (`utils/logging/transcript_logger.py`):
- Wrapper around `Runner.run()` that captures transcripts
- Signature: `async def run_with_transcript_logging(participant, prompt, context, transcript_logger, interaction_type)`
- Returns: Result from Runner.run

**ParticipantAgent.get_instructions_for_context()** (`experiment_agents/participant_agent.py`):
- Extracts instructions that would be generated for a context
- Used by transcript logger for instruction capture
- Returns: String of system instructions

### Configuration Example

```yaml
# Enable transcript logging
transcript_logging:
  enabled: true
  output_path: "transcripts/my_experiment.json"  # Optional, defaults to transcript_{experiment_id}.json
  include_instructions: false  # Default: false (opt-in due to performance)
  include_input_prompts: true  # Default: true
  include_memory_updates: false  # Default: false (cleaner transcripts)
```

### Integration Pattern (All Runner.run sites)

```python
# Before:
result = await Runner.run(agent.agent, prompt, context=context)

# After:
result = await run_with_transcript_logging(
    participant=agent,  # Full ParticipantAgent, not agent.agent
    prompt=prompt,
    context=context,
    transcript_logger=self.transcript_logger,
    interaction_type="initial_ranking"  # Explicit label
)
```

### Interaction Types Reference

**Phase 1**:
- `initial_ranking` - First ranking before explanation
- `explanation` - Detailed explanation response
- `post_explanation_ranking` - Ranking after explanation
- `demonstration` - Principle application rounds
- `constraint_retry` - Validation re-prompts for amounts
- `final_ranking` - Final Phase 1 ranking

**Phase 2**:
- `internal_reasoning` - Private reasoning before statement
- `statement` - Public discussion statement
- `vote_prompt` - Vote initiation prompts
- `vote_confirmation` - Voting confirmation phase
- `ballot` - Secret ballot voting
- `final_ranking` - Final ranking after results

**Memory**:
- `memory_update` - Memory consolidation (optional)

### Testing Checklist

**Unit Tests**:
- [ ] TranscriptLoggingConfig validation (including path validation)
- [ ] TranscriptLogger methods (record, save, call numbering)
- [ ] run_with_transcript_logging wrapper (with/without logger)
- [ ] ParticipantAgent.get_instructions_for_context()

**Component Tests**:
- [ ] Phase 1 complete with transcript
- [ ] Phase 2 complete with transcript
- [ ] Voting sequences with transcript
- [ ] Memory updates with transcript (if enabled)

**Integration Tests**:
- [ ] Full experiment with transcript enabled
- [ ] Verify JSON structure matches specification
- [ ] Verify all agents captured
- [ ] Verify all interaction types present
- [ ] Verify sequential call numbering
- [ ] Verify experiment runs without transcript (disabled)

### Common Pitfalls to Avoid

1. ❌ **Don't add transcript_logger to Protocol definitions** - Keep it concrete only
2. ❌ **Don't use `agent.agent` in wrapper** - Pass full `ParticipantAgent`
3. ❌ **Don't forget explicit `interaction_type`** - Don't rely only on context
4. ❌ **Don't break on transcript failure** - Wrap in try/except
5. ❌ **Don't mutate context between capture and execution** - Keep wrapper simple
6. ❌ **Don't enable `include_instructions` by default** - Performance warning

## Future Enhancements (Not in Scope)

- Transcript diff tools to compare experiments
- Transcript replay functionality
- Transcript search/filter utilities
- Real-time transcript streaming
- Transcript compression for large experiments
