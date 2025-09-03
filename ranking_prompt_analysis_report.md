# Ranking Prompt Analysis Report: Phase 1 & Phase 2

## Executive Summary

This comprehensive analysis examines all ranking prompt constructions across Phase 1 and Phase 2 of the Frohlich Experiment. The analysis reveals systematic design patterns, multilingual consistency, and significant redundancy in how justice principle information is presented to agents. The system currently presents the same principle information **3 times** across different prompts, creating unnecessary complexity and potential inconsistency.

## Ranking Prompt Locations and Architecture

### Phase 1 Ranking Prompts

#### 1. Initial Ranking (`core/phase1_manager.py:258`)
- **Location**: `core/phase1_manager.py`, `_step_1_1_initial_ranking()` method
- **Prompt Key**: `prompts.phase1_initial_ranking_prompt_template`
- **Purpose**: First-time principle ranking before any experience
- **Construction Method**: Direct language manager lookup
- **Processing**: Enhanced utility agent parsing via `parse_principle_ranking_enhanced()`

#### 2. Post-Explanation Ranking (`core/phase1_manager.py:472`)
- **Location**: `core/phase1_manager.py`, `_step_1_2b_post_explanation_ranking()` method
- **Prompt Key**: `prompts.phase1_post_explanation_ranking_prompt`
- **Purpose**: Re-ranking after learning principle applications
- **Construction Method**: Direct language manager lookup
- **Processing**: Enhanced utility agent parsing via `parse_principle_ranking_enhanced()`

#### 3. Final Ranking (`core/phase1_manager.py:497`)
- **Location**: `core/phase1_manager.py`, `_step_1_4_final_ranking()` method
- **Prompt Key**: `prompts.phase1_final_ranking_after_experience`
- **Purpose**: Final ranking after experiencing all 4 application rounds
- **Construction Method**: Direct language manager lookup
- **Processing**: Enhanced utility agent parsing via `parse_principle_ranking_enhanced()`

### Phase 2 Ranking Prompts

#### 1. Final Ranking (`core/services/counterfactuals_service.py:704`, `core/services/counterfactuals_service.py:751`)
- **Location**: `core/services/counterfactuals_service.py`, both `_get_final_ranking_task()` and `_get_final_ranking_task_streamlined()` methods
- **Prompt Key**: `prompts.phase2_final_ranking_prompt`
- **Purpose**: Final principle ranking after group discussion and results delivery
- **Construction Method**: Direct language manager lookup
- **Processing**: Enhanced utility agent parsing via `parse_principle_ranking_enhanced()`

## Multilingual Translation Analysis

### English (`translations/english_prompts.json`)

**Initial Ranking Template** (lines 66-67):
```json
"phase1_initial_ranking_prompt_template": "This is your first time ranking these four principles of justice..."
```

**Post-Explanation Ranking** (lines 65):
```json
"phase1_post_explanation_ranking_prompt": "After learning how each justice principle is applied..."
```

**Final Ranking After Experience** (lines 68):
```json
"phase1_final_ranking_after_experience": "After experiencing the four rounds of principle application..."
```

**Phase 2 Final Ranking** (lines 71):
```json
"phase2_final_ranking_prompt": "CURRENT TASK: The Four Justice Principles..."
```

### Spanish (`translations/spanish_prompts.json`)

**Translations Present** (lines 63-66, 119, 147, 156, 158):
- All Phase 1 ranking prompts are properly translated
- Phase 2 final ranking prompt is properly translated
- Consistent formatting and instruction structure maintained

**Key Observations**:
- Format instructions preserved across languages
- Response examples adapted appropriately
- Certainty level translations consistent

### Mandarin (`translations/mandarin_prompts.json`)

**Translations Present** (lines 63, 84, 90, 150-152):
- All ranking prompts properly translated
- Chinese-appropriate formatting maintained
- Consistent principle descriptions and examples

**Key Observations**:
- Numbering and formatting adapted to Chinese conventions
- Response structure preserved
- Certainty levels appropriately translated

## Principle Information Redundancy Analysis

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

### Redundancy Analysis

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

## Systematic Todo List for Ranking Prompt Improvements

### Phase 1: Foundation Analysis and Standardization

#### 1.1 Principle Description Standardization
- [ ] **Extract Common Principle Descriptions**: Create reusable templates in translation files
- [ ] **Audit Current Variations**: Document all 3 versions of principle descriptions across prompts
- [ ] **Standardize Principle Definitions**: Choose one canonical version for consistency
- [ ] **Update All Ranking Prompts**: Replace inline descriptions with standardized template references
- [ ] **Validate Translation Consistency**: Ensure standardized descriptions work across English, Spanish, and Mandarin
- [ ] **Test Parsing Compatibility**: Verify utility agent parsing works with standardized descriptions

