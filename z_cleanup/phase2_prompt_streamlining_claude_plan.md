# Phase 2 Prompt Streamlining: Systems-Level Plan

**Author**: Claude Code (Assistant)
**Date**: 2025-10-01
**Status**: Proposed Design
**Builds On**: phase2_prompt_streamlining_plan.md and phase2_prompt_streamlining_plan_review.md

---

## Executive Summary

This plan eliminates hidden coupling in Phase 2 prompt construction through **minimal, surgical changes** that preserve the services-first architecture. The core improvement: replace the `_current_public_history` side channel with explicit context header passing, reducing system complexity by 3 integration points while maintaining 100% prompt bit-identity.

**Principle**: Make implicit data flow explicit without adding abstraction layers.

---

## System Analysis

### Current Architecture (Prompt Construction Flow)

```
Phase2Manager
  ├─ Sets config._current_public_history ← SIDE CHANNEL
  ├─ Calls DiscussionService.get_participant_statement_with_retry()
  │    ├─ Calls DiscussionService.build_discussion_prompt()
  │    │    └─ Returns short prompt string
  │    └─ Calls Runner.run(agent, prompt, context=context)
  │         └─ OpenAI Runner invokes agent →
  │              └─ ParticipantAgent.format_context_info() ← IMPLICITLY CALLED
  │                   ├─ Reads config._current_public_history ← SIDE CHANNEL
  │                   └─ Calls language_manager.format_phase2_discussion_instructions()
  │                        └─ Returns formatted context header with history
  │
  └─ On retry: retry_callback reconstructs prompt ← DUPLICATION
       └─ Calls DiscussionService.build_discussion_prompt() again
```

### Problems Identified

1. **Hidden Data Flow** (`_current_public_history` side channel)
   - Set: `core/phase2_manager.py:334`
   - Read: `experiment_agents/participant_agent.py:289, 304`
   - Risk: Easy to forget to set, hard to debug when stale
   - Coupling: ParticipantAgent depends on Phase2Manager implementation detail

2. **Duplicate Logic** (Retry callback)
   - Original call: `core/phase2_manager.py:344-350`
   - Retry callback: `core/phase2_manager.py:343-350` (same logic)
   - Risk: Changes must be synchronized manually

3. **Unclear Responsibilities**
   - DiscussionService.build_discussion_prompt() returns minimal string
   - Actual discussion context is assembled elsewhere (in ParticipantAgent)
   - Hard to understand what prompt an agent actually sees

4. **Test Coverage Gap**
   - Golden tests don't capture actual production prompts
   - Side channel makes it hard to test prompt construction in isolation

---

## Design Principles

1. **Explicit > Implicit**: Replace side channels with explicit parameters
2. **Services Own Content**: Services provide prompts, managers orchestrate
3. **Single Source of Truth**: Each prompt component has one authoritative source
4. **Preserve Architecture**: Work within existing services-first pattern
5. **Zero Prompt Changes**: Maintain byte-for-byte prompt identity
6. **Incremental Migration**: Each step is independently testable and reversible

---

## Proposed Architecture

### Simplified Flow

```
Phase2Manager
  ├─ Formats context header ONCE per turn
  │    └─ Calls language_manager.format_phase2_discussion_instructions()
  │         └─ Returns formatted header with history
  │
  ├─ Stores header in context.formatted_context_header ← NEW, EXPLICIT
  │
  ├─ Calls DiscussionService.get_participant_statement_with_retry()
  │    ├─ Calls DiscussionService.build_discussion_prompt()
  │    │    └─ Returns short prompt string
  │    └─ Calls Runner.run(agent, prompt, context=context)
  │         └─ OpenAI Runner invokes agent →
  │              └─ ParticipantAgent.format_context_info()
  │                   ├─ Checks context.formatted_context_header
  │                   ├─ If present: uses it directly ← NEW PATH
  │                   └─ If absent: falls back to old logic ← COMPATIBILITY
  │
  └─ On retry: uses SAME context object ← NO DUPLICATION
       └─ Header already formatted, just re-runs with feedback
```

