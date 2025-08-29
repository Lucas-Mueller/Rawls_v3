# Mandarin Translation Letter Removal Implementation Plan

## Overview
Based on the successful implementation for English prompts and the plan for Spanish translation, this document outlines the systematic removal of letter-based principle naming (a, b, c, d) from the Mandarin translation file `translations/mandarin_prompts.json`.

## Analysis Summary
The Mandarin translation file contains **6 specific locations** where principles are referenced by letters (a, b, c, d), similar to the English and Spanish files but with some differences in structure.

## Files to Modify
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`

## Identified Locations with Letter References

### 1. Line 28 - `phase1_rounds1_4_principle_application`
**Current issues:**
- `"我选择 [a/b/c/d 原则]"` (Choose [principle a/b/c/d])
- `"如果选择 c 或 d，请具体说明"` (If choosing c or d, specify)
- Example references principle letters

**Changes needed:**
- Replace `"[a/b/c/d 原则]"` with `"[原则名称]"` (principle name)
- Replace `"c 或 d"` with constraint principle names
- Update example to use descriptive principle names

### 2. Line 30 - `phase2_discussion_prompt_simple`
**Current issues:**
- `"(a) **最大化最低收入**：选择使最低收入最大化的分配"`
- `"(b) **最大化平均收入**：选择使平均收入最大化的分配"`
- `"(c) **在最低收入约束下最大化平均收入**：在确保最低收入的同时最大化平均收入"`
- `"(d) **在范围约束下最大化平均收入**：在限制收入差距的同时最大化平均收入"`

**Changes needed:**
- Remove letter prefixes (a), (b), (c), (d) from all principle descriptions
- Maintain proper Chinese punctuation and formatting

### 3. Line 31 - `phase2_discussion_prompt_complex`
**Current issues:**
- Same letter prefixes as in `phase2_discussion_prompt_simple`

**Changes needed:**
- Remove all letter prefixes from principle descriptions
- Maintain consistent formatting with simple prompt

### 4. Line 33 - `utility_secret_ballot_request`
**Current issues:**
- `"(a) 最低收入最大化：选择使社会最低收入最大化的收入分配"`
- `"(b) 平均收入最大化：选择使社会平均收入最大化的收入分配"`
- `"(c) 在最低收入约束条件下最大化平均收入：只有在保证每个人都获得特定最低收入后"`
- `"(d) 在范围约束条件下最大化平均收入：只有在保证最贫穷与最富有个人之间的收入差距不超过特定数额后"`
- Example: `"我的投票选择是原则c，最低收入约束为$15,000"`

**Changes needed:**
- Remove letter prefixes from all principle descriptions
- Update example to use principle name instead of letter

### 5. Line 57 - `utility_llm_parse_principle_choice`
**Current issues:**
- `"(a) 最大化最低收入 - 专注于最弱势的个体"`
- `"(b) 最大化平均收入 - 最大化社会总收入"`
- `"(c) 在最低收入约束下最大化平均收入"`
- `"(d) 在范围约束下最大化平均收入"`
- `"字母：a、b、c、d"` (Letters: a, b, c, d)
- Critical rules referencing letters
- JSON examples with letter format

**Changes needed:**
- Remove letter-based principle descriptions
- Remove letter references from participant reference methods
- Update JSON format examples to use principle names
- Update critical rules to reference principle names in Chinese

### 6. Line 105 - `phase1_application_round`
**Current issues:**
- `"(a) 最大化底线收入"`
- `"(b) 最大化平均收入"`
- `"(c) 在底线约束下最大化平均收入"`
- `"(d) 在范围约束下最大化平均收入"`
- `"如果您选择(c)或(d)，您必须告诉我们"` (If you choose (c) or (d))

**Changes needed:**
- Remove letter prefixes from principle list
- Replace letter references with principle names

### 7. Line 106 - `phase2_secret_ballot_vote`
**Current issues:**
- `"(a) 最大化底线收入"`
- `"(b) 最大化平均收入"`
- `"(c) 在底线约束下最大化平均收入"`
- `"(d) 在范围约束下最大化平均收入"`
- `"如果您选择(c)或(d)，您必须指定"` (If you choose (c) or (d))

**Changes needed:**
- Remove letter prefixes from principle list
- Update constraint reference to use principle names

## Implementation Strategy

### Phase 1: Basic Letter Removal
1. **Remove letter prefixes** from all principle descriptions
2. **Update constraint references** from letters to principle names in Chinese
3. **Update examples** to use descriptive principle names

### Phase 2: Chinese-Specific Considerations
1. **Maintain proper Chinese grammar** and sentence structure
2. **Preserve formal tone** consistent with academic/experimental context
3. **Ensure character spacing** follows Chinese typography conventions
4. **Update instructional text** to flow naturally in Chinese
5. **Handle measure words** (量词) appropriately for principles and constraints

### Phase 3: Utility Section Updates
1. **Update parsing logic** to work with Chinese principle names
2. **Maintain JSON format compatibility** with system expectations
3. **Update critical rules** to reference Chinese principle names
4. **Test validation logic** with Chinese inputs

## Chinese Principle Name Mappings
Based on existing translations in the `common.principle_names` section:

- **(a)** → `"最低收入最大化"` (Maximizing floor income)
- **(b)** → `"平均收入最大化"` (Maximizing average income)  
- **(c)** → `"在最低收入约束条件下最大化平均收入"` (Maximizing average with floor constraint)
- **(d)** → `"在范围约束条件下最大化平均收入"` (Maximizing average with range constraint)

## Constraint Reference Translations
- `"(c)或(d)"` → `"约束原则（在最低收入约束条件下最大化平均收入或在范围约束条件下最大化平均收入）"`
- `"原则c"` → `"在最低收入约束条件下最大化平均收入"`
- `"原则d"` → `"在范围约束条件下最大化平均收入"`

## Chinese Language Considerations

### Typography and Formatting
- **Punctuation**: Maintain Chinese punctuation marks (，。：；)
- **Parentheses**: Use Chinese parentheses where appropriate （）
- **Number formatting**: Keep consistent with existing Chinese text
- **Spacing**: Follow Chinese text spacing conventions

### Grammatical Structure
- **Classifier usage**: Ensure proper measure words for counting principles
- **Sentence flow**: Maintain natural Chinese sentence patterns
- **Technical terms**: Keep consistency with established economic terminology
- **Formal register**: Preserve academic/formal tone throughout

### Cultural Adaptation
- **Context clarity**: Ensure instructions are culturally appropriate
- **Decision-making language**: Use terminology familiar to Chinese speakers
- **Group dynamics**: Consider Chinese group decision-making conventions

## Testing Strategy
1. **JSON Syntax Validation**: Verify file is valid JSON after changes
2. **Character Encoding**: Ensure proper UTF-8 encoding maintained
3. **System Functionality**: Run test suite to ensure Chinese prompts work
4. **Translation Consistency**: Verify principle names match across all references
5. **User Experience**: Test Chinese experiment flow end-to-end
6. **Language Quality**: Review for natural Chinese expression

## Risk Mitigation
1. **Backup original file** before making changes
2. **Character encoding preservation** during edits
3. **Incremental updates** with testing at each step
4. **Version control** to track all changes
5. **Native speaker review** if possible
6. **Rollback plan** if issues are discovered

## Success Criteria
- ✅ All letter references (a, b, c, d) removed from Chinese prompts
- ✅ Principle names used consistently throughout in proper Chinese
- ✅ JSON file remains syntactically valid with proper encoding
- ✅ System functionality preserved
- ✅ Chinese grammar and natural flow maintained
- ✅ Technical terminology remains accurate
- ✅ Test suite passes completely

## Implementation Order
1. **phase2_discussion_prompt_simple** - Most critical for user experience
2. **phase2_discussion_prompt_complex** - Matching pair to above
3. **utility_secret_ballot_request** - Voting functionality
4. **phase1_rounds1_4_principle_application** - Individual choice prompts
5. **phase1_application_round** - Basic application prompts
6. **phase2_secret_ballot_vote** - Final voting
7. **utility_llm_parse_principle_choice** - Most complex, parsing logic

## Special Notes for Chinese Implementation

### Character Consistency
- Ensure consistent use of simplified vs traditional characters (file uses simplified)
- Maintain consistent terminology for economic concepts
- Preserve formal academic register throughout

### JSON Handling
- Be careful with Unicode characters in JSON strings
- Test JSON parsing with Chinese characters
- Ensure proper escaping of quotes within Chinese text

### Parsing Considerations
- Update parsing rules to recognize Chinese principle names
- Consider character-based pattern matching vs English word-based
- Test constraint amount extraction with Chinese currency formatting

## Example Transformations

**Before:**
```
"(a) **最大化最低收入**：选择使最低收入最大化的分配"
```

**After:**
```
"**最低收入最大化**：选择使最低收入最大化的分配"
```

**Before:**
```
"如果您选择(c)或(d)，您必须指定确切的约束金额"
```

**After:**
```
"如果您选择约束原则（在最低收入约束条件下最大化平均收入或在范围约束条件下最大化平均收入），您必须指定确切的约束金额"
```

This plan ensures the Mandarin translation will maintain proper Chinese grammar, natural expression, and cultural appropriateness while removing all letter-based references and making principles accessible only by their descriptive names.