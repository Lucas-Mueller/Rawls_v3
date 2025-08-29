# Letter-Based Principle Contamination Remediation Plan

**Date**: August 29, 2025  
**Scope**: System-wide letter-based principle reference elimination across English, Spanish, and Mandarin  
**Priority**: CRITICAL - Addresses 47+ contaminated files affecting core system functionality

---

## Executive Summary

This plan systematically addresses the extensive letter-based principle contamination found throughout the Frohlich Experiment codebase. The contamination affects multiple system layers and three languages (English, Spanish, Mandarin), requiring coordinated remediation across 6 distinct subprojects.

### Contamination Impact
- **Current Issue**: `"My choice is principle b"` incorrectly parsed as valid principle choice
- **Root Cause**: Incomplete letter rejection patterns + system contamination
- **Scope**: 47+ files with letter-based references across translations, tests, documentation, and archives

---

## Subproject 1: CRITICAL - Core System Decontamination

**Priority**: 1 (URGENT - Complete within 24 hours)  
**Objective**: Fix immediate test failures and strengthen core letter rejection mechanisms

### English Components
- **File**: `experiment_agents/utility_agent.py`
  - Fix letter rejection patterns to catch `"choice is principle X"` pattern
  - Add comprehensive regex patterns for all letter variations
  - Strengthen LLM fallback to reject any letter-based references
  - Add validation for `"My choice is principle [a-d]"` format

- **File**: `translations/english_prompts.json`
  - **Line 46**: Remove `"I might vote for principle a"` example from utility_llm_parse_vote_intention prompt
  - Replace all letter examples with full-name examples
  - Audit all utility prompts for hidden letter contamination

### Spanish Components
- **File**: `translations/spanish_prompts.json` 
  - Audit for any `principio [a-d]` patterns (currently clean based on search)
  - Verify all utility prompts use full principle names only
  - Add Spanish-specific letter rejection patterns if needed

### Mandarin Components  
- **File**: `translations/mandarin_prompts.json`
  - Audit for 原则[a-d], 甲乙丙丁原则 patterns (currently clean based on search)
  - Verify all utility prompts use full principle names only
  - Add Mandarin-specific letter rejection patterns if needed

### Implementation Tasks
1. **Pattern Enhancement** (2 hours)
   - Add missing `"choice is principle [a-d]"` regex pattern
   - Add `"preference is principle [a-d]"` pattern
   - Add `"vote is principle [a-d]"` pattern
   - Add multilingual letter patterns: `principio [a-d]`, `原则[a-d]`, `选择[a-d]`

2. **LLM Fallback Hardening** (3 hours)  
   - Update all utility prompts to explicitly reject letter-based references
   - Add examples of what NOT to accept in utility agent prompts
   - Strengthen rejection language across all three languages

3. **Active Translation Cleanup** (1 hour)
   - Remove letter examples from `translations/english_prompts.json:46`
   - Verify `translations/missing_batch1.json` is not actively loaded
   - Clean any remaining letter references in active translation files

### Success Criteria
- All Phase 2 tests pass: `python -m pytest tests/unit/test_phase2_*.py tests/integration/test_phase2_*.py -v`
- `"My choice is principle b"` returns `None` or rejection response
- Letter rejection works across all three languages

---

## Subproject 2: HIGH - Translation System Comprehensive Audit

**Priority**: 2 (Complete within 48 hours)  
**Objective**: Ensure translation system serves no letter-based content in any language

### English Translation Files
- **File**: `translations/english_prompts.json`
  - Line-by-line audit for any letter examples
  - Replace examples with full principle names
  - Verify utility prompts are letter-free
  
- **File**: `translations/missing_batch1.json`
  - **Lines 20, 48, 56**: Remove letter-based examples and prompts
  - Determine if file is actively used by language manager
  - If active: clean completely; if inactive: move to archive

