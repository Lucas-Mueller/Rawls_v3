# Legacy Code Marked for Deletion

This file tracks legacy voting trigger phrase detection code that will be removed during the tool-based voting implementation.

**Created**: 2025-08-31  
**Purpose**: Track legacy code for cleanup after tool-based voting implementation  
**Status**: Initial tracking - to be updated during implementation

## Files and Methods to Delete

### Core Phase2Manager Methods
- [x] **File**: `core/phase2_manager.py`
  - [x] **Method**: `_is_voting_trigger_phrase()` (lines 1249-1286)
    - Contains hardcoded phrase lists for English, Spanish, and Mandarin
    - REPLACED with tool call detection
  - [x] **Code Block**: Voting trigger phrase detection in `_handle_complex_voting_mode()` (line 1306)
    - `if not self._is_voting_trigger_phrase(statement):`
    - REPLACED with tool call processing

### Translation File Cleanup
- [ ] **File**: `translations/english_prompts.json`
  - [ ] **Section**: Voting trigger phrase references (if any)
  - [ ] **Content**: Phase 2 instructions mentioning trigger phrases

- [ ] **File**: `translations/spanish_prompts.json` 
  - [ ] **Section**: Voting trigger phrase references (if any)
  - [ ] **Content**: Phase 2 instructions mentioning trigger phrases

- [ ] **File**: `translations/mandarin_prompts.json`
  - [ ] **Section**: Voting trigger phrase references (if any) 
  - [ ] **Content**: Phase 2 instructions mentioning trigger phrases

### Test Files - Legacy Voting Phrase Tests
- [ ] **File**: `tests/unit/test_phase2_voting_complete_flow.py`
  - [ ] **Method**: `test_voting_trigger_phrase_detection_english()` (lines 175-184)
  - [ ] **Method**: `test_voting_trigger_phrase_detection_spanish()` (lines 200-209)
  - [ ] **Method**: `test_voting_trigger_phrase_detection_mandarin()` (lines 223-232)
  - [ ] **Method**: All test methods that mock `_is_voting_trigger_phrase`

- [ ] **File**: `tests/integration/test_two_stage_voting_integration.py`
  - [ ] **Method**: `test_voting_trigger_phrase_detection()` (lines 115-134)
  - [ ] **Assertions**: All assertions testing `_is_voting_trigger_phrase` method

- [ ] **File**: `tests/integration/test_phase2_voting_integration.py`
  - [ ] **Code**: All mocking of `_is_voting_trigger_phrase` (lines 134, 182, etc.)
  - [ ] **Tests**: Any tests specifically validating trigger phrase patterns

## Implementation Progress

### Completed Deletions
- [ ] None yet - implementation not started

### Pending Analysis
During implementation, analyze these areas for additional legacy code:
- Phase 2 instruction templates referencing "say X to vote"
- Documentation mentioning voting trigger phrases
- Configuration options for phrase pattern customization
- Any utility methods supporting phrase detection

## Notes
- This file will be updated during implementation as legacy code is identified and removed
- Each deletion should be verified against test suite to ensure no regressions
- Some test files may need complete rewriting rather than selective deletion

## Post-Implementation Cleanup
After tool implementation is complete and tested:
1. Delete all checked items from this list
2. Run full test suite to ensure no references remain
3. Search codebase for any remaining phrase detection patterns
4. Archive this file or delete if all items completed