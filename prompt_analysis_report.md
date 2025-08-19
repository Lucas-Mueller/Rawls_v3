# Frohlich Experiment Prompt Structure Analysis Report

## Executive Summary

After conducting a comprehensive analysis of the prompt structure across the Frohlich Experiment system, several critical issues and improvement opportunities have been identified. While the system demonstrates good architectural principles with its language manager approach, there are significant inconsistencies, hardcoded elements, and opportunities for optimization.

## Key Findings

### 1. Critical Issues

#### 1.1 Hardcoded Prompts Bypassing Language Manager

**Issue**: Multiple critical prompts are hardcoded and bypass the language manager system, breaking multi-language support.

**Locations**:
- `core/phase1_manager.py` lines 464-486: `_build_application_prompt()` method contains hardcoded English-only prompt
- `core/phase2_manager.py` lines 634-648: Secret ballot voting prompt is hardcoded
- `core/phase2_manager.py` lines 540-546: Vote agreement prompt is hardcoded

**Impact**: 
- Multi-language experiments will fail when these prompts are used
- Inconsistent user experience across languages
- Maintenance burden due to duplication

**Specific Examples**:

```python
# In phase1_manager.py - HARDCODED
def _build_application_prompt(self, distribution_set, round_num: int) -> str:
    return f"""
ROUND {round_num}

{distributions_table}

You are to make a choice from among the four principles of justice which are mentioned above:
(a) maximizing the floor,
(b) maximizing the average,
(c) maximizing the average with a floor constraint, and
(d) maximizing the average with a range constraint.
...
"""

# In phase2_manager.py - HARDCODED  
voting_prompt = """
SECRET BALLOT VOTE

Choose ONE of the four justice principles for the group to adopt:
(a) maximizing the floor
(b) maximizing the average  
(c) maximizing the average with a floor constraint
(d) maximizing the average with a range constraint
...
"""
```

#### 1.2 Principle Descriptions Repeated Multiple Times

**Issue**: The four justice principles are described identically in multiple prompts, creating maintenance overhead.

**Locations**:
- English prompts: Lines 26, 28, 29, 30 in `english_prompts.json`
- Spanish prompts: Lines 26, 28, 29, 30 in `spanish_prompts.json` 
- Hardcoded locations: `phase1_manager.py` and `phase2_manager.py`

**Impact**:
- If principle descriptions need updates, multiple locations must be changed
- Risk of inconsistency if one location is updated but others aren't
- Increased translation maintenance burden

### 2. Structural Issues

#### 2.1 Mixed Prompt Generation Approaches

**Issue**: The system uses both language manager-based prompts and hardcoded prompts inconsistently.

**Analysis**:
- Most prompts correctly use language manager: `language_manager.get("prompts.key")`
- Some critical prompts are hardcoded, breaking the pattern
- No clear documentation on when to use which approach

#### 2.2 Complex Prompt Building Logic

**Issue**: Some prompts are built through complex concatenation that could be simplified.

**Examples**:
- `_build_application_prompt()` manually concatenates distribution tables with prompt text
- Phase 2 internal reasoning and discussion prompts are built separately but share similar structure

#### 2.3 Redundant Validation and Error Messages

**Issue**: Multiple similar validation messages exist across different prompt types.

**Examples**:
- Constraint validation messages repeated for both parser and validator
- Similar error messages for principle choice and principle ranking validation
- Duplicate certainty level handling across different prompt types

### 3. Translation and Localization Issues

#### 3.1 Inconsistent Translation Structure

**Issue**: Translation files have varying levels of detail and some inconsistencies.

**Findings**:
- English prompts: 83 lines with comprehensive coverage
- Spanish/Mandarin: Similar structure but potential quality variations
- Some prompts are excessively long (e.g., `phase2_group_discussion` spans 15+ lines)

#### 3.2 No Validation for Translation Completeness

**Issue**: No automated verification that all translations contain equivalent information.

**Impact**:
- Risk of missing translations causing runtime errors
- Difficult to maintain translation consistency across updates

### 4. Performance and Efficiency Issues

#### 4.1 Verbose Prompts

**Issue**: Many prompts contain excessive detail that may not be necessary for AI agents.

**Examples**:
- `utility_vote_detection` contains 25+ example phrases for vote detection
- Multiple prompts repeat the same principle definitions
- Excessive formatting instructions that could be simplified

#### 4.2 Redundant Context Information

**Issue**: Similar context information is repeated across many prompts.

**Examples**:
- Justice principle definitions appear in almost every prompt
- Constraint examples repeated in multiple locations
- Response format instructions duplicated

## Recommendations

### Immediate Fixes (High Priority)

#### 1. Fix Hardcoded Prompts
Replace hardcoded prompts with language manager calls:

