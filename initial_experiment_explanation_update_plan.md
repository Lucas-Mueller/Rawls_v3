# Plan: Update Initial Experiment Explanation

## Overview
Replace the current experiment explanation shown to agents initially (before first memory update) with the detailed Frohlich experiment introduction. After the first memory update, the explanation should remain unchanged.

## Current Behavior
- `experiment_explanation` from `prompts.experiment_explanation` is currently shown on first turn per phase
- Current text is brief (2 paragraphs about Phase 1 and Phase 2)
- Controlled by `include_experiment_explanation_each_turn` config flag

## Proposed Changes

### 1. Add New Prompt Key (All Language Files)

**File**: `translations/english_prompts.json`

Add new key under `prompts` section:

```json
"initial_experiment_explanation": "\nThis experiment deals with the question: \"What is a just distribution of income?\" An individual's lifetime income is in part a result of many genetic and social accidents. The luckiest get the greatest talents and the highest rewards such as status and wealth. The least fortunate get the lowest abilities and opportunities, and receive the associated costs of poverty. Societies can deal with these inequities and risks by adopting income redistribution policies. This experiment deals with the justice of such policies. The experiment is divided into three parts.\n\nIn the first part of the experiment each of you will be introduced to a few theories of justice. To do this you will consider some examples and make some choices. These choices will have real monetary consequences for you. Your pay for the first part of the experiment will be based on your choices. You will have 1 hour for the first part. In this part you will be given a series of questions. These questions are merely to ensure that you have learned the concepts which are being used in the experiment. If you do not answer the questions correctly, then you are to go back to review the material and correct wrong answers. Once you have mastered the material, you can go on to make choices for which you will be paid. If you do not learn the material in a reasonable amount of time, you will not be able to earn as much money as possible since you must finish the first part of the experiment in 1 hour. But you should have plenty of time to finish this part of the experiment. Everyone will go on to the second part either after 1 hour or after everyone has finished Part I, whichever occurs first.\n\nIn the second part, you will all be asked, as a group, to discuss notions of justice. After the discussion, you will be asked to reach a group decision on which principle of justice you like best. Your pay for Part II of the experiment will be based on the principle which the group chooses.\n\nThroughout the experiment, we shall scale all examples and choices so that the monies can be thought of as average lifetime incomes. We then refer to these stakes as incomes. In Part I your actual stakes are equal to $1 for every $10,000 of income listed in the text.\n"
```

**Files**: `translations/spanish_prompts.json` and `translations/mandarin_prompts.json`

Use placeholder (will be translated separately):
```json
"initial_experiment_explanation": "\n{initial_experiment_explanation}\n"
```

### 2. Update Language Manager

**File**: `utils/language_manager.py`

Add new method:
```python
def get_initial_experiment_explanation(self) -> str:
    """Get the initial/detailed experiment explanation shown before first memory update."""
    return self.get("prompts.initial_experiment_explanation")
```

Update `format_context_info()` method to use different explanation based on whether it's the first turn:

```python
# Around line 467-474, replace:
experiment_explanation = self.get_experiment_explanation() if include_explanation else ""

# With:
if include_explanation:
    # Use detailed explanation on first turn, brief explanation thereafter
    if is_first_turn:
        experiment_explanation = self.get_initial_experiment_explanation()
    else:
        experiment_explanation = self.get_experiment_explanation()
else:
    experiment_explanation = ""
```

### 3. Update Memory Manager (Optional - for memory update prompts)

**File**: `utils/memory_manager.py`

Check if memory update prompts need the initial explanation. Currently they use `{experiment_explanation}` placeholder which gets filled by `language_manager.py`.

**No changes needed** - the memory prompts will continue to use the brief `experiment_explanation` as they currently do, since memory updates happen after the initial context has already been shown.

## Testing Strategy

1. **Unit Test**: Verify new method `get_initial_experiment_explanation()` returns correct text
2. **Integration Test**: Verify agents receive detailed explanation on first turn only
3. **Manual Test**: Run experiment with `config/fast.yaml` and check:
   - First context shows detailed explanation
   - Memory updates show brief explanation (or none based on config)
   - Subsequent turns after first memory update don't repeat initial explanation

## Implementation Steps

1. ✅ Add `initial_experiment_explanation` key to `translations/english_prompts.json`
2. ✅ Add placeholder to `translations/spanish_prompts.json` and `translations/mandarin_prompts.json`
3. ✅ Add `get_initial_experiment_explanation()` method to `utils/language_manager.py`
4. ✅ Update `format_context_info()` logic in `utils/language_manager.py`
5. ✅ Test changes with fast config
6. ✅ Verify memory updates still work correctly

## Notes on Simplicity

- **No new config flags**: Reuses existing `is_first_turn` logic
- **No database changes**: Only JSON and Python code
- **Clear separation**: Initial explanation is distinct from ongoing explanation
- **Backward compatible**: Existing `experiment_explanation` unchanged for memory prompts
- **Single responsibility**: Each explanation serves a specific purpose

## Translation Tasks (Future)

Spanish and Mandarin translations will need to be provided for `initial_experiment_explanation`. The placeholder approach allows this to be done separately without blocking the English implementation.

## Edge Cases Handled

1. **Multiple phases**: First turn detection happens per-phase, so Phase 2 first turn gets appropriate explanation
2. **Config override**: `include_experiment_explanation_each_turn=True` respects existing behavior
3. **Memory updates**: Continue using brief explanation in prompts to avoid token bloat