### Key Changes

1. **Add `formatted_context_header` to ParticipantContext**
   - Optional field (None by default)
   - When present, used instead of dynamic formatting
   - Enables explicit context passing

2. **Update ParticipantAgent.format_context_info()**
   - Check for `context.formatted_context_header` first
   - If present, use it directly
   - Otherwise, fall back to current logic (for backward compatibility)

3. **Update Phase2Manager discussion flow**
   - Pre-format context header once per turn
   - Store in `context.formatted_context_header`
   - Remove `config._current_public_history = ...` line

4. **No changes to DiscussionService**
   - Continues to provide discussion prompts
   - No new responsibilities

---

## Implementation Plan

### Phase 1: Establish Safety Net (Week 1)

**Goal**: Lock in current behavior before any changes

#### 1.1 Add Service-Level Golden Tests

Create `tests/golden/test_service_prompt_outputs.py`:

```python
@pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
def test_discussion_service_prompt_output(language):
    """Snapshot the actual discussion prompt from DiscussionService."""
    # Setup
    config = build_test_config(language=language)
    service = DiscussionService(language_manager, settings)
    discussion_state = create_test_discussion_state(round=3, history="...")

    # Execute
    prompt = service.build_discussion_prompt(
        discussion_state=discussion_state,
        round_num=3,
        max_rounds=5,
        participant_names=["Alice", "Bob", "Charlie"]
    )

    # Assert
    assert_matches_snapshot(prompt, f"discussion_prompt_{language}_round3.txt")
```

Similar tests for:
- `build_internal_reasoning_prompt()` (round 1 vs round 2+)
- Vote initiation prompts
- Vote confirmation prompts
- Results delivery prompts

**Files to Create**:
- `tests/golden/test_service_prompt_outputs.py`
- `tests/golden/snapshots/discussion_prompt_english_round1.txt`
- `tests/golden/snapshots/discussion_prompt_english_round3.txt`
- (Similar for spanish, mandarin, other prompt types)

**Success Criteria**:
- All current prompts captured as snapshots
- Tests pass on current codebase
- Coverage for English/Spanish/Mandarin

---

#### 1.2 Add Integration Test for _current_public_history

Create `tests/integration/test_phase2_prompt_construction.py`:

```python
def test_current_public_history_side_channel():
    """Verify _current_public_history is set and used correctly."""
    # Setup
    manager = Phase2Manager(...)
    discussion_state = GroupDiscussionState(public_history="Test history")

    # Track when _current_public_history is set
    config._current_public_history = None

    # Execute discussion turn
    await manager._get_participant_statement(participant, context, discussion_state, ...)

    # Assert: Side channel was used
    assert config._current_public_history == "Test history"

    # Assert: ParticipantAgent used it to format context
    # (Check via logs or instrumentation)
```

**Success Criteria**:
- Test documents current behavior
- Captures both setting and reading of side channel
- Will fail when we remove _current_public_history (good!)

---

### Phase 2: Add Explicit Context Passing (Week 2)

**Goal**: Introduce new path without removing old one

#### 2.1 Add `formatted_context_header` to ParticipantContext

**File**: `models/participant_context.py` (or wherever ParticipantContext is defined)

```python
@dataclass
class ParticipantContext:
    # ... existing fields ...

    # NEW: Pre-formatted context header for explicit passing
    # When present, overrides dynamic formatting in format_context_info()
    formatted_context_header: Optional[str] = None
```

**Tests**:
```python
def test_participant_context_with_formatted_header():
    """Verify formatted_context_header field exists and is optional."""
    context = ParticipantContext(name="Alice", ...)
    assert context.formatted_context_header is None  # Default

    context.formatted_context_header = "## Phase 2 Discussion\n..."
    assert context.formatted_context_header == "## Phase 2 Discussion\n..."
```

**Success Criteria**:
- Field added to dataclass
- Defaults to None (backward compatible)
- Type checking passes

---

#### 2.2 Update ParticipantAgent.format_context_info()

