# Ranking Reasoning Removal Implementation Plan

## Issue Summary

Agents are currently being asked to provide reasoning when ranking justice principles throughout the experiment. The user wants to streamline the ranking process to only collect:
1. Rankings of the four justice principles (1-4)
2. Certainty levels using the existing scale (very_unsure, unsure, no_opinion, sure, very_sure)

Reasoning requirements should be removed from all ranking prompts while preserving the core ranking and certainty functionality.

## Root Cause Analysis

The framework currently requests reasoning in multiple ranking contexts:

### Phase 1 Ranking Locations
1. **Initial Ranking** (`phase1_initial_ranking_prompt_template`) - Currently only requests ranking + certainty (no reasoning)
2. **Post-Explanation Ranking** (`phase1_post_explanation_ranking_prompt`) - Requests consideration prompts and asks to "note any changes"
3. **Final Ranking** (`phase1_final_ranking_after_experience`) - Explicitly requests explanation: "Then explain how your experience in the four application rounds influenced your ranking"

### Phase 2 Ranking Location
1. **Final Ranking** (`phase2_final_ranking_prompt`) - Currently clean (only ranking + certainty)

### Application Rounds (Not Rankings, but Related)
- Phase 1 application rounds request "4. Explain your reasoning in detail" - but these are principle choice selections, not rankings

## Affected Components

### Core Files Requiring Changes
1. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`**
   - `phase1_post_explanation_ranking_prompt` 
   - `phase1_final_ranking_after_experience`

2. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`**
   - `phase1_round5_final_ranking` (equivalent to final ranking)
   - May need to verify other keys

3. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`**
   - Corresponding Mandarin prompts

### Code Files Using These Prompts
1. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase1_manager.py`**
   - `_build_post_explanation_ranking_prompt()` - line 537
   - `_build_final_ranking_prompt()` - line 553

2. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`**
   - `collect_final_rankings()` method uses `phase2_final_ranking_prompt`

### Parsing and Validation
- **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/experiment_agents/utility_agent.py`**
   - `parse_principle_ranking_enhanced()` - Currently handles JSON parsing correctly, should continue to work

## Implementation Strategy

### Step 1: English Translation Updates
**Target**: Remove reasoning requirements from ranking prompts

**Changes Needed**:
1. **`phase1_post_explanation_ranking_prompt`**: 
   - Remove "Consider:" section with three bullet points
   - Remove "noting any changes from your initial ranking" instruction
   - Keep only: ranking request + certainty request + response format

2. **`phase1_final_ranking_after_experience`**:
   - Remove "Then explain how your experience in the four application rounds influenced your ranking" instruction
   - Remove reasoning example: "After applying these principles, I learned that..."
   - Keep only: ranking request + certainty request + response format

### Step 2: Spanish Translation Updates
**Target**: Update corresponding Spanish prompts

**Changes Needed**:
1. **`phase1_round5_final_ranking`**:
   - Remove "A continuación, explique cómo ha influido su experiencia en las cuatro rondas de aplicación en su clasificación"
   - Remove reasoning example: "Después de aplicar estos principios, he aprendido que..."
   - Keep only: ranking + certainty + format

### Step 3: Mandarin Translation Updates  
**Target**: Update corresponding Mandarin prompts

**Investigation Needed**:
- Locate equivalent Mandarin ranking prompts
- Remove reasoning requirements while preserving ranking + certainty

### Step 4: Validation and Testing
**Target**: Ensure parsing and functionality remain intact

**Requirements**:
- Verify utility agent parsing continues to work correctly
- Confirm ranking collection in Phase1Manager and CounterfactualsService
- Test multilingual functionality across all three languages

## Technical Considerations

### Existing Certainty Scale
The framework already uses the correct 5-level certainty scale:
- `very_unsure` 
- `unsure`
- `no_opinion`
- `sure`
- `very_sure`

This scale is properly defined in all three languages and should be preserved.

