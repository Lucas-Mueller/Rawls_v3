# Spanish Translation Letter Removal Implementation Plan

## Overview
Based on the successful implementation for English prompts, this plan outlines the systematic removal of letter-based principle naming (a, b, c, d) from the Spanish translation file `translations/spanish_prompts.json`.

## Analysis Summary
The Spanish translation file contains **8 specific locations** where principles are referenced by letters (a, b, c, d), mirroring the English file structure.

## Files to Modify
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`

## Identified Locations with Letter References

### 1. Line 28 - `phase1_rounds1_4_principle_application`
**Current issues:**
- `"Si elige un principio de restricción (c o d), DEBE especificar la cantidad de restricción en dólares."`
- `"Exponga claramente su elección: \"Elijo [principio a/b/c/d]\""`
- `"Ejemplo: \"Elijo el principio c (maximizar los ingresos promedio con restricción de ingreso mínimo)\""`

**Changes needed:**
- Replace `"(c o d)"` with `"(maximizar los ingresos promedio con restricción de ingreso mínimo o maximizar los ingresos promedio con restricción de rango)"`
- Replace `"[principio a/b/c/d]"` with `"[nombre del principio]"`
- Update example to use principle name instead of letter

### 2. Line 30 - `phase2_discussion_prompt_simple`
**Current issues:**
- `"(a) **Maximizar los ingresos mínimos**:"`
- `"(b) **Maximizar los ingresos promedio**:"`
- `"(c) **Maximizar los ingresos promedio con restricción de ingreso mínimo**:"`
- `"(d) **Maximizar los ingresos promedio con restricción de rango**:"`
- `"Para los principios de restricción (c o d), especifique la cantidad"`
- Examples with letters: `"Mi preferencia es el principio a"`

**Changes needed:**
- Remove letter prefixes from all principle descriptions
- Update constraint reference to use principle names
- Update all examples to use principle names

### 3. Line 33 - `utility_secret_ballot_request`
**Current issues:**
- `"(a) Maximizar los ingresos mínimos:"`
- `"(b) Maximizar los ingresos promedio:"`
- `"(c) Maximizar los ingresos promedio con restricción de ingreso mínimo:"`
- `"(d) Maximizar los ingresos promedio con restricción de rango:"`
- `"Mi elección de voto es principio c con una restricción"`

**Changes needed:**
- Remove letter prefixes from principle descriptions
- Update example to use principle name

### 4. Line 45 - `phase1_application_round`
**Current issues:**
- `"Si elige (c) o (d), tendrá que decirnos cuál es esa restricción"`

**Changes needed:**
- Replace `"(c) o (d)"` with principle names for constraint principles

### 5. Line 46 - `phase2_discussion_prompt_complex`
**Current issues:**
- Same letter prefixes as in `phase2_discussion_prompt_simple`

**Changes needed:**
- Remove all letter prefixes from principle descriptions

### 6. Line 47 - `phase2_secret_ballot_vote`
**Current issues:**
- `"Si elige (c) o (d), DEBE especificar la cantidad exacta"`

**Changes needed:**
- Replace letter references with principle names

### 7. Line 89 - `utility_format_improvement_choice`
**Current issues:**
- `"Qué principio eligieron (a, b, c, o d)"`
- `"(a) Maximizar ingresos mínimos"`
- `"(b) Maximizar ingresos promedio"`
- `"(c) Maximizar promedio con restricción de mínimo"`
- `"(d) Maximizar promedio con restricción de rango"`
- `"Si eligieron c o d"`

**Changes needed:**
- Remove all letter references
- Update instructions to refer to principle names
- Update all examples

### 8. Line 95 - `utility_llm_parse_principle_choice`
**Current issues:**
- `"(a) Maximizar ingresos mínimos"`
- `"(b) Maximizar ingresos promedio"`
- `"(c) Maximizar promedio con restricción de mínimo"`
- `"(d) Maximizar promedio con restricción de rango"`
- `"Letras: a, b, c, d"`
- JSON format examples with letters
- Multiple critical rules referencing letters

**Changes needed:**
- Remove letter-based principle descriptions
- Remove letter references from participant reference methods
- Update JSON format examples to use principle names
- Update critical rules to reference principle names
- Update all examples

## Implementation Strategy

### Phase 1: Basic Letter Removal
1. **Remove letter prefixes** from all principle descriptions
2. **Update constraint references** from letters to principle names
3. **Update examples** to use descriptive principle names

### Phase 2: Spanish-Specific Considerations
1. **Maintain grammatical correctness** in Spanish
2. **Preserve formal/informal tone** consistency with original translations
3. **Ensure gender agreement** for adjectives and articles
4. **Update instruction text** to flow naturally in Spanish

### Phase 3: Utility Section Updates
1. **Update parsing logic** to work with Spanish principle names
2. **Maintain JSON format compatibility** with system expectations
3. **Update critical rules** to reference Spanish principle names
4. **Test validation logic** with Spanish inputs

## Spanish Principle Name Mappings
Based on existing translations in the `common.principle_names` section:

- **(a)** → `"Maximizar los ingresos mínimos"`
- **(b)** → `"Maximizar los ingresos promedio"`
- **(c)** → `"Maximizar los ingresos promedio con restricción de ingreso mínimo"`
- **(d)** → `"Maximizar los ingresos promedio con restricción de rango"`

## Constraint Reference Translations
- `"(c o d)"` → `"principios de restricción (maximizar los ingresos promedio con restricción de ingreso mínimo o maximizar los ingresos promedio con restricción de rango)"`
- `"principio c"` → `"maximizar los ingresos promedio con restricción de ingreso mínimo"`
- `"principio d"` → `"maximizar los ingresos promedio con restricción de rango"`

## Testing Strategy
1. **JSON Syntax Validation**: Verify file is valid JSON after changes
2. **System Functionality**: Run test suite to ensure Spanish prompts work
3. **Translation Consistency**: Verify principle names match across all references
4. **User Experience**: Test Spanish experiment flow end-to-end

## Risk Mitigation
1. **Backup original file** before making changes
2. **Incremental updates** with testing at each step
3. **Version control** to track all changes
4. **Rollback plan** if issues are discovered

## Success Criteria
- ✅ All letter references (a, b, c, d) removed from Spanish prompts
- ✅ Principle names used consistently throughout
- ✅ JSON file remains syntactically valid
- ✅ System functionality preserved
- ✅ Spanish grammar and flow maintained
- ✅ Test suite passes completely

## Implementation Order
1. **phase2_discussion_prompt_simple** - Most critical for user experience
2. **phase2_discussion_prompt_complex** - Matching pair to above
3. **utility_secret_ballot_request** - Voting functionality
4. **phase1_rounds1_4_principle_application** - Individual choice prompts
5. **phase1_application_round** - Basic application prompts
6. **phase2_secret_ballot_vote** - Final voting
7. **utility_format_improvement_choice** - Parser improvements
8. **utility_llm_parse_principle_choice** - Most complex, parsing logic

## Notes
- Spanish translation maintains the same structure and logic as English
- All changes should preserve the experimental integrity
- User instructions should remain clear and unambiguous
- Constraint principles must still clearly indicate the need for dollar amounts