**File**: `experiment_agents/participant_agent.py` (lines 280-330)

**Change**:
```python
def format_context_info(context: ParticipantContext, language_manager, experiment_config=None):
    """Format context information for agent instructions."""

    # NEW: Check for pre-formatted context header first
    if hasattr(context, 'formatted_context_header') and context.formatted_context_header is not None:
        # Use pre-formatted header directly (new explicit path)
        phase_instructions = context.formatted_context_header
    else:
        # FALLBACK: Generate dynamically using current logic (backward compatibility)
        # ... existing logic from lines 287-310 ...
        phase_instructions = language_manager.format_phase2_discussion_instructions(
            round_number=context.round_number,
            max_rounds=max_rounds,
            participant_names=participant_names,
            discussion_history=public_history
        )

    # Rest of function unchanged
    return language_manager.format_context_info(
        name=context.name,
        role_description=context.role_description,
        # ... etc ...
        phase_instructions=phase_instructions
    )
```

**Tests**:
```python
def test_format_context_info_with_preformatted_header():
    """Verify format_context_info uses pre-formatted header when present."""
    context = ParticipantContext(name="Alice", phase=ExperimentPhase.PHASE_2)
    context.formatted_context_header = "CUSTOM HEADER"

    result = format_context_info(context, language_manager, config)

    assert "CUSTOM HEADER" in result
    # Verify it didn't call format_phase2_discussion_instructions

def test_format_context_info_without_preformatted_header():
    """Verify format_context_info falls back to dynamic generation."""
    context = ParticipantContext(name="Alice", phase=ExperimentPhase.PHASE_2)
    # No formatted_context_header set

    result = format_context_info(context, language_manager, config)

    # Should use current logic (side channel, etc.)
    assert result  # Just verify it works
```

**Success Criteria**:
- New path: Uses `formatted_context_header` when present
- Old path: Falls back to current logic when absent
- All existing tests pass (backward compatibility maintained)
- Golden tests still pass (prompts unchanged)

---

#### 2.3 Add Context Header Formatting Helper to Phase2Manager

**File**: `core/phase2_manager.py`

**Add new method**:
```python
def _format_phase2_context_header(self, discussion_state: GroupDiscussionState,
                                    round_num: int) -> str:
    """
    Format Phase 2 discussion context header with history.

    Extracts the context header formatting logic to a single location,
    eliminating duplication and making the data flow explicit.

    Args:
        discussion_state: Current discussion state with history
        round_num: Current round number

    Returns:
        Formatted context header string ready for agent instructions
    """
    participant_names = [p.name for p in self.participants]
    max_rounds = self.config.phase2_rounds

    return self.language_manager.format_phase2_discussion_instructions(
        round_number=round_num,
        max_rounds=max_rounds,
        participant_names=participant_names,
        discussion_history=discussion_state.public_history
    )
```

**Tests**:
```python
def test_format_phase2_context_header():
    """Verify context header formatting produces expected output."""
    manager = Phase2Manager(...)
    discussion_state = GroupDiscussionState(public_history="Alice: Hello\nBob: Hi")

    header = manager._format_phase2_context_header(discussion_state, round_num=2)

    assert "Round 2" in header
    assert "Alice: Hello" in header
    assert "Bob: Hi" in header
```

**Success Criteria**:
- Helper method extracts formatting logic
- Returns same string as current flow
- Unit testable in isolation

---

#### 2.4 Update Phase2Manager to Use Explicit Context Passing

**File**: `core/phase2_manager.py` (lines 320-394)

**Change in `_get_participant_statement`**:

```python
# OLD (line 334):
self.config._current_public_history = discussion_state.public_history

# NEW:
# Format context header once and store in context (explicit data flow)
context.formatted_context_header = self._format_phase2_context_header(
    discussion_state, round_num
)
```

**Remove retry callback duplication** (lines 336-370):

Since `context.formatted_context_header` is already set, the retry callback doesn't need to reconstruct anything. The context object already has everything needed.

