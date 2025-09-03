# System Context Reduction Strategy Plan

## Executive Summary

This plan addresses the redundancy identified in the ranking prompt analysis report by systematically removing principle information from system context and consolidating all principle-related content into input prompts. The current system presents justice principle information **3 times** across different channels, creating unnecessary complexity and inefficient context usage.

## Current System Context Analysis

### 1. System Context Generation Location
**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/language_manager.py`
**Method**: `format_context_info()` (lines 374-422)

#### Current System Context Components:
1. **Agent Identity**: Name, role description, bank balance
2. **Phase Information**: Current phase and round number
3. **Memory Section**: Agent's formatted memory
4. **Experiment Explanation**: **[REDUNDANT - TO REMOVE]**
5. **Personality**: Agent personality description
6. **Phase Instructions**: Task-specific instructions **[MAY CONTAIN REDUNDANT PRINCIPLES]**
7. **Language Instruction**: Language-specific response requirements

### 2. Experiment Explanation Content Analysis
**Location**: `translations/english_prompts.json` → `experiment_explanation`

#### Current Content (62 lines):
```
"You are participating in an experiment studying principles of justice and income distribution.

The experiment has two main phases:

PHASE 1: You will individually learn about and apply four different principles of justice to income distributions. You will be asked to rank these principles by preference and apply them to specific scenarios. Your choices will affect your earnings.

PHASE 2: You will join a group discussion to reach consensus on which principle of justice the group should adopt. The group's chosen principle will then be applied to determine everyone's final earnings.

Throughout the experiment, engage thoughtfully with the principles and other participants."
```

#### Redundancy Analysis:
- **General experiment structure**: ✅ KEEP - Not redundant
- **Principle references**: ❌ REMOVE - Redundant with input prompts
- **Phase descriptions**: ❌ REMOVE - Redundant with phase instructions
- **Engagement guidance**: ✅ KEEP - Valuable behavioral guidance

### 3. Configuration System
**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/config/models.py`
**Setting**: `include_experiment_explanation_each_turn: bool = False`

#### Current Behavior:
- Default: Only include experiment explanation on first turn per phase
- Optional: Include on every turn if configured
- **Impact**: Even with optimization, still includes redundant principle information

## Strategy Design

### Phase 1: Immediate System Context Reduction

#### 1.1 Remove Principle Information from Experiment Explanation
**Target**: `translations/english_prompts.json` → `experiment_explanation`

**Current Problematic Content**:
- "four different principles of justice to income distributions"
- "rank these principles by preference and apply them to specific scenarios"
- References to principle application and group consensus

**Proposed Streamlined Content**:
```
"You are participating in an experiment studying distributive justice and income distribution.

Your choices in this experiment will affect your earnings. In some phases you will make individual decisions, in others you will participate in group discussions.

Throughout the experiment, engage thoughtfully and provide clear, reasoned responses that explain your thinking."
```

#### 1.2 Audit Phase Instructions for Principle Redundancy
**Target**: Phase-specific instruction methods in `utils/language_manager.py`

**Methods to Audit**:
- `get_phase1_instructions()` (line 246-269)
- `get_phase2_instructions()` (line 271-287)

**Check for**:
- Embedded principle definitions
- Redundant explanations of principles
- Duplicated response format instructions

#### 1.3 Configuration Optimization
**Current Setting**: `include_experiment_explanation_each_turn: bool = False`
**Recommendation**: Keep current default but reduce redundancy in the explanation content itself

### Phase 2: System Context Content Optimization

#### 2.1 Essential Context Components to KEEP
1. **Agent Identity Information**:
   - Name, role description, bank balance
   - **Justification**: Agents need to know who they are and their current status

2. **Phase and Round Information**:
   - Current phase and round number
   - **Justification**: Critical for understanding current task context

3. **Memory Section**:
   - Agent's personal memory and experiences
   - **Justification**: Core to agent continuity and decision-making

4. **Personality**:
   - Agent personality description
   - **Justification**: Shapes agent behavior and responses

5. **Behavioral Guidance**:
   - "Engage thoughtfully", response quality expectations
   - **Justification**: Important for response quality, not redundant

6. **Language Instruction**:
   - Language-specific response requirements
   - **Justification**: Critical for multilingual support

#### 2.2 Content to REMOVE or REDUCE
1. **Detailed Experiment Structure**:
   - Phase descriptions that duplicate task instructions
   - **Impact**: Reduces 2-3 lines of redundant content

2. **Principle References**:
   - Any mention of "four principles of justice"
   - Principle ranking or application references
   - **Impact**: Eliminates primary redundancy source

3. **Process Explanations**:
   - Detailed explanations of how phases work
   - **Impact**: Reduces context size, relies on task instructions

### Phase 3: Implementation Strategy

#### 3.1 Implementation Order (Risk Mitigation)
1. **Step 1**: Update experiment explanation content (lowest risk)
2. **Step 2**: Audit phase instructions for redundancy
3. **Step 3**: Test with existing functionality
4. **Step 4**: Extend to all languages
5. **Step 5**: Clean up any remaining redundancy

#### 3.2 Backward Compatibility Measures
- **Configuration Preservation**: Keep `include_experiment_explanation_each_turn` setting
- **Functionality Preservation**: Maintain all existing method signatures
- **Content Quality**: Ensure reduced content still provides necessary behavioral guidance

