# Phase 2 Group Discussion Architecture

This document explains the Phase 2 group discussion pipeline: how participant agents produce free‑form text, how those responses are validated, parsed, and converted into system state and decisions (consensus), and which modules and techniques (LLM prompts, regex, utility agents) perform each step.

Key code locations:
- Core manager: `core/phase2_manager.py`
- Utility parsing agent: `experiment_agents/utility_agent.py`
- Models and state: `models/experiment_types.py`, `models/response_types.py`
- Language prompts: `utils/language_manager.py`
- Logging: `utils/agent_centric_logger.py`
- Settings: `config/phase2_settings.py`


## High-Level Flow

- Phase entry and setup
  - `Phase2Manager.run_phase2(...)` orchestrates the entire phase.
  - Transfers Phase 1 memory into Phase 2 contexts with validation: `_initialize_phase2_contexts(...)` (sanitizes memory, enforces character limits).
  - Initializes `GroupDiscussionState` and per‑round flow control.

- Round loop
  - For each round (1..`config.phase2_rounds`):
    - Generate speaking order via `_generate_speaking_order(...)` (supports fixed/random/conversational strategies and the “finisher cannot start next round” rule).
    - For each participant in order:
      - Collect internal reasoning (optional) and public statement with retry/timeout: `_get_participant_statement_enhanced(...)` → `_get_participant_statement_with_retry(...)`.
      - Validate, quarantine if needed, and append to discussion history.
      - Log with `AgentCentricLogger` and update agent memory via `MemoryManager`.
      - Convert statement to system logic depending on mode:
        - Simple mode: detect per‑round preferences; if unanimous, declare consensus.
        - Complex mode: detect vote intention, then run a formal confirmation phase and secret ballot with parsing and consensus checks.

- After discussion
  - If consensus: apply chosen principle to distributions and compute payoffs.
  - If no consensus: apply random assignment.
  - Collect final rankings per participant.


## Components & Responsibilities

- `Phase2Manager` (core/phase2_manager.py)
  - Round orchestration, statements, consensus detection, voting, payoffs, final rankings.
  - Concurrency-safe consensus via `asyncio.Lock` and `_voting_in_progress` flag.
  - Validation stats, quarantine handling, and diagnostic logging.

- `UtilityAgent` (experiment_agents/utility_agent.py)
  - LLM‑first, regex‑assisted parsing for: principle choices, rankings, vote intention, agreement detection, preference detection, and constraint amounts.
  - Provides consensus checks for preferences and secret ballots.

- `LanguageManager` (utils/language_manager.py)
  - Centralized multilingual prompt templates for instructions, parsing, agreement, vote detection, constraints, etc.

- `GroupDiscussionState` (models/experiment_types.py)
  - Tracks `public_history`, `statements`, `vote_history`, consensus metadata, and safety fields (`valid_participants`, `vote_triggered`, `active_vote_in_progress`).

- `AgentCentricLogger` + `MemoryStateCapture` (utils/agent_centric_logger.py)
  - Records per‑round statements, inferred intentions, voting rounds, and outcomes.

- `Phase2Settings` (config/phase2_settings.py)
  - Tunables for validation, timeouts, retries, quarantine behavior, logging granularity, and constraint correction.


## Statement Pipeline (Free‑Form → Validated Text)

1) Prompt construction
- `_build_internal_reasoning_prompt(...)` (if reasoning enabled) and `_build_discussion_prompt(...)` supply round context, history, and participants; sourced from `LanguageManager`.

2) Collection with retry + timeout
- `_get_participant_statement_with_retry(...)` wraps `Runner.run(...)` in `asyncio.wait_for(...)` with exponential backoff.
- Validation `_validate_statement(...)`: non‑empty, trimmed, and language‑aware minimum length via `Phase2Settings.get_min_statement_length(language)`.