**Updated retry callback**:
```python
async def retry_callback(feedback: str) -> str:
    try:
        self.logger.info(f"Intelligent retry for {participant.name}")

        # Build discussion prompt (service responsibility)
        discussion_prompt = self.discussion_service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=context.round_number,
            max_rounds=self.config.phase2_rounds,
            participant_names=participant_names,
            internal_reasoning=getattr(context, 'internal_reasoning', "")
        )

        # Add retry feedback to prompt
        retry_prompt = self._build_statement_retry_prompt(
            discussion_prompt, feedback, self.config.retry_feedback_detail
        )

        # Context already has formatted_context_header set, so Runner will use it
        retry_result = await Runner.run(participant.agent, retry_prompt, context=context)
        retry_response = retry_result.final_output

        # Update memory if enabled
        if self.config.memory_update_on_retry:
            await self._update_memory_with_retry_experience(
                participant, context, feedback, retry_response, self.config
            )

        return retry_response
    except Exception as e:
        self.logger.error(f"Retry failed: {e}")
        return ""
```

**Key Insight**: By setting `formatted_context_header` on context ONCE before the initial call, both the initial attempt and all retries use the same pre-formatted header. No duplication needed.

**Tests**:
```python
@pytest.mark.asyncio
async def test_discussion_turn_uses_explicit_context_header():
    """Verify discussion turns use explicit context header."""
    manager = Phase2Manager(...)
    discussion_state = GroupDiscussionState(public_history="Test history")
    context = ParticipantContext(name="Alice", round_number=1)

    # Execute
    await manager._get_participant_statement(
        participant, context, discussion_state, ...
    )

    # Assert: Context was updated with formatted header
    assert context.formatted_context_header is not None
    assert "Test history" in context.formatted_context_header
    assert "Round 1" in context.formatted_context_header

@pytest.mark.asyncio
async def test_retry_uses_same_context_header():
    """Verify retries reuse the same formatted header."""
    manager = Phase2Manager(...)
    # Force a validation failure to trigger retry
    discussion_state = GroupDiscussionState(public_history="Original history")
    context = ParticipantContext(name="Alice", round_number=2)

    # Mock validation to fail first time
    with mock.patch.object(DiscussionService, 'validate_statement') as mock_validate:
        mock_validate.side_effect = [False, True]  # Fail, then succeed

        await manager._get_participant_statement(
            participant, context, discussion_state, ...
        )

        # Assert: Context header was set only once (not reconstructed)
        # Check logs or instrumentation to verify _format_phase2_context_header
        # was called exactly once
```

**Success Criteria**:
- `config._current_public_history = ...` line removed
- `context.formatted_context_header = ...` line added
- Retry callback no longer reconstructs prompts
- Golden tests still pass (prompts unchanged)
- All existing tests pass

---

### Phase 3: Validation and Documentation (Week 3)

**Goal**: Confirm migration is complete and document changes

#### 3.1 Remove _current_public_history Attribute

**File**: `config/models.py` (or wherever ExperimentConfiguration is defined)

**Change**:
```python
class ExperimentConfiguration:
    # ... existing fields ...

    # REMOVED: _current_public_history
    # This was a side channel for Phase2Manager → ParticipantAgent communication
    # Now replaced with explicit context.formatted_context_header passing
```

**Search for remaining references**:
```bash
grep -r "_current_public_history" core/ experiment_agents/ config/
```

Should only find:
- This documentation
- Old test cases (to be updated)

**Tests**:
```python
def test_current_public_history_removed():
    """Verify _current_public_history attribute no longer exists."""
    config = ExperimentConfiguration(...)
    assert not hasattr(config, '_current_public_history')
```

**Success Criteria**:
- Attribute removed from ExperimentConfiguration
- No references in production code
- Test in Phase 1.2 now fails (expected - documents removal)

---

#### 3.2 Update Integration Test to Verify New Flow

**File**: `tests/integration/test_phase2_prompt_construction.py`