### Parsing System Compatibility
The utility agent's `parse_principle_ranking_enhanced()` method expects:
```json
{
  "rankings": [
    {"principle": "maximizing_floor", "rank": 1},
    {"principle": "maximizing_average", "rank": 2},
    {"principle": "maximizing_average_floor_constraint", "rank": 3}, 
    {"principle": "maximizing_average_range_constraint", "rank": 4}
  ],
  "certainty": "sure"
}
```

The updated prompts must still generate responses that can be parsed into this format.

### Response Format Preservation
Current ranking prompts use this format:
```
1. [Your best choice]
2. [Your second choice] 
3. [Your third choice]
4. [Your worst choice]

Overall certainty: [certainty_level]
```

This format should be preserved as it's compatible with existing parsing logic.

## Testing Strategy

### Unit Tests
1. **Translation Consistency**: Verify all three languages have equivalent prompts
2. **Parsing Validation**: Ensure updated prompts generate parseable responses
3. **Ranking Extraction**: Confirm utility agent can extract rankings and certainty

### Integration Tests  
1. **Phase 1 Flow**: Test complete Phase 1 ranking collection (initial, post-explanation, final)
2. **Phase 2 Flow**: Verify CounterfactualsService final ranking collection
3. **Multilingual Testing**: Test all three languages end-to-end

### Example Response Validation
Test that responses like this are still parseable:
```
1. Maximizing floor income
2. Maximizing average with floor constraint  
3. Maximizing average income
4. Maximizing average with range constraint

Overall certainty: sure
```

## Risk Assessment

### Low Risk Areas
- **Phase 2 final ranking**: Already clean, no changes needed
- **Initial Phase 1 ranking**: Already clean, no changes needed  
- **Parsing system**: Robust JSON extraction should handle simplified responses

### Medium Risk Areas  
- **Translation consistency**: Must ensure all three languages are updated consistently
- **Response format preservation**: Must maintain parseable format structure

### Mitigation Strategies
1. **Backup Current Files**: Create backups before modifications
2. **Incremental Testing**: Test each language individually  
3. **Validation Scripts**: Run existing test suites to catch regressions
4. **Example Response Testing**: Verify sample responses parse correctly

## Timeline Estimation

### Phase 1: English Updates (30 minutes)
- Update 2 English prompts
- Test parsing with simplified responses

### Phase 2: Spanish Updates (30 minutes)  
- Update equivalent Spanish prompts
- Validate translation consistency

### Phase 3: Mandarin Updates (45 minutes)
- Locate and update Mandarin prompts
- Handle potential character encoding considerations

### Phase 4: Testing and Validation (45 minutes)
- Run existing test suites  
- Test multilingual functionality
- Validate end-to-end ranking collection

### Total Estimated Time: 2.5 hours

## Dependencies

### Prerequisites
- Access to translation files (English, Spanish, Mandarin)
- Understanding of existing parsing format requirements
- Test environment for validation

### Blocking Factors
- None identified - this is a straightforward content modification task

## Success Criteria

1. **All ranking prompts request only rankings and certainty levels**
2. **No reasoning explanations are requested in any ranking context**  
3. **Existing certainty scale is preserved across all languages**
4. **Parsing system continues to extract rankings and certainty correctly**
5. **All three languages (English, Spanish, Mandarin) are updated consistently**
6. **Existing test suites pass without regressions**

## Implementation Notes

### Key Prompt Identifiers
- `phase1_post_explanation_ranking_prompt` (English)
- `phase1_final_ranking_after_experience` (English)  
- `phase1_round5_final_ranking` (Spanish)
- Equivalent Mandarin keys (to be identified)

### Preserved Elements
- Four-level ranking structure (1-4)
- Certainty scale (5 levels)
- Response format structure
- Principle name consistency
- JSON parsing compatibility

### Removed Elements  
- "Consider:" sections with reasoning prompts
- "Then explain..." instructions
- Reasoning examples in prompt templates
- Any text requesting explanations or justifications

This plan provides a systematic approach to removing reasoning requirements from all ranking contexts while preserving the core ranking and certainty collection functionality that the experiment requires.