#### 1.2 Phase 1 Ranking Prompt Refinement
- [ ] **Review Initial Ranking Prompt**: Optimize first-time ranking instructions for clarity
- [ ] **Enhance Post-Explanation Context**: Better acknowledge learned experience from detailed explanation
- [ ] **Improve Final Ranking Context**: Stronger reference to application rounds experience
- [ ] **Standardize Response Examples**: Use consistent example formats across all Phase 1 prompts
- [ ] **Consolidate Response Format Instructions**: Single template for ranking format specification

#### 1.3 Multilingual Consistency Validation
- [ ] **Spanish Translation Review**: Verify all ranking prompts maintain consistent terminology
- [ ] **Mandarin Translation Review**: Ensure cultural appropriateness and format consistency
- [ ] **Cross-Language Format Testing**: Validate response parsing works identically across languages
- [ ] **Translation Template Creation**: Build reusable translation templates for principle descriptions

### Phase 2: Service Layer and Architecture Optimization

#### 2.1 CounterfactualsService Consolidation
- [ ] **Complete Migration to Streamlined Approach**: Update all callers to use `collect_final_rankings_streamlined()`
- [ ] **Add Deprecation Warnings**: Mark `collect_final_rankings()` legacy method as deprecated
- [ ] **Update Phase2Manager Integration**: Ensure clean service usage in Phase2Manager
- [ ] **Remove Legacy Code**: Clean up compatibility methods after transition period
- [ ] **Update Service Documentation**: Reflect new streamlined architecture

#### 2.2 Phase 2 Prompt Enhancement
- [ ] **Add Discussion Context Integration**: Optional summary of group discussion in ranking prompt
- [ ] **Include Consensus Acknowledgment**: Reference consensus outcome in prompt context
- [ ] **Enhance Social Interaction Context**: Better acknowledge collaborative experience vs individual Phase 1
- [ ] **Optimize Context Window Usage**: Remove redundant information from Phase 2 ranking prompts
- [ ] **Validate Multilingual Enhancements**: Ensure improvements work across all languages

#### 2.3 Service Layer Error Handling
- [ ] **Implement Progressive Prompt Simplification**: Simpler prompts on parsing failures
- [ ] **Add Ranking Response Validation**: Quality checks before accepting rankings
- [ ] **Create Fallback Ranking Generation**: Improved default rankings on complete failure
- [ ] **Implement Smart Retry Logic**: Retry mechanisms with modified prompts on failures

### Phase 3: System-Wide Redundancy Elimination

#### 3.1 Context Information Cleanup
- [ ] **Audit System Context Information**: Review experiment explanation redundancy
- [ ] **Remove Principle Info from System Context**: Move all principle info to input prompts only
- [ ] **Optimize Context Window Usage**: Reduce total character count in agent context
- [ ] **Validate Agent Understanding**: Ensure agents still understand principles with consolidated approach

#### 3.2 Prompt Template Consolidation
- [ ] **Create Master Principle Template**: Single source of truth for principle descriptions
- [ ] **Consolidate Format Instructions**: Single response format template
- [ ] **Reduce Template Count**: Minimize number of distinct ranking prompt templates
- [ ] **Create Dynamic Prompt Builder**: Build prompts from reusable components

#### 3.3 Translation File Optimization
- [ ] **Eliminate Duplicate Translations**: Remove redundant principle descriptions
- [ ] **Create Translation Template System**: Reusable components for all languages
- [ ] **Reduce Translation Maintenance**: Minimize locations requiring updates
- [ ] **Implement Translation Validation**: Automated consistency checks

### Phase 4: Advanced Features and Quality Assurance

#### 4.1 Validation and Testing Framework
- [ ] **Create Prompt Content Validation**: Automated checks for prompt consistency
- [ ] **Implement Ranking Quality Metrics**: Measures of ranking response quality and consistency
- [ ] **Build Prompt Effectiveness Testing**: A/B testing framework for prompt optimization
- [ ] **Add Regression Testing**: Prevent quality degradation during prompt changes
- [ ] **Create Integration Test Suite**: End-to-end ranking collection testing

#### 4.2 Performance Optimization
- [ ] **Measure Prompt Performance**: Analyze success rates and response times
- [ ] **Optimize Context Length**: Minimize unnecessary tokens in ranking prompts
- [ ] **Implement Caching**: Cache parsed ranking responses for efficiency
- [ ] **Monitor Ranking Consistency**: Track ranking stability across prompts

#### 4.3 Documentation and Maintenance
- [ ] **Update Architecture Documentation**: Reflect simplified ranking system
- [ ] **Create Maintenance Guidelines**: How to modify ranking prompts safely
- [ ] **Build Developer Tools**: Utilities for prompt testing and validation
- [ ] **Create Translation Workflow**: Process for updating multilingual content

### Phase 5: Long-term Enhancements

#### 5.1 Dynamic Prompt Optimization
- [ ] **Implement Context-Aware Prompts**: Adapt prompts based on participant performance
- [ ] **Add Personalization Layer**: Adjust prompt complexity based on agent capabilities
- [ ] **Create Adaptive Examples**: Dynamic example selection based on participant progress
- [ ] **Implement Cultural Adaptation**: Region-specific prompt optimizations