**Update test from Phase 1.2**:
```python
def test_context_header_explicit_passing():
    """Verify context header is passed explicitly via context object."""
    # Setup
    manager = Phase2Manager(...)
    discussion_state = GroupDiscussionState(public_history="Test history")
    context = ParticipantContext(name="Alice", round_number=1)

    # Verify no side channel attribute exists
    assert not hasattr(manager.config, '_current_public_history')

    # Execute discussion turn
    await manager._get_participant_statement(
        participant, context, discussion_state, ...
    )

    # Assert: Context was updated with formatted header (explicit)
    assert context.formatted_context_header is not None
    assert "Test history" in context.formatted_context_header

    # Assert: ParticipantAgent used the formatted header
    # (Can verify by checking the actual prompt sent to Runner)
```

**Success Criteria**:
- Test verifies new explicit flow
- Test would fail if old side channel was used
- Documents expected behavior

---

#### 3.3 Add Golden Test for Complete Prompt

**File**: `tests/golden/test_complete_agent_prompts.py`

**New test**:
```python
@pytest.mark.parametrize("language", ["english", "spanish", "mandarin"])
@pytest.mark.parametrize("round_num", [1, 3])
def test_complete_discussion_prompt_with_context(language, round_num):
    """
    Snapshot the COMPLETE prompt that agents receive (context + input).

    This captures both:
    - The context header (formatted_context_header in instructions)
    - The discussion prompt (from DiscussionService)

    Ensures the full prompt remains stable across refactors.
    """
    # Setup
    config = build_test_config(language=language)
    manager = Phase2Manager(...)
    discussion_state = create_test_discussion_state(
        round=round_num,
        history="Alice: I prefer principle 2\nBob: I agree with Alice"
    )
    context = ParticipantContext(name="Alice", round_number=round_num)

    # Format context header (Phase 2.3 helper)
    context.formatted_context_header = manager._format_phase2_context_header(
        discussion_state, round_num
    )

    # Build discussion prompt (service)
    discussion_prompt = manager.discussion_service.build_discussion_prompt(
        discussion_state=discussion_state,
        round_num=round_num,
        max_rounds=5,
        participant_names=["Alice", "Bob", "Charlie"]
    )

    # Format complete context (how ParticipantAgent assembles it)
    complete_prompt = format_context_info(context, language_manager, config)

    # Snapshot
    snapshot_name = f"complete_discussion_prompt_{language}_round{round_num}.txt"
    assert_matches_snapshot(complete_prompt, snapshot_name)
```

**Success Criteria**:
- Captures ACTUAL prompts agents receive
- Would catch any accidental changes to prompt construction
- Covers multilingual and multi-round scenarios

---

#### 3.4 Update Documentation

**Files to Update**:

1. **CLAUDE.md** - Update services documentation:
   ```markdown
   #### DiscussionService
   - **Owns**: Discussion prompts, statement validation, history management
   - **Modify here for**: Prompt templates, validation rules, history truncation
   - **Integration**: Context headers are pre-formatted by Phase2Manager and passed via
     `ParticipantContext.formatted_context_header` for explicit data flow
   ```

2. **phase2_prompt_streamlining_plan.md** - Add completion note:
   ```markdown
   ## Implementation Status

   ✅ **Completed** (2025-10-01): Phase 2 prompt streamlining via explicit context passing
   - Eliminated `_current_public_history` side channel
   - Added `ParticipantContext.formatted_context_header` for explicit passing
   - Extracted `Phase2Manager._format_phase2_context_header()` helper
   - Removed retry callback duplication
   - All golden tests passing with byte-identical prompts
   ```

3. **New doc**: `docs/architecture/prompt_construction.md`:
   ```markdown
   # Phase 2 Prompt Construction

   ## Overview
   Phase 2 prompts are assembled from two components:

   1. **Context Header** (instructions): Pre-formatted by Phase2Manager
   2. **Task Prompt** (input): Provided by services (DiscussionService, VotingService, etc.)

   ## Data Flow

   ```
   Phase2Manager
     ├─ Formats context header: _format_phase2_context_header()
     ├─ Stores in context.formatted_context_header
     ├─ Calls service for task prompt
     └─ Runner.run() assembles both via ParticipantAgent.format_context_info()
   ```

   ## Adding New Prompt Types

   1. Create prompt method in appropriate service
   2. Use `context.formatted_context_header` if Phase 2 discussion context needed
   3. Return task-specific prompt string
   4. Add golden test for the prompt
   ```

