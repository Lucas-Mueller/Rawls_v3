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

**Follow‑ups (Nice to Have)**

- Fix tool-state restoration in confirmation phase (index misalignment when skipping initiator).
- Agent-logger round number bug: use `context.round_number` instead of `current_round_number`.
- Consider returning `VoteResult` (not `bool`) from `conduct_voting_process()` and letting Phase2Manager print directly, removing side‑effect coupling.

