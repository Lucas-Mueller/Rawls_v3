# Mandarin Translation Rebuild Plan

## Project Overview

This plan outlines the complete rebuilding of Mandarin translations for the Frohlich Experiment project. The English prompts file has been substantially updated, requiring a ground-up reconstruction of the Mandarin translation system to ensure accuracy, consistency, and completeness.

## Current State Analysis

### English Source File Analysis
- **Total entries**: 122 prompts and text elements
- **Structure**: Hierarchical JSON with `common` and `prompts` sections
- **Content scope**: Complete experimental framework including:
  - Justice principle definitions and applications
  - Phase 1 and Phase 2 instructions
  - Utility agent parsing and validation instructions
  - Error handling and system messages
  - Memory management prompts
  - Formatting and display templates

### Current Mandarin File Issues
- **Incomplete coverage**: Missing approximately 40-50% of current English content
- **Outdated translations**: Some existing translations don't reflect current English versions
- **Structural gaps**: Missing entire sections like detailed utility agent instructions
- **Inconsistent terminology**: Inconsistent translation of key justice principle terms
- **Quality concerns**: Some translations appear machine-generated without human review

## Translation Requirements

### Core Consistency Requirements

#### Justice Principles (Critical - Must Be Identical Throughout)
1. **Maximizing the floor** → `最大化最低收入` (Consistent term across all contexts)
2. **Maximizing the average** → `最大化平均收入` (Consistent term across all contexts)  
3. **Maximizing average with floor constraint** → `在最低收入约束条件下最大化平均收入` (Consistent term across all contexts)
4. **Maximizing average with range constraint** → `在范围约束条件下最大化平均收入` (Consistent term across all contexts)

#### Income Classes (Must Be Consistent)
- **High** → `高收入` (standardized from current `高`)
- **Medium high** → `中高收入` (standardized from current `中高`)
- **Medium** → `中等收入` (standardized from current `中型` - needs correction)
- **Medium low** → `中低收入` (standardized from current `中低`)
- **Low** → `低收入` (standardized from current `低`)

#### Certainty Levels (Must Be Consistent)
- **Very unsure** → `很不确定` (existing translation acceptable)
- **Unsure** → `不确定` (existing translation acceptable)
- **No opinion** → `无意见` (existing translation acceptable)
- **Sure** → `确定` (standardized from current `有把握的`)
- **Very sure** → `很确定` (existing translation acceptable)

## Translation Methodology

### Phase 1: DeepL Translation + Human Review
1. **Initial DeepL Translation**
   - Use DeepL MCP to translate each English text segment
   - Capture DeepL output for human evaluation
   - Document translation choices for consistency

2. **Human Evaluation Criteria**
   - **Accuracy**: Does translation convey exact meaning?
   - **Cultural appropriateness**: Is language natural for Mandarin speakers?
   - **Technical precision**: Are experimental terms correctly translated?
   - **Consistency**: Does translation match established terminology?
   - **Clarity**: Is the instruction clear and unambiguous?

3. **Modification Process**
   - If DeepL translation is adequate: Use as-is
   - If DeepL translation needs improvement: Modify while maintaining consistency
   - If DeepL translation is poor: Create new translation following established patterns

### Phase 2: Consistency Validation
1. **Terminology Audit**
   - Verify all instances of justice principles use identical translations
   - Confirm income classes are consistently translated
   - Check certainty levels maintain uniform language

2. **Context Validation** 
   - Ensure translations work appropriately in different contexts
   - Verify prompt instructions are actionable in Mandarin
   - Confirm examples and formats translate meaningfully

## Implementation Phases

### Phase A: Core Terminology and Common Elements (Priority 1)
**Target**: Complete `common` section with standardized terminology

**Elements to translate:**
- `principle_names` (4 entries) - Critical consistency requirement
- `income_classes` (5 entries) - Must be standardized
- `certainty_levels` (5 entries) - Must be standardized

**Quality gates**: 100% consistency check before proceeding

### Phase B: Primary Experimental Prompts (Priority 1)
**Target**: Complete all Phase 1 and Phase 2 participant-facing prompts

**Elements to translate:**
- `experiment_explanation` - Overall experiment description
- Phase 1 prompts (6 entries): Initial ranking, detailed explanations, applications, final ranking
- Phase 2 prompts (4 entries): Discussion prompts, voting processes, internal reasoning
- Memory and formatting templates (8 entries)