**Success Criteria**:
- Documentation reflects new architecture
- Clear guidance for future modifications
- Examples for common tasks

---

### Phase 4: Optional Improvements (Future)

**Not part of this plan, but documented for future consideration**

#### 4.1 Extract Common Prompt Utilities

If we discover actual duplication in prompt formatting (e.g., participant list formatting, constraint formatting), extract to a **private helper module**:

**File**: `core/services/_prompt_utils.py`

```python
def format_participant_list(names: List[str], language_manager) -> str:
    """Format participant names for prompts (internal helper)."""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" and {names[-1]}"

def format_constraint_description(principle: PrincipleChoice, amount: int, language_manager) -> str:
    """Format constraint for voting prompts (internal helper)."""
    # ...
```

**Only do this if**:
- Same formatting logic appears in 3+ places
- Extraction genuinely simplifies services
- Doesn't create unnecessary abstraction

#### 4.2 Add ParticipantContext Helper Methods

If context field manipulation is duplicated, add helper methods:

```python
@dataclass
class ParticipantContext:
    # ... existing fields ...

    def prepare_for_voting(self):
        """Reset context for voting phase."""
        self.interaction_type = "voting"
        self.internal_reasoning = None
        # ... other resets

    def prepare_for_final_ranking(self):
        """Reset context for final ranking."""
        self.interaction_type = "final_ranking"
        self.internal_reasoning = None
        # ... other resets
```

**Only do this if**:
- Same field manipulations appear in 3+ places
- Adds clarity without hiding important logic

---

## Validation Strategy

### Automated Tests

1. **Golden Tests** (Phase 1.1, 3.3)
   - Service-level prompt outputs
   - Complete agent prompts (context + input)
   - Must pass before merging any phase

2. **Integration Tests** (Phase 1.2, 3.2)
   - Phase 2 discussion flow end-to-end
   - Retry callback flow
   - Context header usage

3. **Unit Tests** (throughout)
   - ParticipantContext.formatted_context_header field
   - ParticipantAgent.format_context_info() both paths
   - Phase2Manager._format_phase2_context_header()

### Manual Validation

1. **Smoke Test**: Run a complete experiment
   ```bash
   python main.py config/fast.yaml results/smoke_test.json
   ```
   - Verify experiment completes successfully
   - Check logs for any warnings about prompt construction
   - Compare results file to baseline (should be similar)

2. **Prompt Inspection**: Log actual prompts during test run
   ```python
   # Add temporary logging in ParticipantAgent.format_context_info()
   logger.info(f"Context header: {context.formatted_context_header[:100]}...")
   logger.info(f"Task prompt: {prompt[:100]}...")
   ```
   - Verify context header contains expected history
   - Verify task prompt matches golden tests

3. **Multilingual Check**: Run tests in all languages
   ```bash
   python run_tests.py component --languages 3
   ```
   - Verify English, Spanish, Mandarin all work
   - Check for any language-specific issues

### Rollback Plan

Each phase is independently reversible:

**Phase 1**: Delete new test files (no production code changed)

**Phase 2.1-2.2**:
```python
# Remove from ParticipantContext
# formatted_context_header: Optional[str] = None  # DELETE THIS

# Revert ParticipantAgent.format_context_info()
# Remove: if hasattr(context, 'formatted_context_header') and context.formatted_context_header is not None:
```

**Phase 2.3-2.4**:
```python
# Revert Phase2Manager._get_participant_statement
# Remove: context.formatted_context_header = self._format_phase2_context_header(...)
# Restore: self.config._current_public_history = discussion_state.public_history
```

**Phase 3**: Restore `_current_public_history` attribute

