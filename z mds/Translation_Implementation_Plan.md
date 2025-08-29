# Translation Implementation Plan

## Overview

This comprehensive implementation plan addresses all translation issues identified in the Translation Analysis Report. The plan is organized by priority levels with specific tasks, acceptance criteria, and validation procedures to ensure complete resolution of all translation inconsistencies and missing content.

## Priority Classification

- **P0 (Critical)**: Functionality-breaking issues that must be fixed immediately
- **P1 (High)**: Issues that significantly impact user experience
- **P2 (Medium)**: Consistency and quality improvements
- **P3 (Low)**: Nice-to-have enhancements and future improvements

---

## Phase 1: Critical Fixes (P0) - IMMEDIATE ACTION REQUIRED

### Task 1.1: Fix Mixed Language Content in Spanish File
**Priority**: P0 - Critical
**Location**: `translations/spanish_prompts.json`
**Issue**: Line 88 (`utility_constraint_re_prompt`) contains English content

#### Specific Actions:
1. **Translate utility_constraint_re_prompt** (Line 88):
   ```json
   // Current (INCORRECT - English in Spanish file):
   "utility_constraint_re_prompt": "\n{participant_name}, you chose the \"{principle_name}\" principle, but you did not specify the {constraint_type} constraint amount.\n\nReminder about your chosen principle:\n- Floor constraint: Maximizes average income only after guaranteeing everyone receives at least a specified minimum income\n- Range constraint: Maximizes average income while ensuring the difference between richest and poorest does not exceed a specified amount\n\nPlease specify the dollar amount for your {constraint_type} constraint.\n\nFor example:\n- Floor constraint: \"I choose maximizing average with a floor constraint of $X\"\n- Range constraint: \"I choose maximizing average with a range constraint of $X\"\n"
   
   // Required Translation:
   "utility_constraint_re_prompt": "\n{participant_name}, usted eligió el principio \"{principle_name}\", pero no especificó la cantidad de restricción {constraint_type}.\n\nRecordatorio sobre el principio que eligió:\n- Restricción de ingreso mínimo: Maximiza el ingreso promedio solo después de garantizar que todos reciban al menos un ingreso mínimo especificado\n- Restricción de rango: Maximiza el ingreso promedio mientras asegura que la diferencia entre los más ricos y más pobres no exceda una cantidad especificada\n\nPor favor especifique la cantidad en dólares para su restricción {constraint_type}.\n\nPor ejemplo:\n- Restricción de ingreso mínimo: \"Elijo maximizar el promedio con una restricción de ingreso mínimo de $X\"\n- Restricción de rango: \"Elijo maximizar el promedio con una restricción de rango de $X\"\n"
   ```

2. **Scan entire Spanish file** for additional English content:
   - Search for English keywords: "the", "and", "you", "choose", "principle"
   - Verify all prompts are in Spanish
   - Check all system messages and error messages

#### Acceptance Criteria:
- [ ] Line 88 completely translated to Spanish
- [ ] No English content remains in Spanish file
- [ ] Translation maintains technical accuracy
- [ ] Parameter placeholders preserved correctly
- [ ] JSON structure remains valid

**Estimated Time**: 2 hours
**Dependencies**: None
**Validation**: JSON parser test + manual content review

---

## Phase 2: High Priority Fixes (P1)

### Task 2.1: Complete Missing Translation Keys - Spanish
**Priority**: P1 - High
**Location**: `translations/spanish_prompts.json`

