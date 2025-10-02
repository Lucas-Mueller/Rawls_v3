# Phase 1 Memory Update Explanation - Implementation Plan

## Overview
Update Phase 1 memory update prompts to show the detailed experiment introduction only on the first memory update, instead of showing the brief two-phase explanation on every first memory update.

## Current Behavior

### Memory Update Flow in Phase 1
Phase 1 has multiple memory update points:
1. After initial ranking (round 0, stage: INITIAL_RANKING)
2. After detailed explanation (round -1, stage: PRINCIPLE_EXPLANATION)
3. After post-explanation ranking (round 0, stage: POST_EXPLANATION_RANKING)
4. After each application round (rounds 1-4, stage: APPLICATION)
5. After final ranking (round 5, stage: FINAL_RANKING)

### Current Memory Update Prompt Behavior
Located in: `utils/memory_manager.py` (lines 329-340)

```python
# Conditionally include experiment explanation based on first_memory_update flag
# Only show explanation on first memory update, then empty string for subsequent updates
experiment_explanation = ""
if context is not None and context.first_memory_update:
    experiment_explanation = language_manager.get("prompts.experiment_explanation")
```

**Problem:** Currently uses `prompts.experiment_explanation` (short two-phase text) for first memory update. We want:
- Phase 1 first memory update: Use `prompts.initial_experiment_explanation` (long detailed text)
- Phase 1 subsequent memory updates: Use empty string (no explanation at all)
- Phase 2: Empty string (Phase 2 templates handle their own explanations)

### Translation Keys Available

**English** (`translations/english_prompts.json`):

1. **Line 64** - `experiment_explanation` (SHORT):
   ```
   "You are participating in an experiment studying principles of justice and income distribution.

   The experiment has two main phases:

   PHASE 1: You will individually learn about and apply four different principles of justice...
   PHASE 2: You will join a group discussion to reach consensus..."
   ```

2. **Line 65** - `initial_experiment_explanation` (DETAILED):
   ```
   "This experiment deals with the question: \"What is a just distribution of income?\"
   An individual's lifetime income is in part a result of many genetic and social accidents...
   [Full 3-paragraph detailed explanation of experiment structure and stakes]"
   ```

**Status:** Spanish and Mandarin translation files also have both keys.

## Required Changes

### Target Behavior
- **First memory update in Phase 1**: Use `initial_experiment_explanation` (detailed text)
- **All subsequent memory updates in Phase 1**: Use empty string (NO explanation - neither short nor long)
- **Phase 2 memory updates**: Keep existing behavior (no change - empty string unless first round templates include it)

### File to Modify

**File:** `utils/memory_manager.py`
**Method:** `_create_memory_update_prompt` (lines 243-340)

#### Current Code (lines 329-340):
```python
# Conditionally include experiment explanation based on first_memory_update flag
# Only show explanation on first memory update, then empty string for subsequent updates
experiment_explanation = ""
if context is not None and context.first_memory_update:
    experiment_explanation = language_manager.get("prompts.experiment_explanation")

return language_manager.get(
    prompt_key,
    current_memory=current_memory if current_memory.strip() else language_manager.get("prompts.memory_empty_memory_placeholder"),
    round_content=round_content,
    experiment_explanation=experiment_explanation
)
```

#### Proposed Change:
Replace lines 329-333 with phase-aware logic:

```python
# Conditionally include experiment explanation based on first_memory_update flag and phase
# Phase 1: Use detailed initial explanation ONLY on first update, then empty string for all subsequent updates
# Phase 2: Empty string (Phase 2 first round templates already include Phase 2 explanation if needed)
experiment_explanation = ""
if context is not None and context.first_memory_update:
    # Check if we're in Phase 1
    if phase == "phase_1":
        # Phase 1: Use detailed initial experiment explanation on first memory update only
        experiment_explanation = language_manager.get("prompts.initial_experiment_explanation")
    # For Phase 2, leave experiment_explanation as empty string
    # (Phase 2 templates handle their own explanations via _first_round variants)
```

### Implementation Notes

1. **Phase Detection**: The `phase` parameter is already available in the method signature and is populated from context
2. **Flag Management**: The `context.first_memory_update` flag is already set to False after successful memory updates (lines 157, 164, 187)
3. **No Translation Changes**: Both translation keys already exist in all language files
4. **No Phase 1 Manager Changes**: Phase 1 manager already passes `phase="phase_1"` to memory update calls (lines 307, 333, 361, 433, 458)

## Testing Strategy

### Manual Testing
Run a Phase 1 experiment and verify:
1. First memory update contains the detailed `initial_experiment_explanation` text
2. Subsequent memory updates in Phase 1 do NOT contain any experiment explanation
3. Memory update prompts are correctly formatted

### Automated Testing
Review existing tests that validate memory updates:
- `tests/unit/test_memory_manager.py` - May need updates to verify Phase 1 vs Phase 2 behavior
- `tests/component/` - Component tests that run through Phase 1 flows

### Validation Points
1. Check first memory update prompt in Phase 1 contains full detailed text
2. Check subsequent Phase 1 memory updates have empty experiment_explanation
3. Verify `first_memory_update` flag is properly reset to False after first update
4. Confirm Phase 2 behavior remains unchanged

## Risk Assessment

### Low Risk
- **Isolated Change**: Only affects one conditional block in memory_manager.py
- **Backward Compatible**: Uses existing translation keys that are already present
- **No Data Model Changes**: Uses existing `first_memory_update` flag and phase tracking
- **Minimal Surface Area**: Single method, single file

### Potential Issues
1. **Translation Missing**: If any language file is missing `initial_experiment_explanation` key
   - **Mitigation**: All three language files verified to have the key
2. **Phase String Mismatch**: If phase value doesn't match "phase_1" exactly
   - **Mitigation**: Phase 1 manager consistently passes `phase="phase_1"`
3. **Test Failures**: Existing tests may expect old behavior
   - **Mitigation**: Review and update test expectations as needed

## Success Criteria

1. ✅ First memory update in Phase 1 shows detailed `initial_experiment_explanation` text
2. ✅ All subsequent Phase 1 memory updates show NO experiment explanation (empty string)
3. ✅ Phase 2 memory updates show NO experiment explanation via this mechanism (templates handle their own explanations)
4. ✅ All existing tests pass (or are updated appropriately)
5. ✅ Spanish and Mandarin experiments work correctly

## Implementation Checklist

- [ ] Update `utils/memory_manager.py` method `_create_memory_update_prompt`
- [ ] Test with English experiment
- [ ] Test with Spanish experiment
- [ ] Test with Mandarin experiment
- [ ] Review and update unit tests if needed
- [ ] Review and update component tests if needed
- [ ] Verify no regression in Phase 2 behavior

## Related Files (No Changes Needed)

- `core/phase1_manager.py` - Already passes correct phase parameter
- `models/experiment_types.py` - ParticipantContext already has `first_memory_update` flag
- `translations/*.json` - All have required translation keys
- `experiment_agents/participant_agent.py` - No changes needed

## Estimated Effort

- **Implementation**: 5-10 minutes (single conditional block change)
- **Testing**: 15-20 minutes (manual testing with 3 languages)
- **Review**: 5 minutes (verify change is minimal and focused)
- **Total**: ~30-35 minutes