3) Quarantine and fallback
- On repeated failures or timeouts: either quarantine into a neutral public message or use a legacy explicit failure string (configurable via `Phase2Settings.quarantine_failed_responses`).
- Quarantined responses don’t contaminate `public_history` with failure text.

4) Logging + memory update
- `AgentCentricLogger.log_discussion_round(...)` stores internal reasoning, statement, inferred vote intention, and favored principle.
- Memory is updated with delta‑focused content via `MemoryManager.prompt_agent_for_memory_update(...)`.


## Converting Statements to System Logic

There are two distinct detection/consensus paths controlled by `config.voting_detection_mode`.

### A) Simple Mode: Preference Consensus

- Detection: `UtilityAgent.detect_preference_statement(statement)`
  - LLM‑first prompt detects definitive preferences only.
  - Strict letter‑reference rejection (regex): statements like “I prefer a/b/c/d” are immediately ignored.
  - Fallback full‑name patterns (regex) map phrases like “maximizing floor” or “floor constraint”.
  - Principle mapping: `_map_identifier_to_principle(...)` supports English/Chinese/Spanish canonical names.
  - Constraint extraction: `_extract_constraint_amount_flexible(...)` with patterns for `$14,000`, `14.000`, `14k`, `元`, `€`, etc. (handles thousands separators and international forms).

- Tracking + consensus: `_current_round_preferences` dictionary collects one `PrincipleChoice` per participant. When all have a preference, `UtilityAgent.check_preference_consensus_simple_mode(...)` groups by `(principle, constraint_amount)` and returns consensus only if all match exactly. Warnings are emitted for missing constraint amounts on constraint principles.

- Result: If unanimous, `GroupDiscussionState.public_history` is annotated with a consensus message and `GroupDiscussionResult` is finalized.


### B) Complex Mode: Formal Vote Flow

1) Vote intention detection
- `UtilityAgent.detect_vote_intention_enhanced(statement)`
  - Exclusion regexes avoid false positives (e.g., “should we vote later?”, “when should we vote?”).
  - LLM prompt then decides if the statement is a definitive proposal to vote now.
  - `MemoryStateCapture.extract_vote_intention(...)` uses the same utility for logging, with a simple fallback list if needed.

2) Confirmation phase (public)
- `_conduct_confirmation_phase(...)` prompts each participant to agree/disagree to proceed with voting.
- Agreement detection: `UtilityAgent.detect_agreement_multilingual(response)` combines:
  - Decisive agreement tokens (e.g., “LET’S VOTE”, “AGREED”),
  - Explicit refusal regexes (English and Chinese),
  - Domain exceptions (e.g., “NO CONSTRAINTS” must not flip agreement), and
  - LLM fallback when ambiguous.
- Any disagreement or fallback failure aborts the vote and returns to discussion.

3) Secret ballot (private)
- `_conduct_secret_ballot_phase(...)` asks each participant for a vote.
- Parsing ballots:
  - `UtilityAgent.parse_principle_choice_enhanced(...)` is LLM‑JSON first; on failure, falls back to parser agent or a permissive default.
  - Post‑parse correction heuristics: if the ballot text clearly references “floor constraint”/“range constraint” but the parsed principle mismatched, the manager corrects the principle choice to the matching constraint principle.
  - Missing constraints: if a constraint principle has no amount, `_handle_constraint_corrections(...)` re‑prompts the voter; amounts are extracted via `_extract_constraint_amount_flexible(...)`.
- Consensus check: `UtilityAgent.check_ballot_consensus(...)` groups by `(principle, constraint_amount)` and returns consensus only if all ballots match.
- Results are recorded as a `VoteResult` in `GroupDiscussionState.vote_history` and summarized in `public_history` (aggregate only; no individual votes).


## Extracting Principles from Free‑Form Statements