#### Missing Keys to Add:
1. **utility_format_improvement_choice** (Lines 89-90 in English):
   ```json
   "utility_format_improvement_choice": "\nLa siguiente respuesta necesita ser reformateada para una extracción clara de elección de principios:\n\nRespuesta original: \"{response}\"\n\nPor favor reescriba esto para declarar claramente:\n1. Qué principio eligieron (a, b, c, o d) usando:\n   - Letra: \"principio a\", \"opción b\", etc.\n   - Descripción: \"maximizar ingresos mínimos\", \"maximizar ingresos promedio\", etc.\n   - Lenguaje original: \"la distribución más justa que maximiza el mínimo\", etc.\n\n2. Si eligieron c o d, la cantidad específica de restricción en dólares\n\n3. Su nivel de certeza (muy_inseguro, inseguro, seguro, muy_seguro)\n\n4. Su razonamiento (opcional, ya que se han eliminado los requisitos de razonamiento explícito)\n\nLos cuatro principios para referencia:\n(a) Maximizar ingresos mínimos - se enfoca en el individuo más desfavorecido\n(b) Maximizar ingresos promedio - maximiza el ingreso total en la sociedad\n(c) Maximizar promedio con restricción de mínimo - requiere especificación de ingreso mínimo\n(d) Maximizar promedio con restricción de rango - requiere especificación de límite de brecha de ingresos\n\nFormatee como: \"Elijo [principio] [con restricción si aplica]. Estoy [nivel de certeza] sobre esta elección [razonamiento opcional].\"\n\nEjemplos:\n- \"Elijo principio a. Estoy seguro sobre esta elección.\"\n- \"Elijo maximizar promedio con restricción de mínimo de $X. Estoy muy seguro sobre esta elección.\"\n- \"Elijo el principio que considera el bienestar de los más desfavorecidos. Estoy seguro sobre esta elección.\""
   ```

2. **utility_format_improvement_ranking** (Lines 89-90 in English):
   ```json
   "utility_format_improvement_ranking": "\nLa siguiente respuesta necesita ser reformateada para una extracción clara de clasificación:\n\nRespuesta original: \"{response}\"\n\nPor favor reescriba esto como una lista numerada clasificando los 4 principios del mejor (1) al peor (4):\n\n1. [nombre o descripción del principio]\n2. [nombre o descripción del principio]\n3. [nombre o descripción del principio]\n4. [nombre o descripción del principio]\n\nCerteza general: [nivel de certeza]\n\nLos principios pueden referenciarse usando:\n- Nombres cortos: maximizar mínimo, maximizar promedio, restricción de mínimo, restricción de rango\n- Descripciones completas: \"maximizar ingresos mínimos\", \"maximizar ingresos promedio con restricción de mínimo\", etc.\n- Lenguaje original del manual: \"distribución más justa que maximiza ingresos mínimos\", etc.\n\nNota: Las explicaciones de razonamiento explícito ya no son requeridas, pero pueden incluirse si se proporcionan.\n\nFormato de ejemplo:\n1. Maximizar ingresos mínimos\n2. Maximizar promedio con restricción de mínimo\n3. Maximizar ingresos promedio\n4. Maximizar promedio con restricción de rango\n\nCerteza general: seguro"
   ```

3. **Additional missing utility keys** (check English file lines 91-122 for any missing in Spanish)

#### Acceptance Criteria:
- [ ] All English utility keys have Spanish equivalents
- [ ] Translations maintain technical accuracy
- [ ] JSON structure preserved
- [ ] Parameter placeholders correct

**Estimated Time**: 4 hours
**Dependencies**: Task 1.1 completion

### Task 2.2: Complete Missing Translation Keys - Mandarin
**Priority**: P1 - High
**Location**: `translations/mandarin_prompts.json`

#### Missing Keys to Add:
Similar analysis and translation required for Mandarin file, focusing on utility parsing instructions that are present in English but missing in Mandarin.

**Estimated Time**: 4 hours
**Dependencies**: Task 1.1 completion

### Task 2.3: Standardize Spanish Terminology
**Priority**: P1 - High
**Location**: `translations/spanish_prompts.json`

#### Specific Standardizations Needed:

1. **Constraint Terminology**:
   - Standardize on "restricción" throughout (currently mixed with "limitación")
   - Update all instances consistently

2. **Principle Name Consistency**:
   ```json
   // Standardize to:
   "maximizing_floor": "Maximizar los ingresos mínimos"
   "maximizing_average": "Maximizar los ingresos promedio" 
   "maximizing_average_floor_constraint": "Maximizar los ingresos promedio con restricción de ingreso mínimo"
   "maximizing_average_range_constraint": "Maximizar los ingresos promedio con restricción de rango"
   ```

3. **Formal Register Consistency**:
   - Ensure consistent use of "usted" vs "tú" (should be "usted" for formal research context)
   - Standardize verb conjugations for formal address

