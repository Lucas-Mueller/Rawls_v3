# _current_public_history Usage Locations

**Date**: 2025-10-01
**Purpose**: Document all production code uses of `_current_public_history` for Phase 2 refactoring

---

## Production Code Locations

### Assignments (4 locations in core/phase2_manager.py)

1. **Line 334** - Discussion statement preparation
   ```python
   self.config._current_public_history = discussion_state.public_history
   ```
   - Context: Before getting participant statement
   - Method: `_get_participant_statement()`
   - Purpose: Provide history for discussion prompt context header

2. **Line 475** - Vote initiation preparation
   ```python
   self.config._current_public_history = discussion_state.public_history
   ```
   - Context: Before prompting for vote initiation
   - Method: `_process_vote_initiation()`
   - Purpose: Provide history for voting context

3. **Line 499** - Memory update (vote decision)
   ```python
   self.config._current_public_history = discussion_state.public_history
   ```
   - Context: Before updating memory with vote decision
   - Method: `_process_vote_initiation()`
   - Purpose: Provide history for memory update context

4. **Line 735** - Post-round memory updates (batch)
   ```python
   self.config._current_public_history = discussion_state.public_history
   ```
   - Context: Before batch updating all participants' memory post-round
   - Method: `_run_group_discussion()`
   - Purpose: Provide history for memory update contexts

### Reads (2 locations in experiment_agents/participant_agent.py)

1. **Line 289** - Phase 2 discussion stage
   ```python
   public_history = getattr(experiment_config, '_current_public_history', '') if experiment_config else ''
   ```
   - Context: Formatting Phase 2 discussion instructions
   - Function: `format_context_info()`
   - Purpose: Get discussion history for context header

2. **Line 304** - Phase 2 fallback (no explicit stage)
   ```python
   public_history = getattr(experiment_config, '_current_public_history', '') if experiment_config else ''
   ```
   - Context: Formatting Phase 2 instructions when no stage specified
   - Function: `format_context_info()`
   - Purpose: Get discussion history for context header

### Comment Only (1 location in core/services/voting_service.py)

**Line 272** - Documentation comment
```python
# Note: public_history accessed via config._current_public_history in instruction generation
```
- Not actual usage, just documentation
- Will need to update comment after refactoring

---

## Summary

**Total Production Uses**: 6 (4 writes, 2 reads)

**Affected Files**:
- `core/phase2_manager.py` - 4 assignments
- `experiment_agents/participant_agent.py` - 2 reads
- `core/services/voting_service.py` - 1 comment (update needed)

**Usage Pattern**: Side channel for passing discussion history from Phase2Manager to ParticipantAgent

**Refactoring Strategy**: Replace all 4 assignments with explicit `context.formatted_context_header` setting, update both reads to use the explicit field with fail-fast error handling.

---

**Next Steps**:
1. Create golden tests to lock in current behavior
2. Add `formatted_context_header` field to ParticipantContext
3. Update all 4 assignment locations in Phase2Manager
4. Update both read locations in ParticipantAgent
5. Remove the side channel attribute
6. Update the comment in VotingService
