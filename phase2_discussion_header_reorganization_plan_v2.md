# Phase 2 Discussion Header Reorganization Plan v2
## REVISED based on plan-reviewer feedback

## Change Summary from v1
- **Addresses translation hardcoding** (reviewer's critical issue)
- **Implements Option B**: MOVE information to context (not duplicate)
- **Removes info from discussion prompt** (new requirement)
- **Adds proper edge case handling**
- **Simplified approach** where possible

---

## Objective

**Move** discussion round and participant information from the discussion prompt to the context header section for:
1. Better accessibility (information on top)
2. Consistency with other general information (phase, bank balance, etc.)
3. Cleaner separation of stable context vs task instructions

### What Changes
- **Context Header**: Add "group discussion - round X of Y" and "Participants: [names]"
- **Discussion Prompt**: Remove this information (keep only task instruction)
- **Final Ranking**: No discussion header (stage-based conditional)

---

## Current State Analysis

### Current Implementation
**Context Template** (`translations/english_prompts.json` line 75):
```
Name: {name}
Role Description: {role_description}
Bank Balance: ${bank_balance:.2f}
Current Phase: {phase}

{formatted_memory}
```

**Discussion Prompt** (`translations/english_prompts.json` line 129):
```
"phase2_discussion_short_prompt": "GROUP DISCUSSION - Round {round_number} of {max_rounds}\n\nWhat is your statement to the group for this round?"
```

**Group Composition** (shown separately in discussion history)

### Issues Identified by Reviewer
1. ✅ **Translation hardcoding**: English "and" hardcoded in participant list
2. ✅ **Missing edge cases**: Empty list, single participant handling
3. ✅ **Duplication concern**: Now addressed - we MOVE not duplicate

---

## Desired State

### New Context Header During Discussion
```
Name: Sophie
Role Description: Thoughtful participant
Bank Balance: $15.50
Current Phase: Phase 2

group discussion - round 2 of 10

Participants: Sophie and Alice

{formatted_memory}
```

### New Discussion Prompt (Simplified)
```
What is your statement to the group for this round?
```

### Context During Final Ranking (Unchanged)
```
Name: Sophie
Role Description: Thoughtful participant
Bank Balance: $15.50
Current Phase: Phase 2

{formatted_memory}
```

---

## Implementation Plan

### Step 1: Add Localized List Formatting Keys

**File: `translations/english_prompts.json`**

Add after line 56 in "common" section:
```json
"list_formatting": {
  "conjunction": "and",
  "two_items": "{first} and {second}",
  "three_plus_items": "{items}, and {last}"
}
```

**File: `translations/spanish_prompts.json`**

```json
"list_formatting": {
  "conjunction": "y",
  "two_items": "{first} y {second}",
  "three_plus_items": "{items} y {last}"
}
```

**File: `translations/mandarin_prompts.json`**

```json
"list_formatting": {
  "conjunction": "和",
  "two_items": "{first}和{second}",
  "three_plus_items": "{items}和{last}"
}
```

### Step 2: Add Discussion Header Section Key

**File: `translations/english_prompts.json`**

Add after line 230:
```json
"context_discussion_header_section": "\ngroup discussion - round {round_number} of {max_rounds}\n\nParticipants: {participants}\n"
```

**File: `translations/spanish_prompts.json`**

```json
"context_discussion_header_section": "\ndiscusión grupal - ronda {round_number} de {max_rounds}\n\nParticipantes: {participants}\n"
```

**File: `translations/mandarin_prompts.json`**

```json
"context_discussion_header_section": "\n小组讨论 - 第 {round_number} 轮，共 {max_rounds} 轮\n\n参与者：{participants}\n"
```

### Step 3: Update Context Template

**File: `translations/english_prompts.json`** (line 75)

```json
"context_context_info_format": "\nName: {name}\nRole Description: {role_description}\nBank Balance: ${bank_balance:.2f}\nCurrent Phase: {phase}\n{discussion_header_section}\n{formatted_memory}\n\n{internal_reasoning_section}\n\n{experiment_explanation}\n\n{phase_instructions}\n\n{language_instruction}\n"
```

**Apply same pattern to Spanish and Mandarin translations.**

### Step 4: Simplify Discussion Prompt (Remove Duplicated Info)

**File: `translations/english_prompts.json`** (line 129)

**OLD:**
```json
"phase2_discussion_short_prompt": "GROUP DISCUSSION - Round {round_number} of {max_rounds}\n\nWhat is your statement to the group for this round?"
```

**NEW:**
```json
"phase2_discussion_short_prompt": "What is your statement to the group for this round?"
```

**Apply same simplification to Spanish and Mandarin translations.**

### Step 5: Add Participant List Formatting Method to Language Manager

**File: `utils/language_manager.py`**

Add new method after line 500:

```python
def format_participant_list(self, participant_names: List[str]) -> str:
    """
    Format participant list with language-appropriate conjunctions.

    Args:
        participant_names: List of participant names

    Returns:
        Formatted participant list string

    Examples:
        ["Alice"] → "Alice"
        ["Alice", "Bob"] → "Alice and Bob"
        ["Alice", "Bob", "Carol"] → "Alice, Bob, and Carol"
    """
    if not participant_names:
        return ""

    if len(participant_names) == 1:
        return participant_names[0]

    if len(participant_names) == 2:
        return self.get("common.list_formatting.two_items",
                       first=participant_names[0],
                       second=participant_names[1])

    # Three or more participants
    items_list = ", ".join(participant_names[:-1])
    return self.get("common.list_formatting.three_plus_items",
                   items=items_list,
                   last=participant_names[-1])
```

### Step 6: Update Language Manager Context Builder

**File: `utils/language_manager.py`** (around line 410)

Update method signature to add optional parameters:

```python
def format_context_info(self, name: str, role_description: str, bank_balance: float,
                       phase, round_number: int, personality: str,
                       formatted_memory: str = "",
                       internal_reasoning: str = "",
                       phase_instructions: str = "",
                       experiment_config = None,
                       stage: Optional[Any] = None,  # ExperimentStage enum
                       max_rounds: Optional[int] = None,
                       participant_names: Optional[List[str]] = None) -> str:
```

Add discussion header logic before the `return` statement (around line 470):

```python
# Format discussion header section if in discussion stage
discussion_header_section = ""
if stage and max_rounds and participant_names:
    # Import ExperimentStage dynamically to avoid circular imports
    from models.experiment_types import ExperimentStage

    if stage == ExperimentStage.DISCUSSION:
        # Format participant list using language-aware method
        participant_list = self.format_participant_list(participant_names)

        # Only add header if we have valid data
        if participant_list and round_number:
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

### Step 7: Update Phase2Manager to Pass Required Parameters

**File: `core/phase2_manager.py`**

Find where discussion contexts are built and add parameters. Search for calls involving `format_context_info` or context instruction building during discussion rounds.

**Expected location pattern** (actual line numbers may vary):
```python
# During discussion round context setup
context_instructions = self.language_manager.format_context_info(
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

**Important**: Ensure `ExperimentStage` is imported at top of file:
```python
from models.experiment_types import ExperimentStage
```

### Step 8: Update DiscussionService Prompt Building

**File: `core/services/discussion_service.py`** (line 115-119)

The `build_discussion_prompt` method currently passes `round_number` and `max_rounds` to the prompt template. Since we're simplifying the prompt, we can remove these parameters:

**OLD:**
```python
return language_manager.get(
    "prompts.phase2_discussion_short_prompt",
    round_number=round_num,
    max_rounds=max_rounds
)
```

**NEW:**
```python
return language_manager.get(
    "prompts.phase2_discussion_short_prompt"
)
```

---

## Testing Requirements

### Unit Tests

**File: `tests/unit/test_language_manager.py`**

Add comprehensive tests:

```python
def test_format_participant_list_single():
    """Test formatting with single participant."""
    lm = LanguageManager()
    result = lm.format_participant_list(["Alice"])
    assert result == "Alice"

def test_format_participant_list_two():
    """Test formatting with two participants."""
    lm = LanguageManager()
    result = lm.format_participant_list(["Alice", "Bob"])
    assert result == "Alice and Bob"

def test_format_participant_list_three_plus():
    """Test formatting with three+ participants."""
    lm = LanguageManager()
    result = lm.format_participant_list(["Alice", "Bob", "Carol"])
    assert result == "Alice, Bob, and Carol"

def test_format_participant_list_empty():
    """Test formatting with empty list."""
    lm = LanguageManager()
    result = lm.format_participant_list([])
    assert result == ""

def test_format_context_info_with_discussion_header():
    """Test that discussion header appears during discussion stage."""
    lm = LanguageManager()
    from models.experiment_types import ExperimentStage

    result = lm.format_context_info(
        name="Alice",
        role_description="Participant",
        bank_balance=10.0,
        phase="Phase 2",
        round_number=2,
        personality="thoughtful",
        stage=ExperimentStage.DISCUSSION,
        max_rounds=10,
        participant_names=["Alice", "Bob"]
    )

    assert "group discussion - round 2 of 10" in result.lower()
    assert "Participants: Alice and Bob" in result

def test_format_context_info_without_discussion_header():
    """Test that discussion header does NOT appear during final ranking."""
    lm = LanguageManager()
    from models.experiment_types import ExperimentStage

    result = lm.format_context_info(
        name="Alice",
        role_description="Participant",
        bank_balance=10.0,
        phase="Phase 2",
        round_number=None,
        personality="thoughtful",
        stage=ExperimentStage.FINAL_RANKING
    )

    assert "group discussion" not in result.lower()
    assert "Participants:" not in result

def test_format_participant_list_multilingual():
    """Test participant list formatting in Spanish and Mandarin."""
    # Spanish
    lm_es = LanguageManager()
    lm_es.set_language(SupportedLanguage.SPANISH)
    result_es = lm_es.format_participant_list(["Alice", "Bob"])
    assert "y" in result_es  # Spanish conjunction

    # Mandarin
    lm_zh = LanguageManager()
    lm_zh.set_language(SupportedLanguage.MANDARIN)
    result_zh = lm_zh.format_participant_list(["Alice", "Bob"])
    assert "和" in result_zh  # Mandarin conjunction
```

### Integration Tests

**File: `tests/integration/test_phase2_discussion_header.py`** (new file)

```python
import pytest
from core.experiment_manager import FrohlichExperimentManager
from models.experiment_types import ExperimentStage

@pytest.mark.asyncio
async def test_discussion_header_in_phase2_context():
    """Test that discussion header appears in Phase 2 discussion context."""
    # Create minimal config with 2 participants, 2 rounds
    config = create_minimal_test_config(
        num_participants=2,
        phase2_rounds=2,
        phase1_rounds=0  # Skip Phase 1
    )

    manager = FrohlichExperimentManager(config)

    # Run through first discussion round
    await manager.run_phase2()

    # Get context from first participant during discussion
    context = manager.phase2_manager.participants[0].context

    # Verify header is present
    assert "group discussion" in context.instructions.lower()
    assert "round 1 of 2" in context.instructions.lower()
    assert "Participants:" in context.instructions

@pytest.mark.asyncio
async def test_discussion_header_absent_in_final_ranking():
    """Test that discussion header does NOT appear in final ranking."""
    # Create minimal config
    config = create_minimal_test_config(
        num_participants=2,
        phase2_rounds=2,
        phase1_rounds=0
    )

    manager = FrohlichExperimentManager(config)

    # Run through Phase 2 to final ranking
    await manager.run_phase2()

    # Get context during final ranking
    context = manager.phase2_manager.participants[0].context

    # Verify stage is FINAL_RANKING
    assert context.stage == ExperimentStage.FINAL_RANKING

    # Verify header is NOT present
    assert "group discussion" not in context.instructions.lower()
    assert "round" not in context.instructions.lower()
```

### Manual Verification Checklist

Run experiment and verify:
- [ ] Discussion header appears in Phase 2 rounds 1-10
- [ ] Header shows correct round numbers (e.g., "round 3 of 10")
- [ ] Participant names formatted correctly
- [ ] Header does NOT appear in final ranking
- [ ] All three languages display correctly
- [ ] Discussion prompt is simplified (no duplicate info)

---

## Edge Cases Handling

### Empty Participant List
**Scenario**: `participant_names=[]` passed to method
**Handling**: `format_participant_list` returns empty string, conditional prevents header addition

### Single Participant
**Scenario**: Only one participant in experiment
**Handling**: Format as just the name without conjunction

### Missing Parameters
**Scenario**: `max_rounds=None` or `participant_names=None`
**Handling**: Conditional check prevents header creation, returns empty string

### Stage Not Set
**Scenario**: `stage=None` passed to method
**Handling**: Conditional check fails early, no header added

### Translation Key Missing
**Scenario**: Translation file doesn't have new keys
**Handling**: Language manager logs warning, returns key name as fallback

---

## Rollout Strategy

### Phase 1: Translation Updates (30 min)
1. Add `list_formatting` keys to all three language files
2. Add `context_discussion_header_section` keys to all three files
3. Update `context_context_info_format` templates in all three files
4. Simplify `phase2_discussion_short_prompt` in all three files
5. Commit: "Add discussion header translations and simplify prompt"

### Phase 2: Language Manager Updates (45 min)
1. Add `format_participant_list()` method with proper localization
2. Update `format_context_info()` signature and logic
3. Add defensive checks for edge cases
4. Commit: "Implement language-aware participant list formatting"

### Phase 3: Phase2Manager and DiscussionService Updates (30 min)
1. Find and update context building call sites in Phase2Manager
2. Update discussion prompt building in DiscussionService
3. Ensure `ExperimentStage` is imported where needed
4. Commit: "Wire discussion header into Phase 2 context building"

### Phase 4: Testing (1 hour)
1. Add unit tests for language manager methods
2. Add integration tests for Phase 2 context
3. Run full test suite: `python run_tests.py`
4. Fix any failures
5. Commit: "Add comprehensive tests for discussion header feature"

### Phase 5: Manual Verification (30 min)
1. Run experiment: `python main.py`
2. Verify output in all three languages
3. Check edge cases (single participant config)
4. Document any issues
5. Final commit: "Complete Phase 2 discussion header reorganization"

---

## Risk Assessment

### Low Risk
- ✅ Stage-based conditional is explicit and testable
- ✅ Default to empty string prevents breaking changes
- ✅ Backward compatible (existing code without new params works)

### Medium Risk (Addressed from v1)
- ✅ Translation consistency - now using proper localized keys
- ✅ Edge cases - explicit handling for empty/single/missing
- ✅ Parameter passing - defensive checks prevent errors

### Remaining Risks
1. **Call site discovery**: May need to search multiple locations in Phase2Manager
   - Mitigation: Grep for context building patterns, test thoroughly
2. **Import cycles**: Dynamic import of ExperimentStage in language_manager
   - Mitigation: Use late import inside method, test imports
3. **Token usage**: Slightly increases context size
   - Impact: Minimal (~50 characters per round)

---

## Success Criteria

- [ ] Discussion header appears during Phase 2 discussion (rounds 1-10)
- [ ] Discussion header does NOT appear during final ranking
- [ ] Header displays in lowercase style: "group discussion - round X of Y"
- [ ] Participant names formatted correctly in all languages
- [ ] English: "Alice and Bob" or "Alice, Bob, and Carol"
- [ ] Spanish: "Alice y Bob" or "Alice, Bob y Carol"
- [ ] Mandarin: "Alice和Bob" or "Alice、Bob和Carol"
- [ ] Discussion prompt simplified (no duplicate round info)
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual verification in all three languages successful
- [ ] No regression in existing functionality

---

## Timeline Estimate

- Translation updates: 30 minutes
- Language manager code: 45 minutes
- Phase2Manager/DiscussionService updates: 30 minutes
- Testing: 1 hour
- Verification: 30 minutes
- **Total: 3 hours 15 minutes**

---

## Changes from v1

### Improvements Based on Reviewer Feedback
1. ✅ **Fixed translation hardcoding** - Added localized list formatting keys
2. ✅ **Clarified requirement** - Now explicitly MOVES (not duplicates) information
3. ✅ **Added edge case handling** - Empty lists, single participant, missing params
4. ✅ **Simplified discussion prompt** - Removed redundant information per Option B
5. ✅ **Better method design** - Separate `format_participant_list()` method
6. ✅ **Defensive programming** - Multiple conditional checks prevent errors

### Maintained from v1
- ✅ Stage-based conditional approach (reviewer agreed it's technically sound)
- ✅ Services-first architecture (language manager handles formatting)
- ✅ Comprehensive testing strategy
- ✅ Clear rollout phases

---

## Justification for Approach

### Why Modify Context Template?
**User Requirement**: Information should be "on top" for accessibility and consistency with other general information (phase, bank balance, etc.)

This requirement explicitly places the feature in the context section, not the prompt section.

### Why Stage-Based Conditional?
**Clean State Management**: The `ExperimentStage` enum already tracks where the agent is in the experiment. Using this existing infrastructure is cleaner than adding new flags or conditions.

### Why Remove from Prompt?
**User Requirement**: Option B - information should appear ONLY in context, not duplicated. This simplifies the prompt and reduces redundancy.

---

## Dependencies

- None (standalone feature)

## Related Documentation

- `CLAUDE.md` - Project overview and architecture
- `phase2_discussion_header_reorganization_plan.md` - Original v1 plan
- Plan reviewer feedback - Addressed critical issues