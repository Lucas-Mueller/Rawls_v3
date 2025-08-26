**Scope**
- Assess Phase 2 vote detection and retry behavior across statement collection, vote initiation, unanimous agreement, and ballot parsing.
- Key modules: `core/phase2_manager.py`, `experiment_agents/utility_agent.py`, `utils/language_manager.py`, `models/*`, `translations/english_prompts.json`.

**High-Level Flow**
- Discussion loop (per round):
  - Participant generates a public statement with validation + retry.
  - Utility agent detects vote intent in the statement.
  - If detected, collect unanimous agreement to start a vote.
  - If unanimous, conduct secret ballot, validate/repair votes, and check exact consensus.

**Vote Detection**
- Proposer detection:
  - Code: `Phase2Manager._run_group_discussion` → `UtilityAgent.detect_vote_intention_enhanced`.
  - Prompt: `prompts.utility_vote_detection_enhanced` (translations) focuses on intent, not exact wording, returns `VOTE_DETECTED` or `NO_VOTE`.
  - Behavior: If `VOTE_DETECTED`, manager proceeds to unanimity check.
- Unanimous agreement check:
  - Code: `Phase2Manager._check_unanimous_vote_agreement`.
  - Agents are prompted with `prompts.phase2_vote_agreement` (“YES/NO”), then analyzed by `UtilityAgent.detect_agreement_multilingual` with `prompts.utility_agreement_detection_enhanced` producing `AGREES`/`DISAGREES`.
  - Requires all participants to agree to initiate the vote.
- Notes:
  - There is an older prompt path `LanguageManager.get_vote_detection_prompt` using `prompts.utility_vote_detection`. Tests ensure it exists; the runtime path uses the enhanced variant.

**Ballot Collection and Parsing**
- Secret ballot:
  - Code: `Phase2Manager._get_participant_vote`.
  - Prompt: `prompts.phase2_secret_ballot_vote` (letters list), requires numeric constraint for (c)/(d).
  - Parsing: `UtilityAgent.parse_principle_choice_enhanced`:
    - Tries direct regex extraction first; falls back to agent-based parsing; on repeated failures, uses permissive fallback `_parse_with_fallback`.
    - Robust constraint extraction `_extract_constraint_amount_robust` handles formats like `$12,000`, `12k`, contextual phrases, and defaults for abstract terms.
  - Validation: `UtilityAgent.validate_constraint_specification` enforces positive constraint when needed; if invalid → `_re_prompt_for_valid_vote` to fix.
  - Consensus: `_check_exact_consensus` requires all votes to match exactly (principle and constraint amount). Vote counts logged; `VoteResult` recorded to discussion history.

**Statement Retry Mechanism (Phase 2)**
- Code: `Phase2Manager._get_participant_statement_with_retry` (used via `_get_participant_statement_enhanced`).
- Validation:
  - Rejects empty/whitespace and very short statements (`< 10` trimmed chars) with warnings.
  - Tracks validation stats: total requests, successes, failed validations, retry attempts, fallbacks.
- Retries:
  - Up to `max_retries=3` per statement. On retry, prompt is augmented with an explicit instruction: “previous response was empty or too short… provide a meaningful response.”
  - On success, returns statement and delta content for memory updates.
  - On final failure or exception, raises `AgentCommunicationError`; caller catches and substitutes a fallback statement like `"[Agent_X failed to provide a valid response after multiple attempts]"` and increments `fallback_statements`.

**Strengths**
- Intent-focused vote detection:
  - Enhanced detection prompt is generous and examples-driven; reduces false negatives for varied phrasing.
  - Agreement prompt explicitly excludes hesitant/conditional approvals via analysis prompt, reducing false positives.
- Defensive parsing pipeline for votes:
  - Multi-stage parsing with regex-first, agent fallback, and permissive fallback ensures high resilience to free-form responses.
  - Constraint extraction handles diverse formats and abstract phrasing; invalid or missing constraints are re-prompted.
- Statement robustness:
  - Clear, minimal validation and guided retries improve data quality and reduce empty/noise statements.
- Logging and observability:
  - Detailed debug logs for vote detection and vote validation; per-round logging via `AgentCentricLogger` and validation statistics.

**Gaps and Risks**
- No retry/backoff around vote-intent/agree detection:
  - `detect_vote_intention_enhanced` and `detect_agreement_multilingual` are single-shot LLM calls; transient misclassifications can block or prematurely delay votes. There’s no rule-based pre-filter or retry.
- Strict unanimity classification:
  - The agreement classifier treats any hesitation as `DISAGREES`. This is safe, but may over-block votes if language includes mild hedging (“Yes, seems fine”). Consider graded detection or dual-path detection (rules + LLM) to reduce false negatives.