- `_extract_favored_principle(statement)` shortcuts exact Chinese phrases first (robust when LLMs vary), else calls `UtilityAgent.parse_principle_choice_enhanced(...)` and returns the canonical key.
- For preference detection and ballot parsing, `UtilityAgent` provides:
  - `_map_identifier_to_principle(...)`: normalized mapping for English, Chinese, and Spanish full names.
  - `_extract_principle_from_text(...)`: LLM‑assisted extraction if mapping fails.


## State, Concurrency, and Safety

- `GroupDiscussionState`
  - `valid_participants` enforces that only configured agent names can append to history (`add_statement(...)` checks).
  - `vote_triggered`, `active_vote_in_progress`, `last_vote_result`, `vote_history` provide explicit voting lifecycle state.

- Concurrency control
  - `_consensus_lock` ensures only one consensus path is active when statements are processed.
  - `_voting_in_progress` prevents overlapping vote rounds.

- Failure isolation
  - Quarantined responses prevent corrupted/empty outputs from entering the public transcript.
  - If a participant’s statement is a fallback/quarantine, consensus detection for that turn is skipped.


## Configuration & Prompts

- `Phase2Settings` highlights
  - `min_statement_length` / `min_statement_length_cjk`: language‑aware minimums.
  - `statement_timeout_seconds`, `confirmation_timeout_seconds`, `ballot_timeout_seconds`.
  - `max_statement_retries`, `retry_backoff_factor`.
  - `quarantine_failed_responses` to protect discussion integrity.
  - `constraint_correction_enabled`, `max_constraint_correction_attempts`.

- `LanguageManager` prompt families
  - Phase 2 instructions: `get_phase2_instructions(...)` → `prompts.phase2_discussion_prompt_simple|complex`.
  - Parser instructions and operations: `utility_parser_instructions`, `utility_parse_principle_choice`, `utility_parse_principle_ranking`, `utility_vote_detection`, `utility_agreement_detection_enhanced`, `utility_llm_parse_vote_intention`, `utility_llm_parse_constraint_amount`, `utility_secret_ballot_request`, `utility_voting_confirmation_request`, `utility_constraint_re_prompt`.
  - System reminders: voting reminder text localized per language.


## Logging & Memory Updates

- Logging
  - `AgentCentricLogger.start_vote_round(...)`, `log_discussion_round(...)`, `log_vote_response(...)`, `complete_vote_round(...)`, `log_confirmation_phase(...)` capture process and outcomes.
  - `MemoryStateCapture.extract_vote_intention(...)` records “Yes/No” vote‑intention assessments for telemetry.

- Memory
  - `utils.memory_content.build_phase2_delta(...)` builds delta‑focused summaries; `MemoryManager.prompt_agent_for_memory_update(...)` applies them using configured guidance style.


## Testing & Fixtures

- `tests/fixtures/phase2_parsing_fixtures.py` provides multilingual statements for:
  - Positive vs negative vote intention detection (English/Chinese/Spanish).
  - Ballot parsing with constraint amounts (including tricky formats: European separators, “k”, CJK numerals/units).
  - Vulnerability cases (e.g., duplicate constraint phrases, “no additional constraints” handling) to ensure robust parsing.


## Practical Notes & Extension Points

- Tuning strictness
  - Raise `min_statement_length*` to reduce low‑effort statements; increase timeouts/backoff for slower models.
  - Keep `quarantine_failed_responses` enabled in production‑like runs.

- Adding new languages
  - Extend `LanguageManager` prompts and `_map_identifier_to_principle(...)` mappings.
  - Add regex tokens for `detect_agreement_multilingual(...)` in the new language if needed.

- Custom consensus rules
  - Replace `check_preference_consensus_simple_mode(...)` or `check_ballot_consensus(...)` if you want majority/weighted rules; both currently require unanimity on `(principle, constraint_amount)`.

- Guardrails
  - The system heavily prefers LLM‑driven parsing with regex exclusions/normalizers as safety nets rather than pure regex extraction, reducing brittleness while keeping determinism on critical cues.