### Spanish Translation Files
- **File**: `translations/spanish_prompts.json`
  - Comprehensive audit for `principio [a-d]`, `elección [a-d]`, `opción [a-d]` patterns
  - Currently appears clean based on regex search but needs manual verification
  - Ensure all examples use full Spanish principle names

### Mandarin Translation Files  
- **File**: `translations/mandarin_prompts.json`
  - Comprehensive audit for `原则[甲乙丙丁a-d]`, `选择[甲乙丙丁a-d]` patterns
  - Currently appears clean based on regex search but needs manual verification  
  - Ensure all examples use full Mandarin principle names

### Language Manager Verification
- **File**: `utils/language_manager.py`
  - Trace how translation files are loaded and served
  - Verify no letter-based content can reach agents
  - Add logging to detect if letter-based prompts are ever served

### Implementation Tasks
1. **Manual File Auditing** (4 hours)
   - Line-by-line review of all 3 main translation files
   - Document any letter references found
   - Create clean replacement examples

2. **Language Manager Analysis** (2 hours)
   - Map translation file loading process
   - Identify all possible paths for contaminated content
   - Add safeguards against letter-based content serving

3. **Multilingual Example Creation** (2 hours)
   - Create comprehensive full-name examples in all 3 languages
   - Ensure examples are consistent across languages
   - Test examples with native language validation

### Success Criteria
- Zero letter-based examples in any active translation file
- Language manager confirmed clean of letter-serving pathways
- Consistent full-name examples across English, Spanish, Mandarin

---

## Subproject 3: MEDIUM - Test Suite Multilingual Remediation

**Priority**: 3 (Complete within 1 week)  
**Objective**: Ensure test suite validates letter rejection across all languages

### English Test Files
- **File**: `tests/unit/test_phase2_preference_detection_simple_mode.py`
  - **Lines 94-101**: Update test cases expecting letter patterns to fail
  - Verify `"I prefer a"`, `"My choice is b"`, `"I support c"` return None/rejection
  - Add test cases for `"My choice is principle a"` pattern

- **File**: `tests/unit/test_full_name_parsing_only.py`  
  - **Line 63**: Verify `"My choice is a"` test expects failure
  - Add comprehensive letter rejection test coverage
  - Test both simple letters and "principle X" patterns

### Spanish Test Coverage
- Add Spanish letter rejection tests: `"Mi elección es principio a"`
- Test Spanish letter patterns: `"principio b"`, `"elijo principio c"`
- Verify Spanish utility agent rejects all letter variations

### Mandarin Test Coverage  
- Add Mandarin letter rejection tests: `"我选择原则a"`
- Test Chinese letter patterns using traditional markers: `"原则甲"`, `"选择乙"`
- Test mixed character patterns: `"原则a"`, `"原则A"`

### Integration Test Updates
- **Files**: Multiple integration test files showing mixed letter/full-name patterns
- Ensure all tests consistently expect letter rejection
- Update any tests that incorrectly accept letter-based input

### Implementation Tasks
1. **Test Pattern Analysis** (3 hours)
   - Catalog all existing letter-based test patterns
   - Map expected vs actual behavior for each test
   - Identify tests that should fail but are passing

2. **Multilingual Test Creation** (4 hours)
   - Create comprehensive letter rejection tests for Spanish
   - Create comprehensive letter rejection tests for Mandarin  
   - Ensure test coverage matches English completeness

3. **Integration Test Fixes** (3 hours)
   - Update integration tests with inconsistent expectations
   - Ensure end-to-end letter rejection works across languages
   - Add cross-language contamination tests

### Success Criteria
- All letter-based test inputs return None/rejection across all languages
- Test suite enforces no-letter policy consistently
- Letter rejection coverage equivalent across English, Spanish, Mandarin

---

## Subproject 4: MEDIUM - Documentation Multilingual Decontamination

**Priority**: 4 (Complete within 1 week)  
**Objective**: Remove letter examples from documentation and ensure consistency

