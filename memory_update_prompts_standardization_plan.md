# Memory Update Prompts Standardization Plan

## Executive Summary
This plan outlines the systematic insertion of standardized memory instruction text across all memory update prompts in English, Spanish, and Mandarin language files. The goal is to ensure consistent memory management guidance for all experiment participants while resolving existing overlap conflicts.

## Background
The experiment uses 9 different memory update prompts across 3 languages (27 total prompts). These prompts guide AI agents on how to update their memory during the experiment. Currently, only the first prompt (`memory_memory_update_prompt`) contains memory management instructions, creating inconsistency across prompts.

## Text to Standardize
The following standardized instruction will be inserted as the second paragraph in all applicable memory update prompts:

```
Important: Your memory is given to you in every interaction and gives you your knowledge on yourself, the previous interactions and the experiment. Do not include your name, personality or bank account since they are given to you in every interaction. Structure your memory as it fits you best. You are given your previous memory and recent activity of the experiment.
```

## Critical Conflict Resolution

### OVERLAP ISSUE: Prompt 1 Conflict
**Problem**: The `memory_memory_update_prompt` in all languages already contains similar instructions:
- "Your memory is given to you in every interaction and gives you your knowledge on yourself and the experiment."
- "Do not include your name, personality or bank account since they are given to you in every interaction."
- "Structure your memory as it fits you best. You are given your previous memory and recent activity of the experiment."

**Solution**: Replace the existing 3-line block with the new standardized 4-line text:
- Adds "Important:" prefix for emphasis
- Adds "the previous interactions and" for completeness

## Scope of Changes

### Affected Prompts (9 per language = 27 total)
1. ✅ `memory_memory_update_prompt` - **REPLACE** overlapping text
2. ✅ `memory_memory_update_prompt_no_recent_activity` - **INSERT** new paragraph
3. ✅ `memory_narrative_update_prompt` - **INSERT** new paragraph
4. ✅ `memory_narrative_update_prompt_no_recent_activity` - **INSERT** new paragraph
5. ✅ `memory_memory_update_prompt_first_round` - **INSERT** new paragraph
6. ✅ `memory_memory_update_prompt_first_round_no_recent_activity` - **INSERT** new paragraph
7. ✅ `memory_narrative_update_prompt_first_round` - **INSERT** new paragraph
8. ✅ `memory_narrative_update_prompt_first_round_no_recent_activity` - **INSERT** new paragraph
9. ❌ `memory_compression_prompt` - **SKIP** (different structure, no "Your Previous Memory:" section)

### Languages (3 total)
- English: `translations/english_prompts.json`
- Spanish: `translations/spanish_prompts.json`
- Mandarin: `translations/mandarin_prompts.json`

## Implementation Strategy

### Insertion Position
**Standard Position**: Insert as the second paragraph, immediately before the "Your Previous Memory:" line.

**Example Transformation**:
```diff
Return your complete updated memory incorporating insights from the recent activity.
+ Important: Your memory is given to you in every interaction and gives you your knowledge on yourself, the previous interactions and the experiment. Do not include your name, personality or bank account since they are given to you in every interaction. Structure your memory as it fits you best. You are given your previous memory and recent activity of the experiment.

Your Previous Memory:
{current_memory}
```

### Prompt 1 Special Handling
For `memory_memory_update_prompt` only, **replace** the existing instructions:

**BEFORE**:
```
Your memory is given to you in every interaction and gives you your knowledge on yourself and the experiment.

Do not include your name, personality or bank account since they are given to you in every interaction.

Structure your memory as it fits you best. You are given your previous memory and recent activity of the experiment. Return the complete memory.
```

**AFTER**:
```
Important: Your memory is given to you in every interaction and gives you your knowledge on yourself, the previous interactions and the experiment. Do not include your name, personality or bank account since they are given to you in every interaction. Structure your memory as it fits you best. You are given your previous memory and recent activity of the experiment. Return the complete memory.
```

## Language-Specific Translations Required

### Spanish Translation
```
Importante: Tu memoria se te da en cada interacción y te proporciona tu conocimiento sobre ti mismo, las interacciones anteriores y el experimento. No incluyas tu nombre, personalidad o cuenta bancaria ya que se te dan en cada interacción. Estructura tu memoria como mejor te convenga. Se te da tu memoria anterior y la actividad reciente del experimento.
```

### Mandarin Translation
```
重要：你的记忆在每次互动中都会提供给你，并给你关于你自己、之前的互动和实验的知识。不要包括你的姓名、性格或银行账户，因为它们在每次互动中都会给你。以最适合你的方式构建你的记忆。你会得到你之前的记忆和实验的最近活动。
```

## Implementation Steps

### Phase 1: Preparation
1. **Backup all translation files**
2. **Create test cases** for each prompt type to validate changes
3. **Prepare translated versions** of the standardized text

### Phase 2: English Implementation (3 hours)
1. **Prompt 1**: Replace overlapping text in `memory_memory_update_prompt`
2. **Prompts 2-8**: Insert standardized text as second paragraph
3. **Prompt 9**: Skip `memory_compression_prompt`
4. **Validate**: Run syntax check and basic prompt parsing tests

### Phase 3: Spanish Implementation (3 hours)
1. **Translate** standardized text to Spanish
2. **Apply same logic** as English implementation
3. **Validate** Spanish prompts for correct insertion

### Phase 4: Mandarin Implementation (3 hours)
1. **Translate** standardized text to Mandarin
2. **Apply same logic** as English implementation
3. **Validate** Mandarin prompts for correct insertion

### Phase 5: Testing & Validation (4 hours)
1. **Syntax validation**: Ensure all JSON files are valid
2. **Integration testing**: Run memory update scenarios with modified prompts
3. **Cross-language consistency**: Verify translations convey same meaning
4. **Regression testing**: Ensure no existing functionality breaks

## Risk Mitigation
- **Backup Strategy**: Full file backups before any changes
- **Incremental Changes**: Modify one language at a time
- **Validation Checks**: JSON syntax validation after each change
- **Rollback Plan**: Ability to revert to backups if issues arise

## Success Criteria
- ✅ All 24 applicable prompts (8 × 3 languages) contain standardized text
- ✅ Prompt 1 overlap resolved correctly in all languages
- ✅ All JSON files remain syntactically valid
- ✅ Memory update functionality works correctly in testing
- ✅ Consistent guidance across all languages and prompt types

## Timeline
- **Total Time**: ~13 hours
- **Phase 1**: 1 hour
- **Phase 2**: 3 hours
- **Phase 3**: 3 hours
- **Phase 4**: 3 hours
- **Phase 5**: 3 hours

## Files to Modify
- `translations/english_prompts.json`
- `translations/spanish_prompts.json`
- `translations/mandarin_prompts.json`

## Testing Requirements
- JSON syntax validation
- Memory update prompt parsing tests
- Integration tests with actual memory update scenarios
- Multi-language consistency validation

---

**Document Version**: 1.0
**Date**: 2025-01-03
**Author**: AI Assistant
**Status**: Ready for Implementation