#### Actions:
1. Create terminology glossary
2. Search and replace inconsistent terms
3. Manual review of all principle references
4. Consistency check across all prompts

#### Acceptance Criteria:
- [ ] Single terminology choice for all constraint-related terms
- [ ] Consistent principle name formatting
- [ ] Consistent formal register throughout
- [ ] No terminology conflicts within file

**Estimated Time**: 3 hours
**Dependencies**: Tasks 2.1 completion

---

## Phase 3: Medium Priority Improvements (P2)

### Task 3.1: Improve Mandarin Formatting Complexity
**Priority**: P2 - Medium
**Location**: `translations/mandarin_prompts.json`

#### Issues to Address:
1. **Voting Instructions Formatting** (Lines 30-31):
   - Simplify complex voting rule explanations
   - Break down long paragraphs into digestible sections
   - Improve readability while maintaining meaning

2. **Technical Term Accessibility**:
   - Review economic terminology for accessibility
   - Consider adding brief explanations for complex concepts
   - Maintain academic rigor while improving clarity

#### Specific Actions:
1. **Reformat phase2_discussion_prompt_simple** (Line 30):
   - Break complex voting rules into numbered steps
   - Add clear section headers
   - Simplify sentence structure without losing meaning

2. **Reformat phase2_discussion_prompt_complex** (Line 31):
   - Similar treatment as simple prompt
   - Ensure complex voting system explanation is clear

#### Acceptance Criteria:
- [ ] Voting instructions easier to follow
- [ ] Maintain all original meaning and functionality
- [ ] Improved readability scores
- [ ] No loss of technical accuracy

**Estimated Time**: 3 hours
**Dependencies**: Task 2.2 completion

### Task 3.2: Enhance Spanish Constraint Explanations
**Priority**: P2 - Medium
**Location**: `translations/spanish_prompts.json`

#### Specific Improvements:
1. **Clarify constraint principle explanations** in main prompts
2. **Improve example formatting** for constraint specifications
3. **Enhance error message clarity** for constraint-related errors

#### Acceptance Criteria:
- [ ] Clearer constraint explanations
- [ ] Better formatted examples
- [ ] More helpful error messages
- [ ] Maintained technical accuracy

**Estimated Time**: 2 hours
**Dependencies**: Task 2.3 completion

---

## Phase 4: Quality Assurance and Validation (P1-P2)

### Task 4.1: Automated Validation System
**Priority**: P1 - High

#### Create Validation Script:
1. **JSON Structure Validation**:
   ```python
   # Script to validate:
   # - JSON syntax correctness
   # - Key completeness across languages
   # - Parameter placeholder consistency
   # - Character encoding issues
   ```

2. **Content Validation**:
   ```python
   # Script to check:
   # - No mixed language content
   # - Consistent terminology usage
   # - Required parameter placeholders present
   # - No broken formatting
   ```

#### Deliverables:
- [ ] `validate_translations.py` script
- [ ] Automated test that can be run before deployments
- [ ] Documentation for validation process

**Estimated Time**: 4 hours
**Dependencies**: None (can run in parallel)

### Task 4.2: Manual Quality Review
**Priority**: P1 - High

#### Review Process:
1. **Native Speaker Review** (if available):
   - Spanish speaker review of all Spanish translations
   - Mandarin speaker review of all Mandarin translations

2. **Technical Accuracy Review**:
   - Verify all economic/experimental terms correctly translated
   - Ensure consistency with research methodology
   - Check all system messages and error handling

3. **Usability Testing**:
   - Test complete experimental flow in each language
   - Verify all prompts display correctly
   - Test error conditions and constraint handling

#### Acceptance Criteria:
- [ ] Native speaker approval of translations
- [ ] Technical accuracy verified
- [ ] Complete experimental flow tested
- [ ] All edge cases validated

**Estimated Time**: 6 hours (across reviewers)
**Dependencies**: Completion of phases 1-3

---

## Phase 5: Documentation and Process Improvement (P3)

### Task 5.1: Create Translation Guidelines
**Priority**: P3 - Low

