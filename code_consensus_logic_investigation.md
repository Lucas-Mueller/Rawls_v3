**Consensus Logic Investigation Report**

- Author: Codex CLI Agent
- Date: 2025-09-04
- Scope: Phase 2 consensus detection, voting flow, and terminal reporting

**Summary**

- The consensus pipeline is implemented across `core/phase2_manager.py`, `core/services/voting_service.py`, and `core/two_stage_voting_manager.py`.
- I found a critical failure mode that can make the system reach consensus internally but fail to recognize or print it in the terminal: unhandled translation lookups in `VotingService.conduct_secret_ballot()` can throw before consensus flags are set, short-circuiting the success path and causing the Phase 2 loop to log a generic voting error and continue discussion.
- Additional bugs and fragilities exist in confirmation tooling state restoration, analytics logging, and the coupling between terminal output and an internal `_consensus_result` side‑effect.

**How Consensus Is Supposed To Work**

- End-of-round, Phase2Manager prompts each participant: `Phase2Manager._attempt_end_of_round_voting()` → `VotingService.prompt_for_vote_initiation()`.
- If any participant wants to vote, `VotingService.conduct_voting_process()` runs:
  - Public confirmation phase: `VotingService.conduct_confirmation_phase()` must get agreement (1/0) from all participants.
  - Secret ballot: `VotingService.conduct_secret_ballot()` delegates to `TwoStageVotingManager.conduct_full_voting_process()` which returns a `VoteResult` with `consensus_reached` and `agreed_principle`.
- On success, `VotingService.conduct_secret_ballot()` adds a consensus message to `discussion_state.public_history`, sets internal flags on `discussion_state` (`_consensus_reached` and `_consensus_result`), and appends the `VoteResult` to `vote_history`.
- Phase2Manager then prints terminal feedback via `process_logger.phase2_voting_result(...)` using values read from `discussion_state._consensus_result` and exits Phase 2 with a `GroupDiscussionResult`.

**Key Code Locations**

- `core/phase2_manager.py`
  - End-of-round voting trigger and terminal output: `_attempt_end_of_round_voting()` and `_run_group_discussion()`
- `core/services/voting_service.py`
  - Vote prompts and confirmation: `prompt_for_vote_initiation()`, `conduct_confirmation_phase()`
  - Secret ballot + consensus side-effects: `conduct_secret_ballot()`
- `core/two_stage_voting_manager.py`
  - Two-stage ballot validation + consensus check: `conduct_full_voting_process()` and `_create_vote_result()`

**Critical Bug: Unhandled Translation Lookups Can Suppress Consensus Recognition**

- In `VotingService.conduct_secret_ballot()` (core/services/voting_service.py), the consensus success path performs multiple translation lookups before setting `_consensus_reached/_consensus_result`:
  - `localized_principle_name = self.language_manager.get(f"common.principle_names.{principle_key}")`
  - `consensus_msg = self.language_manager.get("voting_results.consensus_with_constraint" | "voting_results.consensus_reached", ...)`
- These are not wrapped in `try/except` and do not use the service’s safe `_get_localized_message()` helper.
- If any key is missing or the language manager raises (which is plausible; unit tests show multiple translation gaps), the exception escapes before consensus flags are set. Phase2Manager then catches the exception in `_attempt_end_of_round_voting()` and logs a generic "Error during voting process". The terminal thus never prints the "🎉 Consensus Reached!" line despite actual consensus in `VoteResult`.

Why this matches the observed symptom:
- You reported “agents reached consensus but the system failed to recognize it at least in the terminal output.” This exact control flow can occur when translations for consensus strings are missing or the `LanguageManager` throws. The consensus print depends on `discussion_state._consensus_result` being set; when a translation exception aborts that block, `_consensus_result` remains unset and the logger has nothing to print.

Concrete example paths that can raise before flags are set:
- Missing `common.principle_names.{slug}` key.
- Missing `voting_results.consensus_reached` or `voting_results.consensus_with_constraint` key.
- Any internal error in `LanguageManager.get()` for these keys.

Recommended fix (targeted / low-risk):
- In `conduct_secret_ballot()`:
  - Use `_get_localized_message()` for all translation reads in the consensus branch.
  - Or wrap the translation and history-append code in `try/except` so consensus flags are set regardless of translation failures.
  - Move the `_consensus_reached/_consensus_result` assignment before the translation reads, so side‑effects are not dependent on i18n success.

**Bug: Tooling State Restoration Mismatch in Confirmation Phase**

- In `VotingService.conduct_confirmation_phase()`:
  - The code appends original `allow_vote_tool` settings only for non‑initiators to `original_tool_settings`, then restores by index across all contexts.
  - This misaligns indices when the initiator is skipped, restoring the wrong values to the wrong participants.
  - Effect: tool availability may remain disabled/enabled incorrectly in later interactions.

Recommended fix:
- Track and restore per-context (e.g., dict keyed by `context.name` or store a parallel list of the same length, inserting a sentinel for initiator index).

**Bug: Analytics Logging Uses Nonexistent Context Field**

- In `VotingService.prompt_for_vote_initiation()`, the agent-logger call uses `context.current_round_number`, but `ParticipantContext` defines `round_number`.
- Effect: this block silently never runs due to `hasattr(context, 'current_round_number')` check.

