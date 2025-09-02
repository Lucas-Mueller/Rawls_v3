# Translation Audit Implementation Plan

## Executive Summary

This plan addresses critical translation issues identified in the audit report that are causing failures in Spanish and Mandarin experiments. The issues fall into three main categories:
1. **Missing translation keys** causing KeyError exceptions in non-English experiments
2. **Hardcoded English strings** being sent to participant agents
3. **Inconsistent principle naming** between phases

## Root Cause Analysis

### Primary Issues Identified

1. **Missing Translation Keys (Critical - Causes Experiment Failures)**
   - Phase 1 memory_field_labels keys missing in Spanish/Mandarin
   - Phase 2 voting-related messages missing in Spanish/Mandarin  
   - Phase 2 results formatting keys missing in Spanish/Mandarin
   - MemoryService hardcoded paths that don't exist in translation files

2. **Hardcoded English Text (High Priority)**
   - MemoryService uses hardcoded "Final Phase 2 Results:" prefix
   - TwoStageVotingManager contains hardcoded English fallback messages
   - Various system messages not properly localized

3. **Inconsistent Principle Names (Medium Priority)**
   - Different principle key formats used across phases
   - Potential confusion between system keys and display names

### Current Translation File Structure

- `/translations/english_prompts.json` - Complete English baseline
- `/translations/spanish_prompts.json` - Spanish translations (some keys missing)
- `/translations/mandarin_prompts.json` - Mandarin translations (some keys missing)

### Affected Components

- `core/services/memory_service.py` - Uses non-existent translation keys
- `core/two_stage_voting_manager.py` - Contains hardcoded English fallbacks
- `utils/language_manager.py` - Main translation interface (working correctly)

## Implementation Plan

### Phase 1: Critical Missing Keys (Priority: Critical)
**Objective**: Fix experiment-breaking KeyError exceptions in non-English languages

**Estimated Effort**: 4-6 hours
**Dependencies**: None
**Risk Level**: Low (additive changes only)

#### Tasks:
1. **Add Missing Memory Field Labels**
   - Add `memory_field_labels` section to Spanish translation file
   - Add `memory_field_labels` section to Mandarin translation file
   - Validate keys match English version exactly

2. **Add Missing Phase 2 Voting Keys**
   - Add `prompts.memory_insertions.*` keys for voting decisions
   - Add `voting_phases.*` keys for phase transitions
   - Add `errors.timeout_retry` key for voting timeouts

3. **Add Missing Results Formatting Keys**
   - Add Phase 2 results-related message keys
   - Add any remaining `prompts.*` keys referenced in MemoryService

**Success Criteria**:
- All KeyError exceptions eliminated in Spanish/Mandarin experiments
- Translation validation script passes for all languages
- Memory updates work correctly in all languages

**Deliverables**:
- Updated `spanish_prompts.json` with all missing keys
- Updated `mandarin_prompts.json` with all missing keys
- Validation script confirming no missing keys

---

### Phase 2: Remove Hardcoded English Strings (Priority: High)
**Objective**: Replace hardcoded English text with properly localized versions

**Estimated Effort**: 6-8 hours
**Dependencies**: Phase 1 completion
**Risk Level**: Medium (requires code changes and testing)

#### Tasks:
1. **Fix MemoryService Hardcoded Strings**
   - Replace `"Final Phase 2 Results: {result_content}"` with localized version
   - Add translation key `prompts.memory_insertions.final_results_prefix`
   - Update `update_final_results_memory()` method

2. **Fix TwoStageVotingManager Fallbacks**
   - Replace hardcoded fallback messages with proper translation lookups
   - Ensure all error messages use language_manager.get() calls
   - Remove English-only timeout messages

3. **Audit Other Hardcoded Strings**
   - Search codebase for remaining hardcoded English strings
   - Replace with proper translation key references
   - Add missing keys to translation files

**Success Criteria**:
- No hardcoded English strings sent to participant agents
- All system messages properly localized
- Consistent user experience across all languages

**Deliverables**:
- Updated `memory_service.py` with localized strings
- Updated `two_stage_voting_manager.py` with localized strings  
- Updated translation files with new keys
- Test validation showing proper localization

---

### Phase 3: Standardize Principle Naming (Priority: Medium)
**Objective**: Ensure consistent principle naming conventions across all phases

**Estimated Effort**: 3-4 hours
**Dependencies**: Phase 2 completion
**Risk Level**: Low (primarily documentation and validation)

#### Tasks:
1. **Audit Principle Key Usage**
   - Document all locations where principle names are referenced
   - Identify inconsistencies between phases
   - Map current key usage patterns

2. **Standardize Key References**
   - Ensure all code uses `common.principle_names.*` keys consistently
   - Update any non-standard key references
   - Validate principle names match across all translation files

3. **Add Documentation**
   - Document principle naming conventions for future development
   - Create validation guidelines for new translation keys

**Success Criteria**:
- Consistent principle naming across all phases and languages
- Clear documentation of naming conventions
- Validation scripts to prevent future inconsistencies