### English Documentation
- **File**: `z mds/Letter_Based_Parsing_Removal_Plan.md`
  - **Lines 33, 85, 203**: Remove `"principle c"` examples
  - Replace with full-name examples
  - Update plan to reflect completed remediation

- **File**: `z mds/English_Phase2_Instructions.md`
  - **Lines 25, 35-37**: Replace letter-based examples
  - Update to use full principle names consistently
  - Add examples showing correct full-name usage

### Spanish Documentation
- **File**: `z mds/Spanish_Translation_Letter_Removal_Plan.md`
  - Remove any Spanish letter examples
  - Update with correct Spanish full-name examples
  - Ensure consistency with Spanish translation files

### Mandarin Documentation  
- **File**: `z mds/Mandarin_Translation_Letter_Removal_Plan.md`
  - Remove any Mandarin letter examples  
  - Update with correct Mandarin full-name examples
  - Ensure consistency with Mandarin translation files

### Architecture Documentation
- Update system architecture docs to reflect no-letter policy
- Add guidelines for preventing future letter contamination
- Document the multilingual approach to principle references

### Implementation Tasks
1. **Documentation Audit** (3 hours)
   - Systematic search through all .md files for letter patterns
   - Document findings and create replacement plan
   - Prioritize user-facing vs internal documentation

2. **Multilingual Example Standardization** (2 hours)
   - Create standard full-name examples in all 3 languages
   - Ensure examples are technically accurate and consistent
   - Review with native language expertise if available

3. **Policy Documentation Updates** (2 hours)
   - Update CLAUDE.md to reflect multilingual no-letter policy
   - Add specific guidance for each language
   - Create prevention guidelines for future development

### Success Criteria
- Zero letter examples in any documentation file
- Consistent full-name examples across all languages
- Clear policy documentation preventing future contamination

---

## Subproject 5: LOW - Archive Organization and Historical Cleanup

**Priority**: 5 (Complete within 2 weeks)  
**Objective**: Properly organize historical letter-based files to prevent confusion

### Archive Structure Creation
- Create clear directory structure: `archive/letter_based_legacy/`
- Separate by language: `english/`, `spanish/`, `mandarin/`
- Add README explaining historical context and why files are archived

### English Archives
- **File**: `archive/english_prompts_LETTER_BASED_VERSION_OUTDATED.json.backup`
  - Move to organized archive structure
  - Add clear warning labels about outdated content
  - Document historical significance

### Spanish Archives  
- **File**: `archive/spanish_prompts_LETTER_BASED_VERSION_OUTDATED.json.backup`
  - Contains extensive Spanish letter patterns like `"Mi elección de voto es principio c"`
  - Move to organized Spanish archive section
  - Add Spanish-language warning about outdated content

### Mandarin Archives
- Organize any Mandarin letter-based historical files
- Add Mandarin-language warnings about outdated content
- Ensure clear separation from active files

### Implementation Tasks
1. **Archive Structure Design** (2 hours)
   - Design clear, intuitive archive organization
   - Create README templates for each language section
   - Plan metadata and warning systems

2. **File Migration** (3 hours)  
   - Move all identified legacy files to proper archive locations
   - Add appropriate metadata and warnings
   - Verify no active code references archived files

3. **Documentation Creation** (2 hours)
   - Create comprehensive archive documentation
   - Explain historical context and evolution of system
   - Add guidance for researchers needing historical data

### Success Criteria
- All letter-based legacy files properly archived and labeled
- Clear separation between active and historical files
- Documentation explaining system evolution and archive purpose

---

## Subproject 6: VERIFICATION - Comprehensive Multilingual System Validation

**Priority**: 6 (Complete within 2 weeks)  
**Objective**: Validate complete letter-free operation across all languages

### End-to-End Testing Framework
- Create comprehensive test suite covering all entry points
- Test letter rejection in all three languages
- Verify no contamination pathways exist

