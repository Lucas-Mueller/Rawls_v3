# Claude Code Phase 2 Implementation Plan

Based on the comprehensive review in `phase2_implementation_review.md`, this plan addresses the identified issues and optimization opportunities while maintaining the system's clean architecture and robust error handling capabilities.

## Priority 1: Critical Bug Fix

### 1. Correct Speaking-Order Restriction
**File:** `core/phase2_manager.py` (speaking order logic)
- **Issue:** Tracks previous round starter instead of last speaker
- **Fix:** Track `last_round_finisher` and prevent them from starting next round
- **Impact:** Implements correct turn-taking dynamics per specification

## Priority 2: Code Quality & Cleanup

### 2. Fix Type Annotations
**File:** `core/phase2_manager.py:_apply_group_principle_and_calculate_payoffs`
- **Issue:** `assigned_classes` annotated as `Dict[str, str]` but stores `IncomeClass` enum values
- **Fix:** Correct type annotation or add explicit string coercion
- **Impact:** Improves type safety and code clarity

### 3. Remove Code Redundancy
**File:** `core/phase2_manager.py:_get_participant_statement_with_retry`
- **Issue:** Duplicate `continue` statement in error handling
- **Fix:** Remove redundant continue statement
- **Impact:** Cleaner error handling flow

### 4. Clean Up Unused Helper Method
**File:** `core/phase2_manager.py`
- **Issue:** `_determine_assigned_class` exists but is unused in current flow
- **Fix:** Either integrate for consistent naming/i18n or remove entirely
- **Impact:** Reduces code confusion and maintenance burden

### 5. Update Test References
**File:** Test files referencing legacy method names
- **Issue:** Legacy test references `_check_for_vote_agreement` (now `_check_unanimous_vote_agreement`)
- **Fix:** Update test method references
- **Impact:** Maintains test accuracy and prevents future confusion

## Priority 3: Testing

### 6. Comprehensive Testing
**Files:** `tests/` directory
- **Task:** Run full test suite to validate all fixes
- **Additional:** Add specific tests for speaking-order restriction after fix
- **Impact:** Ensures all changes work correctly and maintain system reliability

## Implementation Strategy

1. **Start with critical fix** (item 1) as it affects experimental validity
2. **Clean up code quality issues** (items 2-5) for maintainability
3. **Run comprehensive tests** (item 6) to verify all fixes work correctly

## Implementation Notes

Each fix will be implemented with careful attention to:
- Maintaining backward compatibility
- Following existing code patterns and architecture
- Ensuring proper error handling and logging
- Validating changes through comprehensive testing

## Files and Key References

- Phase 2 orchestration: `core/phase2_manager.py`
- Group state/results: `models/experiment_types.py`
- Distribution generation/logic: `core/distribution_generator.py`
- Parsing/validation: `experiment_agents/utility_agent.py`
- Memory management: `utils/memory_manager.py`
- i18n prompts: `translations/english_prompts.json` (and others)
- Logging: `utils/agent_centric_logger.py`, `models/logging_types.py`
- Config models: `config/models.py`; defaults: `config/default_config.yaml`

## Expected Outcome

After implementing these changes, the Phase 2 system will:
- Follow correct speaking-order restrictions per master plan specification
- Have cleaner, more maintainable code with proper type safety
- Maintain the existing high-quality architecture and error handling
- Preserve the secret ballot mechanism as designed