All phases maintain backward compatibility until final removal.

---

## Success Metrics

### Code Quality

- **Coupling Reduction**: 1 side channel removed (`_current_public_history`)
- **Duplication Reduction**: Retry callback simplified (from 31 lines to ~20)
- **Explicit Contracts**: Data flow visible in code (context.formatted_context_header)

### Maintainability

- **Prompt Construction**: Single location for context header formatting
- **Testing**: Prompts testable in isolation (service-level golden tests)
- **Debugging**: Clear data flow makes issues easier to trace

### Correctness

- **Prompt Identity**: 100% byte-identical prompts (verified by golden tests)
- **Test Coverage**: New golden tests cover actual production prompts
- **Regression Prevention**: Integration tests catch future breakage

---

## Timeline

### Week 1: Safety Net
- Day 1-2: Implement golden tests (Phase 1.1)
- Day 3: Implement integration test (Phase 1.2)
- Day 4-5: Review and adjust test coverage

### Week 2: Implementation
- Day 1: Add formatted_context_header field (Phase 2.1)
- Day 2: Update ParticipantAgent (Phase 2.2)
- Day 3: Add context header helper (Phase 2.3)
- Day 4: Update Phase2Manager (Phase 2.4)
- Day 5: Integration testing and fixes

### Week 3: Validation
- Day 1: Remove _current_public_history (Phase 3.1)
- Day 2: Update integration tests (Phase 3.2)
- Day 3: Add complete prompt golden tests (Phase 3.3)
- Day 4: Update documentation (Phase 3.4)
- Day 5: Final validation and merge

**Total**: 3 weeks for complete migration

---

## Risk Assessment

### Low Risk ✅
- Adding new optional field to dataclass
- Adding helper method to Phase2Manager
- Creating new tests

### Medium Risk ⚠️
- Modifying ParticipantAgent.format_context_info() (mitigated by fallback path)
- Changing Phase2Manager prompt flow (mitigated by golden tests)

### High Risk ❌
- Removing _current_public_history (mitigated by doing it last, after full validation)

### Mitigation Strategies

1. **Incremental Rollout**: Each phase is independently testable
2. **Backward Compatibility**: Old path remains until final removal
3. **Golden Tests**: Catch any unintended prompt changes immediately
4. **Rollback Plan**: Clear instructions for reverting each phase
5. **Code Review**: Require review of all prompt-related changes

---

## Alternative Approaches Considered

### A. Builder Module Pattern
**Rejected**: Adds abstraction layer without clear benefit, violates services-first architecture

### B. Prompt State Objects
**Rejected**: Creates data duplication (GroupDiscussionState, ParticipantContext already exist)

### C. Mega-Method (run_turn)
**Rejected**: Moves orchestration responsibility from manager into service, violates separation of concerns

### D. Dependency Injection of History
**Rejected**: Would require changing service interfaces, more invasive than context field approach

### E. This Plan (Explicit Context Field)
**Accepted**: Minimal changes, preserves architecture, makes implicit explicit

---

## Conclusion

This plan eliminates the `_current_public_history` side channel through surgical changes that preserve the services-first architecture. By adding an optional `formatted_context_header` field to ParticipantContext and pre-formatting the header in Phase2Manager, we make the data flow explicit without adding abstraction layers.

**Key Benefits**:
- Simpler mental model (explicit data flow)
- Easier testing (prompts testable in isolation)
- Reduced duplication (retry callback simplified)
- Better maintainability (clear responsibilities)
- Zero risk to prompts (byte-identical output)

**Alignment with Principles**:
- ✅ Services own content (DiscussionService still owns prompts)
- ✅ Manager orchestrates (Phase2Manager still controls flow)
- ✅ Explicit > implicit (context field vs side channel)
- ✅ Simple over complex (no new abstractions)
- ✅ Incremental change (each phase independently valuable)

**Next Steps**:
1. Review and approve plan
2. Create GitHub issue/branch for implementation
3. Begin Phase 1 (golden tests)
4. Iterate through phases with review at each step
