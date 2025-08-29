# Phase 2 Parsing Logic — Deep Review

This report provides a detailed review of Phase 2 parsing: how statements are validated; how preferences, votes, ballots, and final rankings are parsed; multilingual handling; fallbacks and safety nets; and risks with recommendations. Sources reviewed include:

- core/phase2_manager.py (primary orchestration and control flow)
- experiment_agents/utility_agent.py (parsing utilities and LLM fallbacks)
- utils/agent_centric_logger.py (agent-centric logging and vote-intent indicator)
- models/principle_types.py, models/experiment_types.py (typed models)
- tests/integration/* (selected coverage of parsing behavior)

## High-Level Flow
- Statement intake: Each round, participants produce a public statement; validation/reties run before it enters the discussion history.
- Simple mode (preference consensus): Extract explicit preferences per round; if all agree, record consensus without voting.
- Complex mode (formal voting): Detect vote intent; run a confirmation phase; then conduct a secret ballot and assess consensus.
- Post-discussion: Apply the agreed principle to assign payoffs and collect final principle rankings.

## Statement Intake & Validation
- Function: Phase2Manager._get_participant_statement_with_retry()
  - Calls Runner.run(...) with a per-statement timeout (Phase2Settings.statement_timeout_seconds).
  - Retries with exponential backoff (Phase2Settings.retry_backoff_factor) up to Phase2Settings.max_statement_retries.
  - On each attempt, validates via Phase2Manager._validate_statement(): non-empty, language-aware min length (Phase2Settings.get_min_statement_length(lang)), strips control chars; logs warnings with previews.
  - On final failure: either quarantines (neutral, localized message injected; increments quarantined_responses) if settings.quarantine_failed_responses, or returns a legacy failure marker string.
  - Quarantined statements are excluded from public reasoning content while still updating validation stats and logs.

## Simple Mode: Preference Detection & Consensus
- Round-local tracking: self._current_round_preferences is reset at the start of each round; preferences are collected only for that round.
- Detection: UtilityAgent.detect_preference_statement(statement)
  - Regex for patterns like “my preference is …”, “I prefer/choose/support …”, allowing legacy letter IDs (A–D), “principle c”, and long-form names; optional inline constraint extraction (e.g., “$13,000”).
  - Maps to JusticePrinciple via _extract_principle_from_text(), which first tries _map_identifier_to_principle(...) then an LLM parse (parse_principle_choice_llm) for harder cases.
  - Fallback: LLM prompt (“prompts.utility_preference_detection”) that emits “PREFERENCE_DETECTED: ...”, then parse back through the same mapping.
- Consensus: UtilityAgent.check_preference_consensus_simple_mode(preferences)
  - Groups by (principle, constraint_amount) and requires a single unanimous group. Warns on missing constraints for C/D.
  - On success: Immediately records GroupDiscussionResult with consensus=true, agreed_principle=PrincipleChoice(...); marks vote_triggered to suppress reminders; appends a concise consensus message to public history.

## Complex Mode: Vote Detection → Confirmation → Secret Ballot
1) Vote intent detection
   - Function: UtilityAgent.detect_vote_intention_enhanced(statement)
     - Exclusion patterns first (e.g., “should we vote?”, “not yet”, “need more discussion”), returning None.
     - Positive patterns for explicit English/Chinese phrases (“let’s vote”, “我提议投票”) and natural decision language.
     - LLM fallback via “prompts.utility_vote_detection_enhanced” requiring explicit tokens like “VOTE_DETECTED”. Returns the original statement if intent detected, else None.
   - Integration: Phase2Manager._handle_complex_voting_mode(...)
     - Uses a consensus lock and an internal _voting_in_progress flag to avoid race conditions; sets discussion_state.vote_triggered (for reminders) and active_vote_in_progress.

2) Confirmation phase (public)
   - Function: Phase2Manager._conduct_confirmation_phase(...)
     - Prompts all participants to confirm proceeding with a vote (“prompts.utility_voting_confirmation_request”).
     - Agreement check via UtilityAgent.detect_agreement_multilingual():
       - Decisive agreement tokens → True (unless explicit refusal terms are present).
       - “NO” in domain phrases like “NO CONSTRAINTS” is not treated as refusal (domain exceptions).
       - Ambiguous cases defer to an LLM prompt (“prompts.utility_agreement_detection_enhanced”).
     - Any fallback/timeout or explicit refusal causes confirmation to fail; logs results and updates memory per-agent.

3) Secret ballot phase (private)
   - Function: Phase2Manager._conduct_secret_ballot_phase(...)
     - Prompts each participant (“prompts.utility_secret_ballot_request”) and parses with UtilityAgent.parse_principle_choice_enhanced(). Timeouts are logged; failures short-circuit the round.
     - Post-parse correction: If raw ballot text contains clear cues (“principle c”, “floor constraint” or “principle d”, “range constraint”) but the parsed principle differs, a corrective override maps to the expected JusticePrinciple (C or D). This guards against occasional LLM drift.
     - Consensus assessment: UtilityAgent.check_ballot_consensus(ballots) operates identically to simple mode grouping, but on private ballots.
     - Constraint correction: Phase2Manager._handle_constraint_corrections(...) is currently a stub that adds a public warning and returns False (no remediation attempt yet).
     - Disagreement messaging: _analyze_ballot_disagreement(...) distinguishes principle-only disagreement, constraint-only disagreement (all picked the same principle but different amounts), and mixed cases; emits localized feedback to public history.

## Parsing Utilities: Core Behaviors
- Principle choice (UtilityAgent.parse_principle_choice_enhanced)
  - Primary path: parse_principle_choice_llm → expects JSON embedded in free-form LLM output and extracts {principle, constraint_amount, certainty, reasoning} via _parse_llm_principle_response(...).
    - Canonicalization: maps letters (a–d), English/Chinese/Spanish names to canonical values; corrects obvious principle/constraint mismatches (e.g., JSON says maximizing_average but text mentions “floor constraint” → coerces to floor constraint variant).
    - Constraint amount: accepts any positive number; if missing for C/D, tries flexible extraction via _extract_constraint_amount_flexible(...) from the LLM output text.
  - Fallbacks: on failures, uses classic parse_principle_choice (LanguageManager-backed, structured ParsedResponse) or an ultimate permissive fallback (UNSURE, maximizing_average).
  - Validation helper: validate_constraint_specification(...) checks for required amounts for C/D and logs warnings.

- Principle ranking (UtilityAgent.parse_principle_ranking_enhanced)
  - First attempts a numbered-list regex (e.g., “1. … 2. …”) and identifies the principle in each line via _identify_principle_in_text(...), which itself calls parse_principle_choice_llm with focused text.
  - Fallback: parse_principle_ranking (LanguageManager-backed ParsedResponse via Runner) when the direct path fails.
  - Completeness: models.PrincipleRanking validator enforces all four principles are present and each rank 1–4 is used exactly once.

- Amount extraction (two paths)
  - _extract_constraint_amount_flexible(statement): regex-based patterns supporting “$14,000”, “14.000”, “14k”, “14 thousand”, and plain numbers (excluding percentages), with normalization and k/thousand multiplication.
  - parse_constraint_amount_llm(response, principle): LLM-guided recovery via a prompt (“prompts.utility_llm_parse_constraint_amount”) that emits “CONSTRAINT_AMOUNT: …”.

## Multilingual Handling
- Direct Chinese mappings: Phase2Manager._extract_favored_principle checks known Chinese phrases first for favored-principle logging, then falls back to UtilityAgent parsing.
- Vote detection: UtilityAgent.detect_vote_intention_enhanced includes explicit Chinese phrases and natural decision language.
- Canonicalization: _map_identifier_to_principle includes English, Chinese, and Spanish names; letter identifiers retained for backward compatibility.
- LanguageManager centralizes all prompts; however, Phase2Manager._get_voting_reminder_message uses language_manager.current_language (string) instead of ExperimentConfiguration.language, which can diverge.

## Logging & Telemetry Integration
- Agent-centric logs (utils/agent_centric_logger.py)
  - log_discussion_round records internal_reasoning, public message, a simple Yes/No initiate_vote signal (via MemoryStateCapture.extract_vote_intention), and favored_principle string.
  - Voting lifecycle: initialize_voting_history, start_vote_round, complete_vote_round, plus confirmation-phase and per-vote response logs.
- Validation stats: Phase2Manager tracks statement validation counts, retries, fallbacks, quarantined responses and reports aggregated stats.

## Edge Cases & Protections
- Concurrency/races: _consensus_lock and internal flags (_voting_in_progress, discussion_state.active_vote_in_progress, and private _consensus_reached/_consensus_result) prevent double-voting and post-consensus churn.
- Quarantine: Prevents failed agent outputs from polluting the public discussion; replaces with localized neutral messages while tracking counts.
- Explicit ballot correction: Detects mismatches between raw ballot cues (C/D) and parsed principles and corrects them with warnings.
- Simple-mode isolation: Preference consensus logic is isolated to simple mode; ballot consensus is used for complex mode.

## Risks & Improvement Opportunities
- JSON extraction fragility: parse_principle_choice_llm relies on scraping JSON from free-form LLM output. Non-JSON preambles or code blocks can break parsing despite good content.
  - Recommendation: When supported, use function-calling / AgentOutputSchema for strict structuring; otherwise wrap JSON in explicit start/end sentinels and validate against a schema before json.loads.
- Constraint remediation missing: _handle_constraint_corrections is a stub. When a user clearly chose a constraint principle but omitted the number, the system cannot converge.
  - Recommendation: Add an immediate, localized re-prompt per voter via UtilityAgent.re_prompt_for_constraint and retry consensus once before failing.
- Canonicalization duplication: The mapping between short/long names across languages exists in multiple places (_parse_llm_principle_response and _map_identifier_to_principle).
  - Recommendation: Centralize canonicalization maps/constants in one place to reduce drift.
- Language source inconsistency: _get_voting_reminder_message consults language_manager.current_language (defaulting to 'mandarin') rather than config.language.
  - Recommendation: Standardize on ExperimentConfiguration.language and ensure LanguageManager is set accordingly at Phase 2 start.
- Hidden round state: _current_round_preferences is private state on the manager and resets every round.
  - Recommendation: Store on GroupDiscussionState (e.g., per-round structure) for traceability and easier auditing/testing.
- Magic prefixes: The quarantine prefix "__QUARANTINED__" is a literal string.
  - Recommendation: Make this a module-level constant to avoid accidental collisions and support future handling logic.

## Tests: Current Coverage & Gaps
- Present
  - tests/integration/test_alice_ballot_parsing_fix.py validates parse_principle_choice_enhanced across letter IDs, long-form names, and robust constraint extraction (e.g., “with a floor constraint of $13,000”).
  - tests/integration/test_multilingual_agent_parsing.py exercises multilingual choice parsing for selected statements.
  - tests/integration/test_complete_experiment_flow.py and tests/integration/test_logging_integration.py patch manager.utility_agent to simulate flows and ensure Phase 2 integrates with logging and result structures.
- Missing/Recommended
  - Unit tests for UtilityAgent.detect_vote_intention_enhanced exclusion vs positive patterns (including Chinese), and LLM fallback token handling.
  - Unit tests for Phase2Manager ballot post-parse corrections (C/D cue overrides) with explicit assertions on warnings and corrected principles.
  - Unit tests for UtilityAgent.detect_preference_statement on ambiguous phrasing, multilingual variants, and non-dollar amount formats (14k, 14.000, “14 thousand”).
  - Unit tests for UtilityAgent.parse_principle_ranking_enhanced ensuring numbered-list extraction + LLM fallback and exact 1–4 coverage.
  - Integration test for confirmation-phase edge cases (timeouts, quarantines) showing safe failure and return to discussion.

## Conclusion
Phase 2 parsing combines pragmatic regex heuristics with LLM-based semantic parsing and multilingual support. The control flow is carefully guarded (locks, flags), and safety nets include quarantine, explicit ballot corrections, and structured result models. The most impactful refinements are: hardening LLM JSON extraction, adding a constraint remediation loop, centralizing canonicalization maps, and unifying language selection. With these implemented and the proposed unit tests, Phase 2 parsing should be robust across languages and tricky edge cases, while remaining auditable and easy to reason about.
