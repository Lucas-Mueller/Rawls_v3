# Phase 2 Memory Update Experiment Explanation Inclusion Plan

## Overview
Modify the memory update prompts in Phase 2 to include the experiment explanation during group discussions, excluding the first memory update and final ranking stages.

## Current State Analysis

### Memory Update Prompt Types
- `memory_memory_update_prompt`: Regular structured format, includes `{experiment_explanation}`
- `memory_narrative_update_prompt`: Narrative format, includes `{experiment_explanation}`
- `memory_memory_update_prompt_first_round`: Phase 2 first round structured, includes detailed Phase 2 explanation + `{experiment_explanation}`
- `memory_narrative_update_prompt_first_round`: Phase 2 first round narrative, includes detailed Phase 2 explanation + `{experiment_explanation}`
- `memory_memory_update_prompt_no_recent_activity`: Discussion variant structured, **does NOT include `{experiment_explanation}`**
- `memory_narrative_update_prompt_no_recent_activity`: Discussion variant narrative, **does NOT include `{experiment_explanation}`**

### Current Logic (memory_manager.py:329-348)
```python
experiment_explanation = ""
if context is not None:
    if phase == "phase_1":
        if context.first_memory_update:
            experiment_explanation = language_manager.get("prompts.initial_experiment_explanation")
        else:
            experiment_explanation = language_manager.get("prompts.experiment_explanation")
    elif context.first_memory_update:
        experiment_explanation = language_manager.get("prompts.experiment_explanation")
```

### Template Selection Logic
- Phase 2 first round: Uses `_first_round` templates (already include explanations)
- Phase 2 discussions (`interaction_type` in `{"internal_reasoning", "statement"}`): Uses `_no_recent_activity` variants
- Other interactions: Uses regular templates

## Required Changes

### 1. Translation File Modifications
Add `{experiment_explanation}` placeholder to the following templates in all language files:

**English (`translations/english_prompts.json`):**
- `memory_memory_update_prompt_no_recent_activity` (line 92)
- `memory_narrative_update_prompt_no_recent_activity` (line 94)

**Spanish (`translations/spanish_prompts.json`):**
- `memory_memory_update_prompt_no_recent_activity`
- `memory_narrative_update_prompt_no_recent_activity`

**Mandarin (`translations/mandarin_prompts.json`):**
- `memory_memory_update_prompt_no_recent_activity`
- `memory_narrative_update_prompt_no_recent_activity`

**Template Structure:**
```
{memory_narrative_update_prompt_no_recent_activity}

{experiment_explanation}

=== Current Discussion History ===
{round_content}
=======================================

Return: Your complete updated memory as a continuous narrative (do not add prefixes like 'Memory update:')
```

### 2. Memory Manager Logic Modification
Update `utils/memory_manager.py` `_create_memory_update_prompt` method (lines 329-348):

**New Logic:**
```python
experiment_explanation = ""
if context is not None:
    if phase == "phase_1":
        # Phase 1 logic unchanged
        if context.first_memory_update:
            experiment_explanation = language_manager.get("prompts.initial_experiment_explanation")
        else:
            experiment_explanation = language_manager.get("prompts.experiment_explanation")
    elif phase == "phase_2" and not context.first_memory_update:
        # Phase 2: Include explanation for discussion stages, exclude final ranking
        from models.experiment_types import ExperimentStage
        if (context.stage == ExperimentStage.DISCUSSION and
            interaction_type in {"internal_reasoning", "statement"}):
            experiment_explanation = language_manager.get("prompts.experiment_explanation")
    elif context.first_memory_update:
        # Preserve existing behavior for first memory update in other phases
        experiment_explanation = language_manager.get("prompts.experiment_explanation")
```

### 3. Affected Systems Analysis

#### Memory Update Flow
- **Phase 2 Group Discussions**: Now includes experiment explanation in every memory update (except first)
- **Phase 2 Final Ranking**: Excludes experiment explanation
- **Phase 2 First Memory Update**: Already includes detailed Phase 2 explanation, unchanged
- **Phase 1**: Unchanged behavior
- **Other Phase 2 Interactions** (voting, results): Unchanged

#### Configuration Integration
- Respects existing `include_experiment_explanation_each_turn` config setting
- Memory updates become more consistent with general experiment explanation inclusion logic
- Backward compatibility maintained - existing configs continue to work

#### Language Manager Integration
- No changes needed to language manager logic
- Memory manager override provides fine-grained control for Phase 2 discussions

### 4. Testing Requirements

#### Unit Tests
- Test memory manager logic with different phase/stage combinations
- Verify experiment_explanation inclusion for Phase 2 discussions
- Verify experiment_explanation exclusion for final ranking and first updates

#### Integration Tests
- Test full Phase 2 discussion flow with memory updates
- Verify prompts contain experiment explanation in correct contexts
- Test multilingual support (English, Spanish, Mandarin)

#### Regression Tests
- Ensure Phase 1 behavior unchanged
- Ensure non-discussion Phase 2 interactions unchanged
- Verify template selection logic still works correctly

### 5. Implementation Steps

1. **Update Translation Templates**
   - Add `{experiment_explanation}` placeholder to `_no_recent_activity` templates in all language files
   - Ensure proper placement within template structure

2. **Modify Memory Manager Logic**
   - Update experiment_explanation inclusion logic in `_create_memory_update_prompt`
   - Add import for `ExperimentStage` enum
   - Implement stage-based conditional logic

3. **Test Implementation**
   - Run existing test suite to ensure no regressions
   - Add specific tests for new Phase 2 discussion behavior
   - Verify multilingual template consistency

4. **Documentation Update**
   - Update CLAUDE.md with new memory update behavior
   - Document configuration implications

### 6. Risk Assessment

#### Low Risk
- Changes are localized to memory manager logic and translation templates
- Existing behavior preserved for Phase 1 and non-discussion Phase 2 interactions
- Template modifications are additive (adding placeholder)

#### Medium Risk
- Potential for inconsistent behavior across language files if templates not updated uniformly
- Need to ensure stage information is properly passed to memory manager

#### Mitigation Strategies
- Comprehensive testing across all language variants
- Gradual rollout with feature flags if needed
- Clear documentation of expected behavior

### 7. Success Criteria

- Phase 2 group discussion memory updates include experiment explanation
- First Phase 2 memory update behavior unchanged (still includes detailed explanation)
- Final ranking memory updates exclude experiment explanation
- All existing functionality preserved
- Tests pass across all language variants
- Configuration system continues to work as expected

## Conclusion

This plan provides a systematic approach to implementing the requested feature while maintaining backward compatibility and minimizing risk. The changes are focused and well-contained, affecting only the specific memory update contexts requested by the user.