**Deliverables**:
- Documentation of principle naming standards
- Updated code with consistent key usage
- Enhanced validation scripts

---

## Technical Implementation Details

### Phase 1 Specific Changes

#### Spanish Translation Keys to Add:
```json
{
  "prompts": {
    "memory_insertions": {
      "vote_initiation_decision": "Ronda {round_num}: Decisión de iniciación de voto: {decision}",
      "initiate_voting": "Decidió iniciar la votación",
      "continue_discussion": "Decidió continuar la discusión",
      "confirmation_response": "{response} participar en la votación",
      "agreed_to": "Acordó",
      "declined_to": "Se negó a",
      "final_results_prefix": "Resultados Finales de la Fase 2:"
    },
    "voting_phases": {
      "initiation": "Se inició la votación",
      "initiation_with_initiator": "{initiator_name} inició la votación",
      "confirmation": "Se solicitó confirmación de votación",
      "secret_ballot": "Votación secreta en progreso"
    }
  },
  "errors": {
    "timeout_retry": "Tiempo de espera agotado. Por favor, inténtalo de nuevo."
  }
}
```

#### Mandarin Translation Keys to Add:
```json
{
  "prompts": {
    "memory_insertions": {
      "vote_initiation_decision": "第{round_num}轮：投票启动决定：{decision}",
      "initiate_voting": "决定启动投票",
      "continue_discussion": "决定继续讨论",
      "confirmation_response": "{response}参与投票",
      "agreed_to": "同意",
      "declined_to": "拒绝",
      "final_results_prefix": "第二阶段最终结果："
    },
    "voting_phases": {
      "initiation": "投票已启动",
      "initiation_with_initiator": "{initiator_name}启动了投票",
      "confirmation": "请求投票确认",
      "secret_ballot": "秘密投票进行中"
    }
  },
  "errors": {
    "timeout_retry": "响应超时。请重试。"
  }
}
```

### Phase 2 Code Changes

#### MemoryService Updates:
```python
# Before:
formatted_content = f"Final Phase 2 Results: {result_content}"

# After:
results_prefix = self.language_manager.get("prompts.memory_insertions.final_results_prefix")
formatted_content = f"{results_prefix} {result_content}"
```

#### TwoStageVotingManager Updates:
```python
# Before:
fallback_messages = {
    "respond_with_number_only": f"Invalid response (attempt {attempt}/{max_attempts}). You must respond with exactly one number: 1, 2, 3, or 4.",
    # ... other hardcoded messages
}

# After:
# Remove fallback_messages dict entirely, always use language_manager.get()
error_message = self.language_manager.get(f"errors.two_stage_{error_type}", 
                                        attempt=attempt, max_attempts=max_attempts)
```

## Risk Assessment and Mitigation

### High Risk Areas:
1. **Translation Key Mismatches**: Risk of typos in key names causing new KeyErrors
   - **Mitigation**: Comprehensive validation script execution before deployment
   - **Testing**: Run experiments in all three languages after each phase

2. **Code Changes Breaking Existing Functionality**: Risk of introducing bugs in working English experiments
   - **Mitigation**: Maintain backward compatibility, extensive testing
   - **Testing**: Full regression test suite execution

### Medium Risk Areas:
1. **Translation Quality**: Risk of poor translations affecting user experience
   - **Mitigation**: Native speaker review of all new translations
   - **Testing**: User experience validation in each language

## Testing Strategy

### Phase 1 Testing:
- Execute Spanish experiment end-to-end
- Execute Mandarin experiment end-to-end
- Verify no KeyError exceptions occur
- Validate all memory updates work correctly

### Phase 2 Testing:
- Test all voting workflows in all languages
- Verify no hardcoded English appears to participants
- Test error conditions and timeout scenarios
- Validate results display formatting

### Phase 3 Testing:
- Audit principle name consistency across all phases
- Test principle selection and display in all languages
- Verify documentation accuracy

## Success Metrics

1. **Zero KeyError exceptions** in non-English experiments
2. **100% localized content** sent to participant agents
3. **Consistent principle naming** across all phases and languages
4. **Successful experiment completion** in all three languages
5. **Passing validation scripts** for all translation files

## Timeline Estimate

- **Phase 1**: 1-2 days (critical path)
- **Phase 2**: 2-3 days  
- **Phase 3**: 1 day
- **Testing & Validation**: 1 day per phase
- **Total**: 8-12 days

## Dependencies and Prerequisites

1. Access to native Spanish and Mandarin speakers for translation review
2. Comprehensive test environment for multi-language testing
3. Backup of current translation files before modifications
4. Clear rollback plan if issues arise

## Post-Implementation Actions

1. Update translation documentation with new key requirements
2. Create validation checklist for future translation additions
3. Implement automated testing for multi-language functionality
4. Schedule periodic audits to prevent regression

---

This implementation plan provides a systematic approach to resolving all translation audit issues while minimizing risk and ensuring comprehensive testing at each phase.