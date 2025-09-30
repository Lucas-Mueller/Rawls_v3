# Phase 2 Discussion Header Reorganization Plan

## Objective

Reorganize the display of discussion information in Phase 2 to show:
1. **GROUP DISCUSSION - Round X of Y** (in small caps style)
2. **Participants: [list of names]**

This information should appear right below "Current Phase" in the context header and should be present throughout the entire group discussion phase, but NOT during final preference ranking.

## Current State Analysis

### Current Implementation Location
- **Context Template**: `translations/english_prompts.json` line 75: `context_context_info_format`
- **Context Builder**: `utils/language_manager.py` lines 470-481: `format_context_info()` method
- **Discussion Service**: `core/services/discussion_service.py` lines 96-119: `build_discussion_prompt()` method

### Current Format
```
Name: {name}
Role Description: {role_description}
Bank Balance: ${bank_balance:.2f}
Current Phase: {phase}

{formatted_memory}
...
```

### Stage Detection
- **Discussion Stage**: `context.stage = ExperimentStage.DISCUSSION` with `context.round_number` set
- **Final Ranking Stage**: `context.stage = ExperimentStage.FINAL_RANKING` with `context.round_number = None`

## Desired State

### New Format During Discussion
```
Name: {name}
Role Description: {role_description}
Bank Balance: ${bank_balance:.2f}
Current Phase: {phase}

group discussion - round X of Y

Participants: [participant names]

{formatted_memory}
...
```

### Format During Final Ranking (Unchanged)
```
Name: {name}
Role Description: {role_description}
Bank Balance: ${bank_balance:.2f}
Current Phase: {phase}

{formatted_memory}
...
```

## Implementation Plan

### Step 1: Add New Translation Keys

**File: `translations/english_prompts.json`**

Add new template key after line 230:
```json
"context_discussion_header_section": "\ngroup discussion - round {round_number} of {max_rounds}\n\nParticipants: {participants}\n"
```

**File: `translations/spanish_prompts.json`**

Add corresponding Spanish translation:
```json
"context_discussion_header_section": "\ndiscusión grupal - ronda {round_number} de {max_rounds}\n\nParticipantes: {participants}\n"
```

**File: `translations/mandarin_prompts.json`**

Add corresponding Mandarin translation:
```json
"context_discussion_header_section": "\n小组讨论 - 第 {round_number} 轮，共 {max_rounds} 轮\n\n参与者：{participants}\n"
```

### Step 2: Modify Context Template

**File: `translations/english_prompts.json`** (line 75)

Update `context_context_info_format` to include optional discussion header section:
```json
"context_context_info_format": "\nName: {name}\nRole Description: {role_description}\nBank Balance: ${bank_balance:.2f}\nCurrent Phase: {phase}\n{discussion_header_section}\n{formatted_memory}\n\n{internal_reasoning_section}\n\n{experiment_explanation}\n\n{phase_instructions}\n\n{language_instruction}\n"
```

**Files: `translations/spanish_prompts.json` and `translations/mandarin_prompts.json`**

Apply same pattern to their respective `context_context_info_format` templates.

### Step 3: Update Language Manager Context Builder

**File: `utils/language_manager.py`** (around line 470)

Modify `format_context_info()` method to conditionally include discussion header:

```python
def format_context_info(self, name: str, role_description: str, bank_balance: float,
                       phase, round_number: int, personality: str,
                       formatted_memory: str = "",
                       internal_reasoning: str = "",
                       phase_instructions: str = "",
                       experiment_config = None,
                       stage: Optional[ExperimentStage] = None,
                       max_rounds: Optional[int] = None,
                       participant_names: Optional[List[str]] = None) -> str:
    """
    Format context information for participant agents.

    Args:
        ...existing args...
        stage: Current experiment stage (for conditional formatting)
        max_rounds: Maximum number of discussion rounds (for header)
        participant_names: List of participant names (for header)

    Returns:
        Formatted context string
    """

    # ... existing code for experiment explanation, language instruction, etc. ...

    # Format discussion header section if in discussion stage
    discussion_header_section = ""
    if stage == ExperimentStage.DISCUSSION and round_number and max_rounds and participant_names:
        # Format participant list
        if len(participant_names) == 1:
            participant_list = participant_names[0]
        elif len(participant_names) == 2:
            participant_list = f"{participant_names[0]} and {participant_names[1]}"
        else:
            participant_list = ", ".join(participant_names[:-1]) + f" and {participant_names[-1]}"

        discussion_header_section = self.get(
            "prompts.context_discussion_header_section",
            round_number=round_number,
            max_rounds=max_rounds,
            participants=participant_list
        )

    return self.get("prompts.context_context_info_format",
                   name=name,
                   role_description=role_description,
                   bank_balance=bank_balance,
                   phase=localized_phase,
                   round_number=round_number,
                   discussion_header_section=discussion_header_section,  # NEW
                   formatted_memory=formatted_memory,
                   internal_reasoning_section=internal_reasoning_section,
                   experiment_explanation=experiment_explanation,
                   personality=personality,
                   phase_instructions=phase_instructions,
                   language_instruction=language_instruction)
```

### Step 4: Update Phase2Manager Context Updates

**File: `core/phase2_manager.py`**

Update calls to `format_context_info()` during discussion rounds to pass required parameters:

