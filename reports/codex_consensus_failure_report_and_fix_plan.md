**Consensus Failure: Report + Fix Plan**

**Summary**

- When agents unanimously agree, the terminal sometimes fails to show “Consensus Reached!”.
- Root cause: unhandled translation lookups in `VotingService.conduct_secret_ballot()` can raise before consensus flags are set, so Phase 2 never prints the consensus result and may continue discussion.

**Confirmation**

- Yes — this is the primary root cause for the issue you observed.

**Root Cause Details**

- Location: `core/services/voting_service.py` → `conduct_secret_ballot()`.
- After receiving a successful `VoteResult`, the code:
  - Resolves localized strings (e.g., `common.principle_names.{slug}`, `voting_results.consensus_*`).
  - Only then sets `discussion_state._consensus_reached/_consensus_result`.
- If any `language_manager.get(...)` raises (missing key, i18n error), execution aborts prior to setting consensus flags. Phase2Manager logs a generic voting error and continues.

**Impact**

- Consensus silently “disappears” from terminal output.
- Public history and logging may lack consensus lines even when unanimity was achieved.

**Fix Plan (Minimal-Risk)**

1) Harden consensus path in `conduct_secret_ballot()`
   - Set `discussion_state._consensus_reached = True` and `_consensus_result` immediately after `vote_result.consensus_reached` is confirmed.
   - Wrap all localization calls in try/except OR use the helper `_get_localized_message()` consistently to avoid exceptions.
   - If i18n fails, fall back to neutral English placeholders but do not block consensus side‑effects.

2) Defensive history update
   - After setting flags, append consensus info to `public_history` using safe getters; on failure, append a simple, non-localized summary.

3) Optional—but recommended—for robustness
   - In `Phase2Manager._attempt_end_of_round_voting()`, if `_consensus_result` is missing but `discussion_state.last_vote_result.consensus_reached` is True, print and return using `last_vote_result` as fallback.

**Acceptance Criteria**

- With translations intentionally missing, a unanimous vote:
  - Sets `discussion_state._consensus_reached = True` and `_consensus_result`.
  - Prints “Consensus Reached!” in terminal (possibly with fallback wording).
  - Adds a consensus line to public history.

**Risks & Mitigations**

- Low: i18n lookups become non-fatal; messages may degrade to fallback text. This is acceptable for resilience.
- Mitigate by collecting missing keys and logging a warning for later localization fixes.


**Implementation Review (Post‑Change)**

- VotingService.conduct_secret_ballot()
  - ✅ Consensus flags are now set immediately after detecting `vote_result.consensus_reached` (lines ~450–466).
  - ✅ All localization reads (principle name, consensus message, tags) are wrapped with try/except and fall back to plain English when needed (lines ~470–506, 511–524).
  - ✅ Public history update remains, now resilient to i18n failures.
  - ✅ `discussion_state.last_vote_result` is preserved and appended to `vote_history` before rendering.

- Phase2Manager._attempt_end_of_round_voting()
  - ✅ Adds defensive fallbacks: if `_consensus_result` is missing, it uses `last_vote_result` to print and return a `GroupDiscussionResult` (lines ~416–490).
  - ✅ Adds final defensive check for unreported consensus after the prompting loop.

- Remaining Gaps (not yet implemented)
  - ⚠️ Confirmation tool-state restore still uses positional list and can misalign when the initiator is skipped:
    - Code restores with `for i, context in enumerate(contexts): if i < len(original_tool_settings): context.allow_vote_tool = original_tool_settings[i]`.
    - Fix: store and restore by index or name, inserting a sentinel for the initiator so list positions align; or use a dict `{i: original_value}` and restore only for those indices.
  - ⚠️ Agent-logger round number still checks `current_round_number` (nonexistent):
    - Update to `round_number=context.round_number` and remove the `hasattr` guard.

**Updated Plan (Next Steps)**

1) Fix confirmation tool-state restoration (high confidence, low risk)
   - Store `original_tool_settings` as a mapping from context index (or name) to value.
   - Restore only for indices that were actually modified.

2) Correct agent-logger round number (very low risk)
   - In `prompt_for_vote_initiation()`, replace usage of `current_round_number` with `context.round_number`.

3) Optional refinement (defer unless needed)
   - Return `VoteResult` (or `GroupDiscussionResult`) from `conduct_voting_process()` and let Phase2Manager print directly, further decoupling from side-effects.

**Validation Checklist**

- Force missing translation keys and verify:
  - Terminal prints “Consensus Reached!” and shows the principle (fallback allowed).
  - `discussion_state._consensus_reached` and `_consensus_result` are set.
  - `public_history` contains a consensus line.
  - Phase2 completes with consensus in results JSON.
- Confirm that after a confirmation attempt, all contexts have `allow_vote_tool` restored to original values.
- Confirm vote initiation logging includes the correct `round_number`.