**Quality gates**: Contextual review for experimental flow

### Phase C: Utility Agent Instructions (Priority 2)  
**Target**: Complete all utility agent parsing and validation instructions

**Elements to translate:**
- Parser instructions (8 entries)
- Validator instructions (10 entries)
- LLM parsing prompts (6 entries)
- Error and success messages (15 entries)

**Quality gates**: Technical accuracy review for AI agent comprehension

### Phase D: System Messages and Templates (Priority 3)
**Target**: Complete all remaining system messages and display formats

**Elements to translate:**
- Error messages (7 entries)
- Success messages (5 entries) 
- Status messages (5 entries)
- Format templates (12 entries)

**Quality gates**: User experience review for clarity

## Key Translation Challenges and Solutions

### Challenge 1: Justice Principle Terminology Precision
**Problem**: These are technical philosophical terms requiring exact consistency
**Solution**: Establish definitive translations in Phase A, create reference glossary, validate every instance

### Challenge 2: Experimental Instruction Clarity  
**Problem**: Instructions must be unambiguous for research validity
**Solution**: Translate for maximum clarity, test instructions for actionability, review experimental flow

### Challenge 3: AI Agent Parsing Instructions
**Problem**: Agent instructions require technical precision for proper function
**Solution**: Focus on functional accuracy, maintain technical terminology, validate with system requirements

### Challenge 4: Cultural and Linguistic Adaptation
**Problem**: Direct translation may not convey intended meaning to Mandarin speakers
**Solution**: Prioritize meaning over literal translation, adapt examples for cultural context, maintain scientific rigor

## Quality Assurance Process

### Tier 1: Individual Entry QA
1. DeepL translation assessment
2. Human modification if needed
3. Consistency terminology check
4. Context appropriateness review

### Tier 2: Section-Level QA  
1. Internal consistency within section
2. Cross-reference validation with established terms
3. Experimental flow validation (for prompts)
4. User experience review

### Tier 3: Complete File QA
1. Global consistency audit across all sections
2. JSON structure and formatting validation
3. Integration testing readiness
4. Final human review of critical experimental elements

## Success Metrics

### Completeness Metrics
- [ ] 100% of English entries translated (122/122)
- [ ] All sections present and complete
- [ ] JSON structure matches English source exactly

### Quality Metrics  
- [ ] Justice principles terminology 100% consistent across all instances
- [ ] Income classes terminology 100% consistent across all instances
- [ ] Certainty levels terminology 100% consistent across all instances
- [ ] All experimental instructions clear and actionable
- [ ] All utility agent instructions technically accurate

### Integration Metrics
- [ ] Valid JSON structure
- [ ] Compatible with existing codebase
- [ ] Ready for experimental deployment
- [ ] No functionality regressions from previous version

## Timeline Estimate

**Phase A (Core Terminology)**: 2-3 hours
**Phase B (Primary Prompts)**: 4-6 hours  
**Phase C (Utility Instructions)**: 3-4 hours
**Phase D (System Messages)**: 2-3 hours
**Quality Assurance**: 2-3 hours

**Total Estimated Time**: 13-19 hours

## Risk Mitigation

### Risk: Inconsistent Terminology
**Mitigation**: Create and maintain terminology reference, validate every instance

### Risk: Loss of Experimental Validity  
**Mitigation**: Prioritize functional accuracy over linguistic elegance, maintain scientific precision

### Risk: Technical Functionality Issues
**Mitigation**: Preserve technical structure, validate agent instruction accuracy, test integration readiness

### Risk: Cultural Inappropriateness
**Mitigation**: Balance cultural adaptation with experimental requirements, maintain research validity

## Post-Implementation Validation

1. **JSON Structure Validation**: Confirm valid JSON and proper encoding
2. **Integration Testing**: Verify compatibility with existing codebase
3. **Terminology Audit**: Final consistency check on all critical terms  
4. **Human Review**: Native speaker review of key experimental instructions
5. **Functionality Testing**: Confirm system can parse all instructions correctly

## Conclusion

This comprehensive rebuild will create a high-quality, consistent, and complete Mandarin translation system that maintains the scientific rigor and experimental validity of the original English version while being culturally appropriate and linguistically natural for Mandarin-speaking participants.