#### Deliverables:
1. **Translation Style Guide**:
   - Terminology preferences
   - Tone and register guidelines
   - Technical term handling
   - Cultural adaptation guidelines

2. **Quality Assurance Process**:
   - Translation review workflow
   - Validation checklist
   - Testing procedures
   - Sign-off process

**Estimated Time**: 3 hours

### Task 5.2: Implement Monitoring System
**Priority**: P3 - Low

#### Create Ongoing Monitoring:
1. **Translation Completeness Monitoring**:
   - Script to detect new English keys without translations
   - Automated alerts for translation gaps

2. **Quality Monitoring**:
   - Regular validation script execution
   - Terminology consistency checks
   - User feedback integration

**Estimated Time**: 2 hours

---

## Implementation Timeline

### Week 1 (Critical Path)
- **Day 1-2**: Task 1.1 (Fix mixed language content)
- **Day 3-4**: Task 2.1 (Complete Spanish missing keys)
- **Day 5**: Task 2.2 (Complete Mandarin missing keys)

### Week 2 (High Priority)
- **Day 1-2**: Task 2.3 (Standardize Spanish terminology)
- **Day 3**: Task 3.1 (Improve Mandarin formatting)
- **Day 4**: Task 3.2 (Enhance Spanish explanations)
- **Day 5**: Task 4.1 (Create validation system)

### Week 3 (Quality Assurance)
- **Day 1-3**: Task 4.2 (Manual quality review)
- **Day 4-5**: Task 5.1 (Create guidelines)

### Week 4 (Process Improvement)
- **Day 1**: Task 5.2 (Implement monitoring)
- **Day 2-5**: Buffer time and final testing

## Resource Requirements

### Human Resources:
- **Developer/Translator**: 1 person, 3-4 weeks
- **Spanish Native Speaker**: 1 person, 8 hours
- **Mandarin Native Speaker**: 1 person, 8 hours
- **Technical Reviewer**: 1 person, 4 hours

### Technical Requirements:
- JSON editing tools
- Text comparison tools
- Python environment for validation scripts
- Git for version control

## Risk Assessment

### High Risks:
1. **Mixed language content in production**: Could confuse users and break experiments
   - **Mitigation**: P0 priority, immediate fix required

2. **Missing utility instructions**: Could cause parsing errors
   - **Mitigation**: P1 priority, comprehensive testing

### Medium Risks:
1. **Terminology inconsistencies**: Could cause user confusion
   - **Mitigation**: Systematic standardization process

2. **Translation quality**: Could affect experimental validity
   - **Mitigation**: Native speaker review and testing

## Success Metrics

### Completion Metrics:
- [ ] 100% of English keys have translations in both languages
- [ ] 0 mixed language content instances
- [ ] 100% terminology consistency within each language
- [ ] All validation tests pass

### Quality Metrics:
- [ ] Native speaker approval rating ≥ 95%
- [ ] Technical accuracy rating ≥ 98%
- [ ] User testing satisfaction ≥ 90%
- [ ] Zero critical translation errors in production

## Validation Procedures

### Pre-Implementation:
1. Backup all current translation files
2. Set up testing environment
3. Prepare validation scripts

### During Implementation:
1. Validate JSON syntax after each change
2. Run terminology consistency checks
3. Test functionality with each update

### Post-Implementation:
1. Complete system testing
2. Native speaker final review
3. User acceptance testing
4. Production deployment validation

## Rollback Plan

### If Issues Occur:
1. **Immediate rollback** to backed-up translation files
2. **Issue identification** and isolated fix
3. **Targeted re-deployment** of corrected sections
4. **Full validation** before final deployment

## Conclusion

This implementation plan provides a comprehensive, prioritized approach to resolving all identified translation issues. The critical mixed-language content issue must be addressed immediately, followed by systematic completion of missing translations and terminology standardization.

The plan balances urgency with thoroughness, ensuring both immediate functionality fixes and long-term quality improvements. With proper execution, all translation issues will be resolved within 3-4 weeks, resulting in high-quality, consistent, and accurate translations across all three languages.

---

**Plan Version**: 1.0  
**Created**: 2025-08-27  
**Next Review**: After Phase 1 completion  
**Owner**: Translation Team Lead