- Short-statement rejection threshold:
  - The `>=10` char minimum might reject terse but adequate contributions (e.g., “Vote now.”). It’s usually fine, but consider lowering or making configurable.
- Fallback statements in discussion:
  - Using a meta fallback string as the public statement can degrade conversational flow and could bias subsequent agents. Optionally, skip adding fallback to public history or insert a neutral facilitator note instead.
- Error handler not leveraged:
  - `ExperimentErrorHandler` is instantiated but not used to govern Phase 2 retries/backoff/jitter; statement retries are manual, and detection operations lack retry policy alignment.
- Exact-match consensus only:
  - No tolerance band for numeric constraints; even minor formatting differences block consensus (by design). If intended, fine; if not, consider canonicalization for semantically equivalent constraints.

**Edge Cases Observed**
- Vote detection on implicit intent:
  - Phrases like “we can finalize” without “vote” may be correctly caught by the enhanced prompt, but without a backup rules engine, misclassifications remain possible.
- Multilingual agreement:
  - Agreement detection relies on a single LLM classification with a strict prompt. Tests add a pattern-based prototype (`test_vote_agreement.py`), but it’s not integrated into runtime.
- Constraint negativity/invalidity:
  - Robust extractor filters negatives and non-sensical amounts and triggers re-prompts; good coverage.

**Recommendations**
- Add hybrid detection for vote intent and agreement:
  - Implement lightweight, language-aware regex/pattern pre-checks (similar to `test_vote_agreement.py`) before invoking LLM analysis. If patterns yield a confident class, skip LLM; otherwise fall back to current LLM prompt. This will reduce latency and variance.
  - Add a 1–2 try retry with slight prompt jitter for `detect_vote_intention_enhanced`/`detect_agreement_multilingual` to mitigate transient failures.
- Parameterize statement validation:
  - Expose `min_statement_length` and `max_statement_retries` in config; record them in logs for reproducibility.
- Improve fallback handling:
  - Replace meta fallback statements with a neutral system note in `GroupDiscussionState.public_history` and suppress adding it as a participant line. Optionally, immediately re-ask the next participant or re-sequence the round.
- Canonicalize numeric constraints before consensus:
  - Normalize `$12k`, `$12,000`, and `12000` to integers and compare on the normalized value to avoid superficial mismatches. Current implementation likely already compares normalized ints, but ensure consistent formatting before logging and comparing.
- Surface detection results on `DiscussionStatement`:
  - When vote intent is detected, set `contains_vote_proposal=True` on the appended `DiscussionStatement` to aid auditing and metrics.
- Optional: leverage `ExperimentErrorHandler` for unified retry policy:
  - Wrap vote-intent and agreement detection calls with the handler so backoff/exponential behavior is consistent with the rest of the system.

**Key Code References**
- Manager:
  - `core/phase2_manager.py` → `_run_group_discussion`, `_get_participant_statement_with_retry`, `_check_unanimous_vote_agreement`, `_conduct_group_vote`, `_get_participant_vote`, `_re_prompt_for_valid_vote`, `_check_exact_consensus`.
- Utility agent:
  - `experiment_agents/utility_agent.py` → `detect_vote_intention_enhanced`, `detect_agreement_multilingual`, `parse_principle_choice_enhanced`, `_extract_constraint_amount_robust`, `validate_constraint_specification`, `re_prompt_for_constraint`.
- Prompts:
  - `translations/english_prompts.json` → `prompts.utility_vote_detection_enhanced`, `prompts.utility_vote_detection`, `prompts.phase2_vote_agreement`, `prompts.utility_agreement_detection_enhanced`, `prompts.phase2_secret_ballot_vote`, `prompts.phase2_discussion_prompt`.
- Models:
  - `models/principle_types.py` → `PrincipleChoice`, `VoteResult`, `JusticePrinciple`.
  - `models/experiment_types.py` → `GroupDiscussionState`, `DiscussionStatement`, `Phase2Results`.
- Tests (signals):
  - `tests/unit/test_vote_detection_fix.py` (prompt presence and format),
  - `tests/integration/test_concurrent_experiment_isolation.py` (mocks for statement retry and agreement),
  - `test_vote_agreement.py` (rule-based prototype for agreement detection).

**Conclusion**
- The Phase 2 vote detection pipeline is intent-focused and multilingual-aware with solid prompts and logging. Statement retries are explicit and pragmatic. Ballot parsing is notably robust, with good constraint handling and repair paths. The primary improvement opportunity is to add hybrid (rules + LLM) detection and minimal retries/backoff for detection steps, and to parameterize validation thresholds. These changes should reduce variance and improve reliability without large refactors.

