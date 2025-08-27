**Phase 2 Voting System: Current Behavior and Code Map**

- Scope: How voting and consensus work in Phase 2 for both complex and simple modes.
- Key files: `core/phase2_manager.py`, `experiment_agents/utility_agent.py`, `models/*`, `utils/agent_centric_logger.py`, `config/models.py`.

**Overview**

- **Two modes**: Controlled by `config.models.ExperimentConfiguration.voting_detection_mode` (`"simple"` or `"complex"`). See `config/models.py` lines around the `voting_detection_mode` field and its validator.
- **Discussion loop**: `Phase2Manager._run_group_discussion(...)` iterates rounds and participants, collects statements, attempts consensus (via complex voting or simple preference consensus), and exits early on consensus; otherwise returns after `phase2_rounds` without consensus. See `core/phase2_manager.py` in `_run_group_discussion`.
- **State**: `models/experiment_types.GroupDiscussionState` tracks `round_number`, `statements`, `public_history`, `vote_history`, and voting flags. `GroupDiscussionResult` returns final consensus info plus `vote_history`.

**Round Flow**

- For each participant per round, `Phase2Manager`:
  - Builds a discussion prompt and fetches a public statement with retries and validation in `_get_participant_statement_with_retry` (empty/too-short statements are retried up to 3 times). See `core/phase2_manager.py`:
    - `_get_participant_statement_with_retry` (validates min content length, logs retries and fallbacks)
    - `_validate_statement` and `_log_validation_statistics`
  - Records the statement in `GroupDiscussionState.add_statement(...)` which also appends to `public_history`. See `models/experiment_types.py`.
  - Logs the round via `utils/agent_centric_logger.AgentCentricLogger.log_discussion_round(...)` (captures internal reasoning preview, vote intention flag, favored principle heuristic, pre-round memory and balance).
  - Updates the participant’s memory via `utils.memory_manager.MemoryManager.prompt_agent_for_memory_update(...)`.
  - If the statement was a fallback (agent failure), consensus processing is skipped for that turn.

**Complex Mode (formal voting with confirmation + secret ballots)**

- Trigger: `config.voting_detection_mode == "complex"` in `_run_group_discussion`.
- Step 1: Detect an explicit vote intent in a participant’s statement using `UtilityAgent.detect_vote_intention_enhanced(...)` which:
  - Uses strict regex on explicit phrases like “let’s vote”, “call for a vote”, excluding hedged/ambiguous mentions such as “should we vote?”; then
  - Falls back to an LLM signal with explicit markers (e.g., `VOTE_DETECTED`).
  - Code: `experiment_agents/utility_agent.py` `detect_vote_intention_enhanced`.
- Step 2: If detected, `Phase2Manager._handle_complex_voting_mode(...)` begins a vote round and logs it via `AgentCentricLogger.start_vote_round(...)` (vote type `formal_vote`, who triggered, and the trigger statement). See `core/phase2_manager.py` around `_handle_complex_voting_mode` and `utils/agent_centric_logger.py`.
- Step 3: Public confirmation phase: `_conduct_confirmation_phase(...)` prompts every participant with `prompts.utility_voting_confirmation_request` and evaluates agreement using `UtilityAgent.detect_agreement_multilingual(...)` which:
  - Rejects empty/one-word responses,
  - Checks decisive agreement tokens (e.g., “YES”, “LET’S VOTE”),
  - Guards against domain terms like “no constraints” being misread as refusal,
  - Falls back to LLM prompt `prompts.utility_agreement_detection_enhanced` when ambiguous.
  - Any refusal, parsing failure, or fallback response aborts the vote; results are appended to `public_history` as `[VOTING CONFIRMATION]` lines and a result line.
  - Code: `core/phase2_manager.py` `_conduct_confirmation_phase`; `experiment_agents/utility_agent.py` `detect_agreement_multilingual`.
