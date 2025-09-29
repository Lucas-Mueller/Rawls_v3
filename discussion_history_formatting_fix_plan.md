# Discussion History Formatting Fix Implementation Plan

## Objective

Remove bold formatting from discussion history headers across all contexts to unify formatting. The discussion history should appear the same whether agents are making statements or updating memory.

## Problem Statement

Currently, discussion history appears with bold formatting (`**=== DISCUSSION HISTORY ===**`) when agents are asked to make statements, but without bold formatting when updating memory. User wants consistent non-bold formatting across all contexts.

## Solution Approach

**Simple Template Update**: Remove bold markdown (`**`) from the `context_discussion_history_section_format` template in all language files.

## Implementation Steps

### 1. Update English Translation Template

**File**: `translations/english_prompts.json`
**Line**: Search for `context_discussion_history_section_format`

**Current**:
```json
"context_discussion_history_section_format": "**=== DISCUSSION HISTORY ===**\n{discussion_history}\n=========================="
```

**Updated**:
```json
"context_discussion_history_section_format": "=== DISCUSSION HISTORY ===\n{discussion_history}\n=========================="
```

### 2. Update Spanish Translation Template

**File**: `translations/spanish_prompts.json`
**Line**: Search for `context_discussion_history_section_format`

**Current**:
```json
"context_discussion_history_section_format": "**=== HISTORIAL DE DISCUSIÓN ===**\n{discussion_history}\n================================"
```

**Updated**:
```json
"context_discussion_history_section_format": "=== HISTORIAL DE DISCUSIÓN ===\n{discussion_history}\n================================"
```

### 3. Update Mandarin Translation Template

**File**: `translations/mandarin_prompts.json`
**Line**: Search for `context_discussion_history_section_format`

**Current**:
```json
"context_discussion_history_section_format": "**=== 讨论历史 ===**\n{discussion_history}\n=================="
```

**Updated**:
```json
"context_discussion_history_section_format": "=== 讨论历史 ===\n{discussion_history}\n=================="
```

## Implementation Details

### Change Summary
- **Files Modified**: 3 translation files
- **Lines Changed**: 3 lines total (1 per language)
- **Change Type**: Remove bold markdown (`**`) from headers
- **Structure Preserved**: Headers and separators remain, only bold emphasis removed

### Before and After Comparison

**Before (Bold)**:
```
**=== DISCUSSION HISTORY ===**
Alice: I think we should consider the floor constraint approach.
Bob: I agree, but we should also look at maximizing average income.
==========================
```

**After (Non-Bold)**:
```
=== DISCUSSION HISTORY ===
Alice: I think we should consider the floor constraint approach.
Bob: I agree, but we should also look at maximizing average income.
==========================
```

## Testing Plan

### 1. Unit Tests
**Objective**: Verify template formatting produces expected output
**Files**: Create or update tests in `tests/unit/test_language_manager.py`

**Test Cases**:
- Template renders without bold formatting
- All 3 languages produce consistent formatting
- Empty discussion history still works
- Long discussion history maintains structure

### 2. Integration Tests
**Objective**: Confirm end-to-end formatting consistency
**Files**: Use existing `tests/integration/` test structure

**Test Cases**:
- Statement prompts show non-bold discussion history
- Memory updates show identical formatting
- Multilingual experiments maintain consistency

### 3. Manual Verification
**Objective**: Visual confirmation of formatting consistency

**Steps**:
1. Run a Phase 2 experiment with multiple agents
2. Examine statement prompts - verify discussion history is not bold
3. Check agent memory updates - verify identical formatting
4. Test across English, Spanish, and Mandarin configurations

## Risk Assessment

### Risk Level: **Minimal**

**Why Low Risk**:
- **Cosmetic Change**: Only affects visual presentation, no functional logic
- **Template-Only**: No code logic modifications required
- **Isolated Impact**: Changes confined to translation templates
- **Reversible**: Easy to revert if issues arise

**Potential Issues**:
- **Visual Regression**: Some users might prefer bold headers
- **Test Updates**: Existing tests expecting bold formatting may need updates

**Mitigations**:
- **Backup**: Git version control allows easy rollback
- **Testing**: Comprehensive test coverage before deployment
- **Validation**: Manual verification across all language configurations

## Rollback Plan

If issues arise, rollback is straightforward:

1. **Git Revert**: `git revert <commit-hash>`
2. **Manual Revert**: Re-add `**` around headers in all 3 translation files
3. **Testing**: Run smoke tests to verify rollback successful

## Success Criteria

### Functional Requirements
- [x] Discussion history appears without bold formatting in statement contexts
- [x] Discussion history formatting matches memory update formatting
- [x] All 3 languages show consistent non-bold formatting
- [x] Existing functionality remains unchanged

### Quality Requirements
- [x] No regression in statement generation
- [x] No regression in memory update processes
- [x] Translation integrity maintained across all languages
- [x] Test suite passes without modification (or minimal updates)

## Implementation Timeline

**Total Effort**: 30 minutes

**Breakdown**:
- **Changes**: 10 minutes (3 simple template edits)
- **Testing**: 15 minutes (run relevant test suites)
- **Validation**: 5 minutes (manual verification in one language)

**Dependencies**: None

## Post-Implementation

### Validation Steps
1. **Automated Testing**: Run test suite to verify no regressions
2. **Manual Testing**: Quick experiment run to visually confirm formatting
3. **Documentation**: Update this plan with actual results

### Monitoring
- **User Feedback**: Monitor for any formatting preference feedback
- **Test Results**: Ensure ongoing tests pass with new formatting
- **Multilingual Consistency**: Periodic verification across all languages

## Conclusion

This is a minimal, targeted fix that addresses the user's formatting consistency request. The solution removes bold formatting from discussion history headers while preserving all structural elements and maintaining multilingual support. The change is low-risk, easily reversible, and requires no code logic modifications.