Recommended fix:
- Replace with `round_number=context.round_number` and drop the `hasattr()` guard.

**Fragility: Terminal Output Coupled to `_consensus_result` Side-Effect**

- `Phase2Manager._attempt_end_of_round_voting()` prints via `process_logger.phase2_voting_result(...)` using `discussion_state._consensus_result` fields. If the side-effect in `VotingService` fails (as above), Phase2Manager cannot print even if `TwoStageVotingManager` found consensus.

Recommended hardening:
- Change `VotingService.conduct_voting_process()` to return the `VoteResult` (or `GroupDiscussionResult`) instead of a `bool`. Then have Phase2Manager both print and return based on that direct outcome, not on a side-effect set later.
- Alternatively, read `discussion_state.last_vote_result` for print fallback when `_consensus_result` isn’t set.

**Behavioral Quirk: Early Break After First Vote Attempt**

- In `_attempt_end_of_round_voting()`, once any participant attempts a vote (success or fail), the loop breaks. This can delay reaching consensus if a later participant in the same round would have proposed a successful vote.
- Not a correctness bug, but may reduce the chance of same‑round consensus realization.

Recommended tweak (optional):
- Consider allowing multiple vote attempts in a round up to a cap, or iterate through all who wanted to vote that round.

**Public History Integration**

- `conduct_secret_ballot()` appends to `discussion_state.vote_history` directly and adds custom consensus/no-consensus tags to `public_history`. It does not use `GroupDiscussionState.add_vote_result()` which includes a standardized "[VOTING RESULT]" entry.
- Not a bug, but if downstream tooling expects the standardized tag, consider calling `add_vote_result(vote_result, language_manager)` in addition to the custom tags.

**Two-Stage Consensus Check**

- `TwoStageVotingManager._create_vote_result()` groups votes by `(principle.value, constraint_amount)` and sets `consensus_reached = len(vote_groups) == 1`. This is correct for unanimity.
- The manager correctly converts integers to `PrincipleChoice` instances, so numeric equality is used for constraint values.

**Additional Observations (Non-blocking to consensus print but useful to fix)**

- Localization in consensus path should be resilient: prefer `_get_localized_message()` helper for all i18n reads in `VotingService`.
- `ProcessFlowLogger.phase2_voting_result(...)` prints a principle slug (e.g., `maximizing_average_floor_constraint`). Consider passing a localized principle display name for better UX.

**Reproduction Notes**

- Configure a language or translations where one of the following keys is missing or throws: `common.principle_names.{slug}`, `voting_results.consensus_reached`, `voting_results.consensus_with_constraint`.
- Run a scenario where `TwoStageVotingManager` yields consensus.
- Observe: the system logs an error during voting, no "🎉 Consensus Reached!" is printed, and Phase 2 continues (or reports no consensus), despite the internal vote outcome being unanimous.

**Concrete Fix Sketches**

1) Make consensus side-effects robust in `VotingService.conduct_secret_ballot()`:

- Move consensus flag assignment before any translation lookup:
  - Set `discussion_state._consensus_reached = True` and `_consensus_result = GroupDiscussionResult(...)` immediately after `vote_result.consensus_reached` is confirmed.
- Wrap localization/printing side-effects in try/except or replace with `_get_localized_message()` to prevent exceptions from aborting consensus flagging.

2) Correct tooling state restoration in confirmation phase:

- Store original `allow_vote_tool` in a mapping keyed by participant/context and restore using the same keys; do not rely on positional list alignment when skipping initiator.

3) Decouple terminal output from consensus side-effects:

- Return the `VoteResult` (or `GroupDiscussionResult`) from `VotingService.conduct_voting_process()` and use it directly in `Phase2Manager` when printing and returning results. Use `discussion_state.last_vote_result` as a fallback if needed.

4) Fix analytics logging round number field:

- Use `context.round_number` instead of `context.current_round_number`.

**Risk/Impact Assessment**

- The i18n exception hardening is the most critical; it directly addresses the observed symptom with minimal behavioral change.
- Confirmation tooling state fix prevents subtle, hard-to-debug behavior in subsequent interactions after a vote attempt.
- Returning a richer object from `conduct_voting_process()` is a cleaner API but more invasive; consider as a follow-up refactor if you want to fully remove the reliance on side-effects.

**Appendix: File References**

- `core/services/voting_service.py`
  - `conduct_secret_ballot()` — add try/except or use `_get_localized_message()` around translation reads; set consensus flags first.
  - `conduct_confirmation_phase()` — fix `original_tool_settings` index alignment; restore by name/index consistently.
  - `prompt_for_vote_initiation()` — fix agent logger call to use `context.round_number`.
- `core/phase2_manager.py`
  - `_attempt_end_of_round_voting()` — optional: allow more than one vote attempt per round or attempt all willing participants.
  - Use returned `VoteResult` to print, rather than relying solely on `_consensus_result`.
- `core/two_stage_voting_manager.py`
  - Consensus logic appears sound for unanimity.

**Closing**

- The primary root cause of “consensus reached but not recognized in terminal output” is unguarded translation lookups in the consensus success path, which can prevent consensus flags from being set. Hardening those reads and decoupling terminal prints from side-effects will eliminate the mismatch.