#### 5.2 Analytics and Monitoring
- [ ] **Add Ranking Prompt Performance Metrics**: Track success rates and quality scores
- [ ] **Implement Real-time Monitoring**: Alert on ranking prompt failures
- [ ] **Create Ranking Analysis Dashboard**: Visual analysis of ranking patterns
- [ ] **Build Comparative Analysis Tools**: Compare prompt effectiveness across versions

#### 5.3 Advanced Parsing and Response Handling
- [ ] **Implement Intelligent Parsing**: Better handling of varied response formats
- [ ] **Add Response Quality Scoring**: Automatic quality assessment of ranking responses
- [ ] **Create Response Enhancement**: Improve unclear or incomplete rankings
- [ ] **Implement Learning System**: Adapt prompts based on parsing success patterns

## Implementation Priority Matrix

### High Priority (Immediate Action)

1. **Principle Description Standardization** (Phase 1.1)
   - **Impact**: High - affects all ranking prompts across both phases
   - **Effort**: Low - template creation and replacement
   - **Risk**: Low - non-breaking change that improves consistency

2. **Service Layer Cleanup** (Phase 2.1)
   - **Impact**: Medium - simplifies codebase and reduces technical debt
   - **Effort**: Medium - deprecation and migration work
   - **Risk**: Medium - requires thorough testing of service integration

3. **Multilingual Consistency Validation** (Phase 1.3)
   - **Impact**: High - ensures quality across all supported languages
   - **Effort**: Medium - systematic review and testing
   - **Risk**: Low - validation and improvement without breaking changes

### Medium Priority (Next Sprint)

4. **Enhanced Context Integration** (Phase 2.2)
   - **Impact**: Medium - improves Phase 2 ranking quality and relevance
   - **Effort**: Medium - prompt modification and testing across languages
   - **Risk**: Low - additive enhancement that improves user experience

5. **Redundancy Elimination** (Phase 3.1-3.2)
   - **Impact**: High - reduces maintenance burden and improves efficiency
   - **Effort**: High - requires systematic refactoring across multiple components
   - **Risk**: Medium - affects core system behavior, requires extensive testing

6. **Error Handling Enhancement** (Phase 2.3)
   - **Impact**: High - improves system robustness and user experience
   - **Effort**: High - comprehensive retry and fallback logic
   - **Risk**: Medium - affects critical path, requires careful implementation

### Low Priority (Future Consideration)

7. **Validation Framework** (Phase 4.1)
   - **Impact**: Medium - quality assurance and long-term maintenance
   - **Effort**: High - new infrastructure and tooling
   - **Risk**: Low - separate from core functionality, additive improvements

8. **Advanced Features** (Phase 5.1-5.3)
   - **Impact**: Low - incremental improvements and optimization
   - **Effort**: High - research and development of new capabilities
   - **Risk**: Low - experimental features that don't affect core system

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

This comprehensive analysis of the ranking prompt system reveals a well-structured but complex architecture with significant opportunities for improvement. The system demonstrates strong multilingual consistency and clean service integration, while exhibiting redundancy patterns that can be systematically addressed.

### Key Findings

1. **Strong Foundation**: The ranking prompt system has consistent structure across all phases and languages
2. **Service Integration**: Clean separation of concerns with CounterfactualsService handling Phase 2 collections
3. **Redundancy Issues**: Multiple principle descriptions create maintenance burden and context inefficiency
4. **Translation Quality**: Excellent multilingual support with consistent formatting across English, Spanish, and Mandarin

### Strategic Recommendations

**Immediate Actions** (High Priority):
- Standardize principle descriptions across all prompts
- Complete service layer migration to streamlined approach  
- Validate multilingual consistency before major changes

**Medium-term Goals** (Medium Priority):
- Eliminate redundant information from system contexts
- Enhance Phase 2 prompts with discussion context
- Implement comprehensive error handling and retry logic

**Long-term Vision** (Low Priority):
- Dynamic prompt optimization based on performance
- Advanced analytics and monitoring capabilities
- Intelligent parsing and response enhancement

### Implementation Strategy

The systematic approach outlined in this report provides a clear pathway for incremental improvements:

1. **Foundation First**: Establish standardized templates and clean architecture
2. **Service Optimization**: Complete migration to streamlined service approach
3. **Redundancy Elimination**: Remove duplicate information systematically
4. **Quality Assurance**: Add comprehensive validation and testing
5. **Advanced Features**: Implement sophisticated optimization and monitoring

### Expected Benefits

**Short-term** (Phase 1-2):
- Reduced maintenance burden through standardization
- Improved consistency across languages and phases
- Cleaner codebase with deprecated legacy methods removed

**Medium-term** (Phase 3-4):
- More efficient context window usage
- Enhanced user experience with better error handling
- Comprehensive quality assurance and testing framework

**Long-term** (Phase 5):
- Adaptive and personalized ranking experience
- Data-driven prompt optimization
- Advanced monitoring and analytics capabilities

The ranking prompt system is well-positioned for these improvements, with existing strong foundations that enable systematic enhancement while maintaining stability and backward compatibility.