```python
# Replace in phase1_manager.py
def _build_application_prompt(self, distribution_set, round_num: int) -> str:
    language_manager = get_language_manager()
    distributions_table = DistributionGenerator.format_distributions_table(
        distribution_set.distributions
    )
    
    return language_manager.get("prompts.phase1_application_round", 
                               round_number=round_num,
                               distributions_table=distributions_table)

# Replace in phase2_manager.py  
voting_prompt = language_manager.get("prompts.phase2_secret_ballot_vote")
```

#### 2. Add Missing Translation Keys
Add these keys to all translation files:
- `prompts.phase1_application_round`
- `prompts.phase2_secret_ballot_vote` 
- `prompts.phase2_vote_agreement`

### Structural Improvements (Medium Priority)

#### 1. Create Principle Description Template System
Instead of repeating principle descriptions, create reusable templates:

```json
{
  "templates": {
    "justice_principles_list": {
      "format": "numbered_list",
      "items": [
        "common.principle_names.maximizing_floor",
        "common.principle_names.maximizing_average", 
        "common.principle_names.maximizing_average_floor_constraint",
        "common.principle_names.maximizing_average_range_constraint"
      ]
    }
  }
}
```

#### 2. Consolidate Validation Messages
Create standardized validation message templates that can be reused:

```json
{
  "prompts": {
    "validation_missing_constraint": "You selected {principle_name} but did not specify the {constraint_type} constraint amount.",
    "validation_incomplete_ranking": "Your ranking is incomplete. Please rank all four principles from 1 to 4."
  }
}
```

#### 3. Simplify Complex Prompts
Break down overly complex prompts into smaller, composable parts:

```python
def _build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int) -> str:
    base_prompt = self.language_manager.get("prompts.phase2_discussion_base")
    history_section = self._format_discussion_history(discussion_state.public_history)
    rules_section = self.language_manager.get("prompts.phase2_discussion_rules")
    
    return f"{base_prompt}\n\n{history_section}\n\n{rules_section}"
```

### Optimization Improvements (Lower Priority)

#### 1. Reduce Prompt Verbosity
- Remove redundant examples from utility prompts
- Simplify response format instructions
- Consolidate similar instruction sets

#### 2. Implement Template Inheritance
Allow prompts to inherit from base templates to reduce duplication:

```json
{
  "base_templates": {
    "principle_application": {
      "header": "CURRENT TASK: Principle Application",
      "principles_list": "@templates.justice_principles_list",
      "response_format": "@templates.standard_response_format"
    }
  }
}
```

#### 3. Add Prompt Validation System
Create automated tests to verify:
- All translation files have equivalent prompt keys
- No prompts exceed reasonable length limits  
- Consistent terminology across all prompts
- All template references resolve correctly

## Implementation Priority

### Phase 1: Critical Fixes (1-2 days)
1. Replace hardcoded prompts with language manager calls
2. Add missing translation keys
3. Test multi-language functionality

### Phase 2: Structural Improvements (3-5 days)  
1. Implement principle description templates
2. Consolidate validation messages
3. Simplify complex prompt building logic

### Phase 3: Optimization (1-2 weeks)
1. Reduce prompt verbosity
2. Implement template inheritance system
3. Add comprehensive prompt validation

## Risk Assessment

### High Risk
- **Multi-language Failure**: Hardcoded prompts will cause immediate failures in Spanish/Mandarin experiments
- **Maintenance Debt**: Current duplication makes updates error-prone

### Medium Risk  
- **Inconsistent User Experience**: Mixed approaches create confusion
- **Translation Drift**: Manual translation maintenance leads to inconsistencies

### Low Risk
- **Performance Impact**: Verbose prompts increase token usage but don't break functionality
- **Code Complexity**: Current approach works but is harder to maintain

## Testing Requirements

After implementing recommendations, verify:

1. **Multi-language Functionality**
   - Run complete experiments in all three languages
   - Verify all prompts display correctly
   - Check that constraint validation works in all languages

2. **Prompt Consistency**
   - Compare principle descriptions across all prompt types
   - Verify voting prompts match discussion prompts
   - Test edge cases with constraint specifications

3. **Template System**
   - Verify template inheritance resolves correctly
   - Test fallback behavior for missing templates
   - Validate performance impact of template processing

## Conclusion

The Frohlich Experiment system has a solid foundation with its language manager architecture, but critical inconsistencies prevent it from fully realizing its multi-language potential. The hardcoded prompts represent the highest priority issue that should be addressed immediately.

The recommended improvements will:
- Ensure reliable multi-language support
- Reduce maintenance overhead  
- Improve prompt consistency
- Optimize system performance
- Make the codebase more maintainable

Implementation should follow the phased approach outlined above, with critical fixes taking precedence over optimizations.