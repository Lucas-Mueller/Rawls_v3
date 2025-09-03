# Ranking Prompt Structure Analysis Report

## Executive Summary

After conducting a comprehensive analysis of the current ranking prompt structure, I've identified significant redundancy in how we present justice principle information to agents. The system currently presents the same principle information **3 times** across different prompts, creating unnecessary complexity and potential inconsistency.

## Current Implementation Analysis

### 1. Principle Information Sources

The current system delivers justice principle information through multiple channels:

#### A. System Instructions (Agent Context)
Location: `utils/language_manager.py` → `format_context_info()` → `experiment_explanation`
- Contains basic principle definitions
- Part of the agent's system context
- Always present during ranking requests

#### B. Input Prompts (Task-Specific)
Location: `translations/english_prompts.json`
- **Initial Ranking**: `phase1_initial_ranking_prompt_template`
- **Post-Explanation Ranking**: `phase1_post_explanation_ranking_prompt`  
- **Final Ranking**: `phase1_final_ranking_after_experience`
- **Phase 2 Final Ranking**: `phase2_final_ranking_prompt`

#### C. Phase-Specific Instructions  
Location: Through `_get_phase_specific_instructions_translated()`
- Additional contextual information based on current phase
- May include experiment explanations

### 2. Redundancy Analysis

#### Current Phase 1 Initial Ranking Structure:
1. **System Context** (via `format_context_info`): Contains general experiment explanation
2. **Input Prompt**: Full detailed principle descriptions with examples
3. **Instructions**: Response format specifications

#### Current Phase 2 Final Ranking Structure:
1. **System Context**: Experiment background 
2. **Input Prompt**: Complete principle definitions + ranking request + format instructions
3. **Context**: Previous discussion history and results

### 3. Principle Definition Variations

The system currently uses **3 different versions** of principle descriptions:

#### Version 1: Common Principle Descriptions (Short)
```json
"principle_descriptions": {
  "maximizing_floor": "Choose the distribution that maximizes the lowest income in society",
  "maximizing_average": "Choose the distribution that maximizes the average income",
  // ... etc
}
```

#### Version 2: Phase 1 Detailed (Long)
```
"1. **Maximizing Floor Income**: The most just distribution of income is that which maximizes the floor (or lowest) income in the society. This principle considers only the welfare of the worst-off individual in society."
```

#### Version 3: Phase 2 Final Ranking (Medium)
```
"Maximizing the floor income: The most just distribution of income is that which maximizes the floor (or lowest) income in the society. This principle considers only the welfare of the worst-off individual in society."
```

### 4. Code Locations & Dependencies

#### Primary Ranking Methods:
- **Phase 1 Manager**: `core/phase1_manager.py`
  - `_step_1_1_initial_ranking()` (line 250)
  - `_step_1_2b_post_explanation_ranking()` (line 464) 
  - `_step_1_4_final_ranking()` (line 489)

#### Phase 2 Manager:
- **Counterfactuals Service**: `core/services/counterfactuals_service.py`
  - `collect_final_rankings()` (line 206)
  - `collect_final_rankings_streamlined()` (line 260)

#### Translation Files:
- **English**: `translations/english_prompts.json`
  - Multiple ranking prompt templates with full principle definitions
- **Spanish/Mandarin**: Equivalent structures in respective files

#### Utility Parsing:
- **Utility Agent**: `experiment_agents/utility_agent.py`
  - Parses ranking responses using `parse_principle_ranking_enhanced()`

## System Architecture Impact

### Memory Context System
The current architecture uses a sophisticated memory management system where:
1. **Agent System Instructions** are dynamically generated via `_generate_dynamic_instructions()`
2. **Context Information** is formatted through `format_context_info()` including experiment explanations
3. **Phase-Specific Instructions** are added based on current experiment state