#### 3.3 Risk Mitigation Strategies
1. **Gradual Implementation**: Start with English only, then extend
2. **A/B Testing**: Compare agent responses before/after changes
3. **Rollback Plan**: Keep original content available for quick restoration

## Expected Impact Analysis

### 1. Context Window Optimization
#### Current System Context Size (English):
- **Experiment Explanation**: ~500 characters
- **Total Context**: ~1,500-2,000 characters
- **Redundancy**: ~200-300 characters of principle references

#### Post-Reduction Estimate:
- **Streamlined Explanation**: ~200 characters
- **Total Reduction**: ~400-500 characters
- **Efficiency Gain**: 20-25% context reduction

### 2. Maintenance Benefits
1. **Single Source of Truth**: All principle information in input prompts only
2. **Translation Consistency**: Reduced duplication across language files
3. **Update Simplicity**: Changes to principle descriptions in one location only
4. **Testing Simplicity**: Fewer interaction points to validate

### 3. Agent Behavior Impact
#### Expected Neutral Impact:
- **Decision Quality**: No change (same principle information available)
- **Response Accuracy**: No change (format instructions remain in prompts)
- **Parsing Reliability**: No change (parser reads from prompt responses)

#### Expected Positive Impact:
- **Context Efficiency**: More room for memory and task-specific information
- **Prompt Clarity**: Cleaner separation between context and task instructions
- **Consistency**: Unified principle presentation across all interactions

## Implementation Plan

### Step 1: Immediate Content Reduction (1-2 hours)
```yaml
Priority: High
Risk: Low
Files to Modify:
  - translations/english_prompts.json (experiment_explanation)
  - translations/spanish_prompts.json (experiment_explanation)  
  - translations/mandarin_prompts.json (experiment_explanation)

Changes:
  - Remove principle-specific references
  - Streamline to essential behavioral guidance
  - Maintain engagement and quality expectations
```

### Step 2: Phase Instruction Audit (2-3 hours)
```yaml
Priority: Medium
Risk: Medium
Files to Audit:
  - utils/language_manager.py (phase instruction methods)
  - translations/*.json (phase instruction content)

Analysis Required:
  - Identify embedded principle definitions
  - Check for response format duplication
  - Assess instruction clarity after context reduction
```

### Step 3: Validation and Testing (2-4 hours)
```yaml
Priority: High
Risk: Low
Testing Requirements:
  - Run existing test suite with modified context
  - Validate agent response quality
  - Check multilingual consistency
  - Verify parsing accuracy
```

### Step 4: System-Wide Cleanup (1-2 hours)
```yaml
Priority: Low
Risk: Low
Cleanup Tasks:
  - Remove unused methods/constants
  - Update documentation
  - Verify configuration consistency
  - Final multilingual validation
```

## Success Metrics

### Quantitative Metrics:
1. **Context Size Reduction**: 20-25% reduction in system context length
2. **Principle Mention Frequency**: Reduce from 3 instances to 1 per ranking task
3. **Translation Consistency**: Zero discrepancies in principle definitions across languages

### Qualitative Metrics:
1. **Agent Response Quality**: No degradation in response depth or accuracy
2. **Parsing Reliability**: Maintain 100% parsing success rate
3. **Developer Experience**: Reduced maintenance complexity for principle updates

## Risk Assessment and Mitigation

### Low Risk Items:
- **Experiment Explanation Streamlining**: Core guidance preserved
- **Content Consolidation**: Same information, better organization
- **Translation Updates**: Mechanical changes across languages

### Medium Risk Items:
- **Phase Instruction Changes**: May affect task understanding
- **Context Length Impact**: Agents may notice reduced context
- **Multilingual Consistency**: Translation errors could emerge

### High Risk Items:
- **Breaking Agent Context Expectations**: None identified
- **Disrupting Response Patterns**: Mitigated by preserving format instructions in prompts
- **Parser Incompatibility**: None expected (parser reads prompt responses, not context)

### Mitigation Strategies:
1. **Incremental Implementation**: English first, then other languages
2. **Test Coverage**: Run full experiment suite after each change
3. **Rollback Capability**: Maintain original content in version control
4. **Monitoring**: Track agent response patterns for 1-2 weeks post-implementation

## Conclusion

The system context reduction strategy will eliminate identified redundancy while preserving all essential agent context information. The approach is conservative, focusing on clearly redundant content while maintaining behavioral guidance and agent identity information.

**Key Benefits**:
1. **Efficiency**: 20-25% reduction in system context size
2. **Maintainability**: Single source of truth for principle information  
3. **Consistency**: Unified principle presentation across all languages
4. **Clarity**: Cleaner separation between agent context and task instructions

**Implementation Timeline**: 6-11 hours total effort over 2-3 days

**Recommended Next Steps**:
1. Begin with Step 1 (immediate content reduction) as proof of concept
2. Validate with English experiments before extending to other languages
3. Monitor agent response quality for any unexpected impacts
4. Complete full implementation once validation confirms expected benefits

This plan provides a systematic approach to eliminating redundancy while ensuring no functionality is lost and all essential agent context information is preserved.