- Step 4: Secret ballot phase: If confirmation succeeds, `_conduct_secret_ballot_phase(...)` prompts all participants with `prompts.utility_secret_ballot_request`, parses each ballot using `UtilityAgent.parse_principle_choice_enhanced(...)` and logs individual parsing success or failure via `AgentCentricLogger.log_vote_response(...)`.
  - On any parsing failure, the vote aborts and the discussion resumes.
  - Code: `core/phase2_manager.py` `_conduct_secret_ballot_phase`; `experiment_agents/utility_agent.py` `parse_principle_choice_enhanced`.
- Step 5: Consensus check: `UtilityAgent.check_ballot_consensus(ballots)` groups ballots by `(principle, constraint_amount)`.
  - Consensus requires all ballots in a single group.
  - Warnings are emitted for missing constraint amounts on constraint principles.
  - A not-yet-implemented correction loop `_handle_constraint_corrections(...)` is stubbed and currently returns `False` (adds a `[VOTING WARNING]` to `public_history`).
  - If consensus, `GroupDiscussionState.last_vote_result` and `vote_history` are updated with a `VoteResult` containing `votes`, `consensus_reached`, `agreed_principle`, `vote_counts`, `timestamp`.
  - `public_history` is updated with `[VOTING RESULT]` (aggregate only; individual ballots remain secret).
  - The vote round is completed in the logger via `AgentCentricLogger.complete_vote_round(...)` capturing consensus, agreed principle/constraint, vote counts, and any warnings.
  - Code: `experiment_agents/utility_agent.py` `check_ballot_consensus`; `core/phase2_manager.py` `_conduct_secret_ballot_phase`, `_handle_constraint_corrections`.
- Early exit: If consensus is reached, `_run_group_discussion` returns a `GroupDiscussionResult` immediately with `discussion_state.vote_history` included.

**Simple Mode (preference-based consensus within a round)**

- Trigger: `config.voting_detection_mode == "simple"` in `_run_group_discussion`.
- For each statement, `UtilityAgent.detect_preference_statement(...)` attempts to parse a declared preference from the public message:
  - Regex on phrases like “my preference is …”, “I prefer …”, optionally with a floor/range constraint amount; otherwise LLM fallback via `prompts.utility_preference_detection`.
  - Returns a `PrincipleChoice` without requiring constraint validation.
  - Code: `experiment_agents/utility_agent.py` `detect_preference_statement`.
- The manager collects per-round preferences in `discussion_state.current_round_preferences` (created dynamically with `hasattr`/assignment; note this field is not part of the `GroupDiscussionState` model). When all participants have expressed a preference in that round, the set is checked via `UtilityAgent.check_preference_consensus_simple_mode(...)`:
  - Same grouping rule as ballots: all must match `(principle, constraint_amount)`.
  - Emits warnings for missing constraint amounts on constraint principles.
  - If all match, an immediate consensus result is returned with a `[CONSENSUS] Preference-based consensus reached: …` line appended to `public_history`.
  - If not, the temporary preferences dict is cleared for the next round.
  - Code: `core/phase2_manager.py` in the `"simple"` branch of `_run_group_discussion`; `experiment_agents/utility_agent.py` `check_preference_consensus_simple_mode`.

**Data Structures and Logging**

- `models/principle_types.PrincipleChoice`: holds `principle`, `constraint_amount` (optional), `certainty`, `reasoning`. `validate_for_voting()` checks that constraint principles carry a positive amount.
- `models/principle_types.VoteResult`: `votes: List[PrincipleChoice]`, `consensus_reached`, `agreed_principle`, `vote_counts`, `timestamp`.
- `models/experiment_types.GroupDiscussionState`:
  - `statements` and `public_history` are the public log; statements are appended verbatim by `add_statement(...)`.
  - `vote_history: List[VoteResult]` accumulates ballot rounds; `last_vote_result` holds the most recent.
  - `active_vote_in_progress` prevents overlapping votes.
- `utils/agent_centric_logger.AgentCentricLogger`:
  - `initialize_voting_history(mode)`, `start_vote_round(...)`, `log_vote_response(...)`, `log_confirmation_phase(...)`, `complete_vote_round(...)` build a structured `VotingHistoryLog` with per-round details, parsing success flags, timestamps, and counts.
  - Discussion rounds are logged via `log_discussion_round(...)`, including a coarse “initiate_vote” flag derived by `MemoryStateCapture.extract_vote_intention(...)` and a heuristic “favored_principle”.