### Language Management
- **Multi-language Support**: All prompts are managed through `LanguageManager`
- **Translation Consistency**: Each language file must maintain 3+ versions of principle descriptions
- **Format Variations**: Different prompt templates for different ranking contexts

## Simplification Opportunities

### Primary Redundancy
**The core issue**: Agents receive principle information through:
1. System context (general background)
2. Input prompt (detailed descriptions)  
3. Previous interactions (accumulated knowledge)

### User's Proposed Solution
Move to single-source principle information:
- Remove detailed descriptions from system context
- Consolidate to input prompt only
- Use consistent principle descriptions across all ranking requests

## Impact Assessment

### Current Complexity Metrics:
- **4 different ranking prompt templates** across phases
- **3 versions of principle descriptions** with slight variations
- **2 system-level contexts** that may include principle information
- **Multiple parsing pathways** for ranking responses

### Translation Maintenance Burden:
- Each language file contains duplicate principle information
- Inconsistencies can emerge between versions
- Updates require changes in multiple locations

### Agent Context Efficiency:
- Current system may exceed optimal context window usage
- Redundant information reduces space for actual memory/history
- Parsing complexity due to varied formats

## Recommended Systematic Approach

### Phase 1: Analysis & Planning ✅
- [x] Identify all ranking prompt calls
- [x] Document current implementation structure  
- [x] Analyze redundancy patterns
- [x] Assess system architecture impact

### Phase 2: Design Simplification Strategy
- [ ] Design unified principle description format
- [ ] Plan system context reduction strategy
- [ ] Design consolidated prompt templates
- [ ] Validate translation consistency requirements

### Phase 3: Implementation Planning  
- [ ] Create implementation order (avoid breaking changes)
- [ ] Plan backward compatibility during transition
- [ ] Design test coverage for prompt changes
- [ ] Plan language file consolidation

### Phase 4: Implementation & Testing
- [ ] Update prompt templates with consolidated format
- [ ] Modify system context generation
- [ ] Update parsing logic if needed
- [ ] Test across all languages and phases

### Phase 5: Validation & Cleanup
- [ ] Verify response consistency across simplification
- [ ] Remove unused prompt templates
- [ ] Clean up language manager methods
- [ ] Update documentation

## Risk Assessment

### Low Risk Items:
- Consolidating principle descriptions (same information, cleaner delivery)
- Removing system context redundancy (agents still get full information)
- Standardizing response formats

### Medium Risk Items:
- Changing long-established prompt templates
- Modifying multilingual content (requires careful translation review)
- Updating parsing logic dependencies

### High Risk Items:
- Breaking agent context expectations
- Disrupting established response patterns
- Creating inconsistencies between phases

## Recommendations

### Immediate Actions:
1. **Principle Description Audit**: Verify all versions communicate the same meaning
2. **Format Standardization**: Choose one response format specification 
3. **Translation Review**: Ensure language consistency before changes

### Implementation Strategy:
1. **Conservative Approach**: Start with Phase 1 ranking prompts only
2. **Iterative Testing**: Validate each change with existing test suite
3. **Backward Compatibility**: Maintain existing functionality during transition

### Success Metrics:
- Reduced total character count in ranking prompts
- Maintained response parsing accuracy  
- Consistent principle understanding across languages
- Simplified maintenance burden for translations

## Conclusion

The current ranking prompt structure exhibits significant redundancy that can be simplified without loss of functionality. The user's suggestion to consolidate principle information into input prompts only is sound and aligns with simplification principles.

**Key Benefits of Simplification:**
- Reduced maintenance complexity
- Improved translation consistency
- More efficient context window usage
- Cleaner agent instruction architecture

**Recommended Next Steps:**
1. Implement the systematic approach outlined above
2. Start with Phase 1 ranking prompts as proof of concept
3. Validate parsing accuracy with simplified prompts
4. Extend to Phase 2 after successful Phase 1 implementation

This analysis supports proceeding with the simplification while maintaining systematic rigor to ensure no functionality is lost during the transition.