1. Find where `format_context_info()` is called during discussion
2. Pass additional parameters:
   - `stage=ExperimentStage.DISCUSSION`
   - `max_rounds=self.experiment_config.phase2_rounds`
   - `participant_names=[p.name for p in self.participants]`

Example location to update:
```python
# During discussion round context update
context_info = self.language_manager.format_context_info(
    name=participant.name,
    role_description=agent_config.role_description,
    bank_balance=context.bank_balance,
    phase="Phase 2",
    round_number=round_num,
    personality=agent_config.personality,
    formatted_memory=formatted_memory,
    internal_reasoning=internal_reasoning,
    phase_instructions=phase_instructions,
    experiment_config=self.experiment_config,
    stage=ExperimentStage.DISCUSSION,  # NEW
    max_rounds=self.experiment_config.phase2_rounds,  # NEW
    participant_names=[p.name for p in self.participants]  # NEW
)
```

### Step 5: Verify Final Ranking Exclusion

**File: `core/services/counterfactuals_service.py`** (lines 835-846)

Verify that final ranking does not pass discussion-related parameters:
- Context stage is already set to `ExperimentStage.FINAL_RANKING`
- `round_number` is set to `None`
- No participant names are passed

This ensures the discussion header section remains empty during final ranking.

## Testing Requirements

### Unit Tests

**File: `tests/unit/test_language_manager.py`**

Add tests for conditional discussion header:
```python
def test_format_context_info_with_discussion_header():
    """Test that discussion header appears during discussion stage."""
    # Test with stage=DISCUSSION, round_number, max_rounds, participant_names
    # Verify header section is present

def test_format_context_info_without_discussion_header():
    """Test that discussion header does not appear during final ranking."""
    # Test with stage=FINAL_RANKING
    # Verify header section is absent

def test_format_context_info_participant_formatting():
    """Test various participant list formats."""
    # Test with 1, 2, 3+ participants
    # Verify proper formatting: "Alice", "Alice and Bob", "Alice, Bob, and Carol"
```

### Integration Tests

**File: `tests/integration/test_phase2_discussion_header.py`**

Create new integration test:
```python
async def test_discussion_header_presence_in_phase2():
    """Test that discussion header appears in Phase 2 discussion context."""
    # Run mini experiment with 2 participants, 2 rounds
    # Capture context during discussion round
    # Assert header section is present

async def test_discussion_header_absent_in_final_ranking():
    """Test that discussion header does not appear in final ranking."""
    # Run mini experiment through to final ranking
    # Capture context during final ranking
    # Assert header section is absent
```

### Manual Verification

1. Run experiment with default config: `python main.py`
2. Check terminal output during Phase 2 discussion rounds
3. Verify header appears as: "group discussion - round X of Y" followed by "Participants: [names]"
4. Check final ranking output
5. Verify header does NOT appear during final ranking

## Rollout Strategy

### Phase 1: Translation Updates
1. Add new translation keys to all three language files
2. Commit with message: "Add discussion header section translation keys"

### Phase 2: Template Updates
1. Update `context_context_info_format` templates in all three languages
2. Commit with message: "Update context templates to include optional discussion header"

### Phase 3: Code Changes
1. Update `language_manager.py` to conditionally build discussion header
2. Update `phase2_manager.py` to pass required parameters during discussion
3. Commit with message: "Implement conditional discussion header in Phase 2 context"

### Phase 4: Testing
1. Add unit tests for language manager
2. Add integration tests for Phase 2 discussion
3. Run full test suite: `python run_tests.py`
4. Commit with message: "Add tests for Phase 2 discussion header feature"

### Phase 5: Verification
1. Run manual verification experiment
2. Review output logs
3. Document any issues found
4. Create final commit: "Complete Phase 2 discussion header reorganization"

## Risk Assessment

### Low Risk
- Changes are additive (new template key, optional parameter)
- Backward compatible (empty string if parameters not provided)
- Stage-based conditional prevents unintended display

### Medium Risk
- Translation consistency across three languages
- Mitigation: Review all translations with native speakers

### Potential Issues
1. **Missing Parameters**: If `max_rounds` or `participant_names` not passed
   - Solution: Default to empty string, log warning
2. **Translation Keys Missing**: If translation file not updated
   - Solution: Fallback to English or key name
3. **Format String Errors**: If template placeholders mismatch
   - Solution: Comprehensive testing before deployment

## Success Criteria

- [ ] Discussion header appears during all Phase 2 discussion rounds
- [ ] Discussion header does NOT appear during final ranking
- [ ] Header displays round information in small caps style
- [ ] Participant names formatted correctly (1, 2, or 3+ participants)
- [ ] All three languages display correctly
- [ ] All tests pass
- [ ] No regression in existing functionality

## Timeline Estimate

- Translation updates: 30 minutes
- Code changes: 1 hour
- Testing: 1 hour
- Verification: 30 minutes
- **Total: 3 hours**

## Dependencies

- None (standalone feature)

## Related Documentation

- `CLAUDE.md` - Project overview and architecture
- `codex_round_section_error_report.md` - Previous similar issue
- `reports/phase2_discussion_history_restructuring_report.md` - Related Phase 2 changes

## Notes

- Use lowercase "group discussion" to match common convention
- "Round X of Y" format matches existing pattern
- Participant formatting follows natural language conventions
- Stage-based conditional is cleaner than interaction_type checking