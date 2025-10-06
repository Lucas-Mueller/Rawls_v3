# Plan to Remove Hardcoded Round Descriptions from Voting Initiation Prompts

## Problem Statement
During Phase 2 voting initiation, the prompts contain hardcoded round descriptions like "Voting Decision Point - Round 1 of 10" which are redundant since the correct round description is already provided in the instruction prompt context. This hardcoded text needs to be removed for all supported languages (English, Spanish, Mandarin).

## Analysis Results
The hardcoded round descriptions appear in the following voting initiation prompts across all three language files:

### Affected Prompts
1. `vote_initiation_prompt`
2. `vote_initiation_with_statement_prompt`
3. `vote_initiation_with_reasoning_prompt`

### Unaffected Prompts
- `vote_initiation_with_statement_and_reasoning_prompt` (does not contain hardcoded round description)

## Language-Specific Changes Required

### English (`translations/english_prompts.json`)
**Current hardcoded text to remove:**
- `"Voting Decision Point - Round {round_number} of {max_rounds}\n\n"`

**Affected prompt keys:**
- `vote_initiation_prompt` (line ~75)
- `vote_initiation_with_statement_prompt` (line ~76)
- `vote_initiation_with_reasoning_prompt` (line ~77)

### Spanish (`translations/spanish_prompts.json`)
**Current hardcoded text to remove:**
- `"Punto de Decisión de Votación - Ronda {round_number} de {max_rounds}\n\n"`

**Affected prompt keys:**
- `vote_initiation_prompt` (line ~79)
- `vote_initiation_with_statement_prompt` (line ~80)
- `vote_initiation_with_reasoning_prompt` (line ~177)

### Mandarin (`translations/mandarin_prompts.json`)
**Current hardcoded text to remove:**
- `"投票决定点 - 第{round_number}轮，共{max_rounds}轮\n\n"`

**Affected prompt keys:**
- `vote_initiation_prompt` (line ~168)
- `vote_initiation_with_statement_prompt` (line ~169)
- `vote_initiation_with_reasoning_prompt` (line ~170)

## Implementation Plan

### Step 1: Verify Current State
- Confirm that the hardcoded round descriptions are present in all three language files
- Ensure no other prompts contain similar hardcoded round information

### Step 2: Make Changes Sequentially by Language
For each language file, remove the hardcoded round description from the beginning of each affected prompt while preserving the rest of the prompt content.

### Step 3: Test Changes
- Run existing tests to ensure no functionality is broken
- Verify that voting initiation still works correctly in all languages
- Check that the round information is still properly conveyed through the instruction context

### Step 4: Validate Multilingual Consistency
- Ensure that all three language files have consistent prompt structures after the changes
- Verify that no translation keys are missing or malformed

## Risk Assessment
- **Low Risk**: This is a cosmetic change that removes redundant information
- **Impact**: Prompts will be cleaner and less repetitive
- **Testing**: Existing test suite should catch any formatting issues

## Expected Outcome
After implementing these changes, the voting initiation prompts will start directly with the voting explanation content instead of the redundant round header, while the proper round context remains available through the instruction prompt system.