### Cross-Language Validation
- Test mixed-language scenarios (English agents, Spanish prompts)
- Verify letter rejection works regardless of language combination  
- Test system behavior with multilingual user inputs

### Performance and Regression Testing
- Ensure letter rejection doesn't impact system performance
- Verify all original functionality works correctly
- Test edge cases and boundary conditions

### Documentation and Monitoring
- Create monitoring system to detect future letter contamination
- Add automated tests to CI/CD pipeline
- Document validation procedures for ongoing maintenance

### Implementation Tasks
1. **Test Framework Creation** (4 hours)
   - Design comprehensive test scenarios covering all languages
   - Create automated test suite for letter rejection validation
   - Set up cross-language contamination testing

2. **System Integration Validation** (3 hours)
   - Test complete experiment flows with letter rejection active
   - Verify no functional regressions introduced
   - Validate performance characteristics

3. **Monitoring and Prevention Systems** (3 hours)
   - Create automated contamination detection
   - Set up alerts for letter-based content introduction
   - Document prevention procedures for future development

### Success Criteria
- Complete letter-free system operation verified across all languages
- No functional regressions or performance impacts
- Monitoring and prevention systems active and documented

---

## Implementation Timeline

### Phase 1: Critical Fixes (Days 1-2)
- **Day 1**: Subproject 1 - Core System Decontamination
- **Day 2**: Subproject 2 - Translation System Audit

### Phase 2: Systematic Cleanup (Days 3-7)  
- **Days 3-4**: Subproject 3 - Test Suite Remediation
- **Days 5-7**: Subproject 4 - Documentation Decontamination

### Phase 3: Organization and Validation (Days 8-14)
- **Days 8-10**: Subproject 5 - Archive Organization
- **Days 11-14**: Subproject 6 - System Validation

---

## Success Metrics

### Technical Metrics
- **Test Pass Rate**: 100% pass rate for `python -m pytest tests/unit/test_phase2_*.py tests/integration/test_phase2_*.py -v`
- **Letter Rejection Rate**: 100% rejection of letter-based inputs across all languages
- **System Performance**: No regression in experiment execution time

### Quality Metrics  
- **Zero Letter Examples**: No letter-based examples in any active system file
- **Documentation Consistency**: Consistent full-name examples across all three languages
- **Archive Organization**: Clear separation and labeling of historical files

### Operational Metrics
- **Prevention Systems**: Automated detection of future letter contamination
- **Monitoring Coverage**: Alerts for letter-based content introduction
- **Maintenance Documentation**: Clear procedures for ongoing letter-free system maintenance

---

## Risk Management

### Technical Risks
- **Risk**: Breaking system functionality during remediation
- **Mitigation**: Comprehensive testing at each subproject completion
- **Rollback Plan**: Git branch-based development with tested checkpoints

### Language-Specific Risks  
- **Risk**: Incomplete letter pattern detection in non-English languages
- **Mitigation**: Native language expertise consultation for Spanish/Mandarin
- **Validation**: Comprehensive multilingual test coverage

### Integration Risks
- **Risk**: Component interactions causing unexpected letter acceptance
- **Mitigation**: End-to-end integration testing across all subprojects
- **Monitoring**: Continuous validation of letter-free operation

---

## Conclusion

This comprehensive plan addresses letter-based principle contamination across all three supported languages through systematic, prioritized remediation. The plan ensures both immediate fixes for critical test failures and long-term system integrity through proper organization, documentation, and monitoring.

**Expected Outcome**: A completely letter-free Frohlich Experiment system that properly rejects all letter-based principle references while maintaining full functionality across English, Spanish, and Mandarin languages.

**Key Success Indicator**: `"My choice is principle b"` (and equivalents in Spanish/Mandarin) correctly return `None` or rejection responses, with all Phase 2 tests passing consistently.