- Final vote mapping for audit: In `core/experiment_manager.py` `_set_general_logging_info`, if `vote_history` exists, the manager maps votes from the last `VoteResult.votes` list to participant names by index order to populate `final_vote_results` and `vote_timestamps`. This preserves anonymity during voting but records an audit mapping post hoc. See the loop over `last_vote.votes` and the subsequent `agent_logger.update_agent_votes(...)` call.

**Prompts and Internationalization**

- All user-facing prompts are pulled from `utils/language_manager.LanguageManager` using keys:
  - Discussion prompts: `prompts.phase2_discussion_prompt_complex` and `prompts.phase2_discussion_prompt_simple` used by `_build_discussion_prompt(...)`.
  - Vote intent: `prompts.utility_vote_detection_enhanced` (LLM fallback path).
  - Voting confirmation: `prompts.utility_voting_confirmation_request`.
  - Secret ballot: `prompts.utility_secret_ballot_request`.
  - Preference detection: `prompts.utility_preference_detection`.
  - Agreement disambiguation: `prompts.utility_agreement_detection_enhanced`.

**Edge Cases and Safeguards**

- Empty/too-short statements are retried; repeated failures produce a visible fallback statement like `[NAME failed to provide a valid response...]` and skip consensus processing for that turn.
- Complex mode confirmation treats empty or one-word responses as disagreement and aborts the vote.
- Any ballot parsing failure aborts the vote attempt and returns to discussion.
- Constraint correction loop is stubbed and currently does not attempt re-prompting; missing constraint amounts on constraint principles generate warnings but prevent consensus unless all participants voted for a non-constraint principle or consistently provided a valid amount.

**Speaking Order and Rounds**

- Speaking order is determined by `_generate_speaking_order(...)` based on `ExperimentConfiguration.speaking_order_strategy` (`"random"`, `"fixed"`, `"conversational"` placeholder), with a guard to avoid having the last round’s finisher start the next. See `core/phase2_manager.py`.
- The loop runs up to `phase2_rounds` (configurable). If no consensus occurs, `GroupDiscussionResult` returns `consensus_reached=False` and the experiment proceeds to payoffs with random assignment.

**Where to Look in Code**

- Core manager: `core/phase2_manager.py`
  - `_run_group_discussion` — main loop and mode branching
  - `_get_participant_statement_with_retry`, `_validate_statement` — statement collection/validation
  - `_handle_complex_voting_mode`, `_conduct_confirmation_phase`, `_conduct_secret_ballot_phase` — complex voting
  - `_calculate_vote_counts`, `_handle_constraint_corrections` — vote tally and stubbed corrections
  - `_extract_favored_principle`, `_build_discussion_prompt` — helpers
- Utility agent: `experiment_agents/utility_agent.py`
  - `detect_vote_intention_enhanced` — explicit vote intent detection
  - `detect_agreement_multilingual` — robust agreement parsing
  - `parse_principle_choice_enhanced` — ballot parsing with pattern + LLM fallback
  - `detect_preference_statement`, `check_preference_consensus_simple_mode` — simple mode consensus
  - `check_ballot_consensus` — consensus grouping for ballots
- Models: `models/experiment_types.py`, `models/principle_types.py`
  - `GroupDiscussionState`, `GroupDiscussionResult`, `VoteResult`, `PrincipleChoice`
- Logging: `utils/agent_centric_logger.py`
  - `initialize_voting_history`, `start_vote_round`, `log_vote_response`, `complete_vote_round`, `log_discussion_round`
- Config: `config/models.py`
  - `voting_detection_mode`, `phase2_rounds`, `speaking_order_strategy`

**Current Limitations / Notes**

- `GroupDiscussionState` does not declare `current_round_preferences`, but simple mode uses a dynamically attached dict when collecting preferences; this works but is not typed at the model level.
- Constraint correction for ballots is not implemented; ballots missing amounts for constraint principles currently prevent consensus.
- Ballots are secret during collection and public history only shows aggregates; the audit mapping to agents happens afterward by index order in `experiment_manager`.

