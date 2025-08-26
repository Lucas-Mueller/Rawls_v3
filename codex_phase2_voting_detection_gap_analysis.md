# Phase 2 Voting Detection: Current vs. Ideal Flow

Scope
- Analyze current Phase 2 voting detection and session flow against the ideal process provided.
- Focus: detection of intent, unanimous agreement step, secret ballot handling, constraint validation/repair, and public transparency.

Ideal Process (Provided)
- Agent publicly states desire to vote.
- System dynamically (semantically) detects voting intention via Utility Agent (not brittle string matching).
- Voting session begins with two steps:
  1) All agents confirm willingness to vote; who agrees/disagrees is public information.
  2) If agreement, secret ballot is cast.
     - If unanimous agreement (on a principle with precise constraint), group discussion ends.
     - If an agent omits or violates constraint rules (range/floor), the system explains the error, agent updates memory, and is asked again to choose a principle.
  3) If disagreement in 2, discussion proceeds

Current Implementation (What the code does)
- Public statement collection
  - `Phase2Manager._get_participant_statement_with_retry(...)` validates and retries empty/short statements (min ~10 chars), then appends to `GroupDiscussionState.public_history`.
  - Internal reasoning optional per agent config; added to memory deltas.

- Voting intent detection
  - `Phase2Manager._run_group_discussion(...)` calls `UtilityAgent.detect_vote_intention_enhanced(statement)` on each public statement.
  - Implementation mixes explicit regex indicators (e.g., “let’s vote”, “time to vote”) with a semantic LLM fallback (`prompts.utility_vote_detection_enhanced`).
  - If detected, a voting session is initiated.

- Step 1: Unanimous agreement to vote
  - `_check_unanimous_vote_agreement` prompts all agents with `prompts.phase2_vote_agreement` (YES/NO intent) and classifies replies via `UtilityAgent.detect_agreement_multilingual` (regex pre-checks + LLM fallback using `prompts.utility_agreement_detection_enhanced`).
  - Returns a boolean for unanimity; agreement/disagreement decisions are NOT recorded to `public_history` beyond debug logs.

- Step 2: Secret ballot and consensus
  - `_conduct_group_vote` prompts each agent with `prompts.phase2_secret_ballot_vote` and parses using `UtilityAgent.parse_principle_choice_enhanced`:
    - Direct regex extraction → agent-based parsing → permissive fallback.
    - Robust constraint parsing (`_extract_constraint_amount_robust`) handles `$12,000`, `12k`, contextual phrases, and negation filtering.
  - If a constraint is missing/invalid, `_re_prompt_for_valid_vote` explains what’s wrong (via `UtilityAgent.re_prompt_for_constraint`), updates the agent’s memory with the re-prompt and response, and retries up to N times; final fallback applies a default constraint or safe default principle.
  - `_check_exact_consensus` requires exact match on principle AND constraint; if consensus reached, discussion exits early. Public history records a summary line via `GroupDiscussionState.add_vote_result`.

- Logging/telemetry
  - Per-round logging via `AgentCentricLogger.log_discussion_round`. Note: vote intention in logs uses a simple substring heuristic (`MemoryStateCapture.extract_vote_intention`), not the Utility Agent.
  - Final `ExperimentManager` builds `final_vote_results` mapping participants to votes (for reporting), while the in-discussion public history remains “secret ballot style”.

Side-by-Side Comparison vs. Ideal
- Semantics over strings (Intent detection)
  - Current: Hybrid approach (regex + LLM fallback). Better than pure string matching but still anchored on English-centric patterns and explicitness; code uses the “enhanced” prompt that only flags explicit proposals.
  - Ideal: Primarily semantic detection. Gap: heavy reliance on curated regex lists and an “EXPLICIT only” prompt may miss softer/implicit but clear intents.

- Session initiation structure
  - Current: On detection → unanimous agreement check → secret ballot → exact consensus check. This matches the ideal two-step structure.
  - Gap: “Who agrees/disagrees is public information” is not added to `public_history`; decisions are only logged in debug and not visible to participants.

- Secret ballot behavior
  - Current: Votes are collected privately; only a summary is appended to public history. This aligns with “secret ballot”.
  - Note: `ExperimentManager` correlates votes to participants for final reporting, but this is not surfaced to agents during discussion.

- Constraint error handling and memory update
  - Current: When constraint missing/invalid, the system explains the error, updates memory with the re-prompt/response, and re-asks. This aligns with the ideal.
  - Gap: After max retries, code forces a default constraint/principle; the ideal implies continued clarification and re-asking without silently substituting defaults. Silent fallbacks risk biasing outcomes.

- Transparency in state tracking
  - Current: `DiscussionStatement.contains_vote_proposal` always False; the system doesn’t mark which statement triggered a vote nor record proposer in the public history.
  - Ideal: Clear public trace of proposals and agreement status.

- Consistency in detection and logging
  - Current: Runtime voting-intent gating uses `UtilityAgent.detect_vote_intention_enhanced`, but logging uses `MemoryStateCapture.extract_vote_intention` (simple substring). This can produce misleading analytics versus the true gating behavior.
  - Ideal: Single source of truth for detection across gating, logging, and memory deltas.

Key Code References
- Manager: `core/phase2_manager.py`
  - Detection and gating: `_run_group_discussion`, `_check_unanimous_vote_agreement`, `_conduct_group_vote`.
  - Statement validation/retry: `_get_participant_statement_with_retry`.
  - Constraint repair: `_re_prompt_for_valid_vote`.
- Utility Agent: `experiment_agents/utility_agent.py`
  - Vote intent: `detect_vote_intention_enhanced`.
  - Agreement detection: `detect_agreement_multilingual`.
  - Vote parsing: `parse_principle_choice_enhanced`, `_extract_constraint_amount_robust`, `re_prompt_for_constraint`.
- Models/State: `models/experiment_types.py`, `models/principle_types.py`.
- Prompts: `translations/english_prompts.json`.
- Logging: `utils/agent_centric_logger.py` (`extract_vote_intention`).

Critical Gaps and Risks
- Public agreement transparency missing
  - Who agreed/disagreed in Step 1 is not added to `public_history` (contrary to the ideal). Participants lack visibility into readiness.

- Overly strict intent detection
  - The enhanced prompt discourages detection of non-explicit but semantically clear intents. Combined with narrow regex, this can miss genuine proposals.

- Divergent detection between control flow and analytics
  - Logging uses a naive substring method; potential false positives/negatives versus the actual Utility Agent detection.

- Silent defaults after failed constraint retries
  - Applying default constraints/principles can deviate from participant intent and the ideal’s “explain + ask again” loop. It should be an explicit, recorded fallback, or escalate gracefully.

- Missing proposer attribution in state
  - Neither `GroupDiscussionState` nor `public_history` marks who proposed the vote; `contains_vote_proposal` remains unused.

- Memory deltas omit vote-intention flags
  - `build_phase2_delta` supports `vote_intention` and `is_vote_round` but Phase 2 code does not populate them, losing valuable traceability.

Recommendations (Prioritized)
1) Record Step 1 outcomes publicly
   - Append a public summary after the agreement check, e.g.:
     - `[VOTE READINESS] Alice: YES, Bob: NO, Carol: YES (Unanimous: False)`
   - Persist in both `GroupDiscussionState.public_history` and memory deltas (`is_vote_round=False` for Step 1).

2) Mark proposals and proposers
   - When intent is detected for a statement, set `contains_vote_proposal=True` and append a line such as `[VOTE PROPOSAL] Proposed by Alice` to `public_history`.
   - Prefer `UtilityAgent.extract_vote_from_statement` to build a `VoteProposal` with clear attribution.

3) Unify detection across runtime and logging
   - Replace `MemoryStateCapture.extract_vote_intention` with the same Utility Agent pipeline used for gating. Store the boolean in memory deltas (`vote_intention`) and logs.

4) Make detection more semantic-first and resilient
   - Use the more generous `prompts.utility_vote_detection` as primary, with the “enhanced” explicit prompt as a secondary disambiguation step when needed.
   - Add a small retry/backoff or dual-path (rules + LLM) approach for both intent and agreement classification to mitigate transient LLM variance.

5) Avoid silent defaults for constraints
   - If retries exhaust, publicly record a facilitator note (e.g., `[VOTE REPAIR] Dana’s constraint remained invalid after retries; vote paused for clarification.`) and loop back to clarification instead of auto-defaulting.
   - If defaults are retained for robustness, surface them in `public_history` and participant memory with rationale.

6) Populate memory deltas for voting
   - When intent is detected, set `vote_intention=True` in `build_phase2_delta`.
   - For Step 1, set `is_vote_round=False` but include readiness outcomes.
   - For Step 2, set `is_vote_round=True` and include `consensus_reached`/`agreed_principle`.

7) Minor UX/config improvements
   - Parameterize `min_statement_length` and statement retry counts in config.
   - Lower the default minimum to avoid rejecting terse-but-sufficient statements like “Vote now.”

Outcome
- The current system broadly follows the ideal two-step session design and handles constraint errors well with memory updates. Key improvements are around public transparency for Step 1, stronger semantic detection (with less over-reliance on explicit phrases), unified detection in logs/state, and avoiding silent defaults on constraint failures. Implementing these will align Phase 2 more closely with the ideal flow and improve traceability and user trust.


---

# Deep-Dive Failure Analysis (experiment_results_20250826_100054.json)

Symptoms
- Consensus: false; Rounds conducted: 4; No votes recorded.
- Public conversation shows repeated, explicit vote proposals by both agents and alignment on the same principle:
  - “I propose we vote on maximizing the average income (no constraints).”
  - “I propose we vote on maximizing the average income now. … Let’s move forward …”
- Final vote results: { Alice: "No vote", James: "No vote" }.

Observed Behavior vs. Expected
- Expected: First explicit vote proposal should trigger Step 1 (unanimous agreement). Given both agents are repeatedly advocating to vote now on the same principle, the agreement step should succeed, leading to a secret ballot and quick consensus on maximizing average (no constraints).
- Observed: No `[VOTE RESULT]` entries in `public_conversation_phase_2`; `final_vote_results` shows "No vote" for both. The system never entered the secret ballot.

Root Cause 1: Agreement classifier false-negatives due to domain text “no constraints”
- Code path: `core/phase2_manager.py` → `_run_group_discussion` → on detection → `_check_unanimous_vote_agreement`.
- `_check_unanimous_vote_agreement` flow:
  - Prompts all agents with `prompts.phase2_vote_agreement` (ask: "Yes" or "No").
  - Parses replies via `UtilityAgent.detect_agreement_multilingual`.
    - Direct pattern check: if it sees any of these tokens in UPPERCASE (`YES`, `I AGREE`, `LET'S VOTE`, etc.), it further checks for negation words: `["BUT", "HOWEVER", "NOT", "NO", "EXCEPT", "THOUGH"]`.
    - If ANY negation token is present anywhere in the reply, it treats the agreement as negated and breaks out of the agreement scan.
    - Then it scans disagreement tokens: `["NO", "NOT", "NEED MORE", "NOT READY", ...]` and immediately returns False if found.
- In this experiment, agent replies commonly include the principle descriptor “(no constraints)”. That contains the token `NO`, which triggers the disagreement path even when the reply starts with “YES” or “I AGREE”.
- Result: Perfectly valid confirmations are misclassified as disagreement. Since unanimity is required, Step 1 repeatedly fails, so Step 2 (secret ballot) never runs. This exactly matches the JSON outcome: explicit proposals but “No vote”.

Why the bug trips here specifically
- The agents strongly prefer “maximizing average (no constraints)”. When asked “Do you agree to conduct a vote now?”, they often answer variants like “Yes, let’s vote on maximizing average (no constraints) now.”
- Uppercased text includes “NO CONSTRAINTS”, so the current direct-pattern agreement logic flags negation by seeing `NO` and then flags disagreement explicitly via the subsequent disagreement check, overriding the initial "YES".

Supporting Code References
- `experiment_agents/utility_agent.py` → `detect_agreement_multilingual`:
  - Agreement detection lists and the unconditional negation scan across the entire response.
  - Disagreement detection list includes `"NO"` without contextual filters.
- `core/phase2_manager.py` → `_check_unanimous_vote_agreement`:
  - Calls `detect_agreement_multilingual` for each response and requires `all(agrees)`.
- `translations/english_prompts.json` → `prompts.phase2_vote_agreement`:
  - Encourages “Yes”/“No” answers but agents frequently append principle wording containing “no constraints”.

Secondary Contributing Issues
- No public record of Step 1 outcomes: Because the agreement step is fully silent in public history, it’s harder to spot misclassifications in run-time artifacts.
- Divergent detection for logging: `utils/agent_centric_logger.MemoryStateCapture.extract_vote_intention` uses naive substring checks, hiding the mismatch with the Utility Agent’s actual gating logic.

Reproduction (Minimal)
- Prompt an agent with the agreement question and a content policy that typically appends principle details; a likely reply:
  - “Yes — let’s vote now on maximizing average (no constraints).”
- Current classifier path:
  - Detects `YES` (agreement), then sees `NO` in “NO CONSTRAINTS”, sets negation, and then matches `NO` in disagreement scan → returns False.

Fixes (Actionable)
1) Agreement classifier: context-aware negation
   - Only treat `NO` as negation when it is used as a standalone voting response, or with explicit refusal phrases.
   - Add explicit exceptions for domain phrases such as `NO CONSTRAINTS`.
   - Prefer word-boundary detection and context (e.g., `(\bNO\b)(?!\s+CONSTRAINTS?)`).
   - If both an agreement token and a suspicious “NO …” token exist, prefer LLM fallback rather than defaulting to disagreement.

2) Agreement classifier: make direct agreement decisive
   - If `YES`, `I AGREE`, or `LET’S VOTE` is present and there is no clear refusal phrase (e.g., "No, not ready", "No, need more discussion"), return True immediately.
   - Only rely on the LLM fallback or negation resolution for ambiguous cases (e.g., "Yes, but later").

3) Prompt hygiene for Step 1
   - Update `prompts.phase2_vote_agreement` to explicitly instruct: “Reply with just Yes or No (do not include principle details).” This reduces risk of embedding domain text like “no constraints” that confuses the rule-based path.

4) Add public transparency
   - After unanimity check, append a line to `public_history` like:
     - `[VOTE READINESS] Alice: YES, James: YES (Unanimous: True)` or `[VOTE READINESS] … (Unanimous: False)`.
   - This will highlight misclassifications in runs and facilitate debugging.

5) Unify detection across logging and runtime
   - Use the same Utility Agent pipeline for logging vote intent and agreement results; avoid mixing naive string checks.

Suggested Code Changes (Sketch)
- In `UtilityAgent.detect_agreement_multilingual`:
  - Replace current negation handling with token-aware logic:
    - Tokenize and search for `NO` only when followed by refusal indicators (`NO,`, `NO ` + verbs like `NEED`, `WANT`, `NOT`, `READY`).
    - Ignore `NO` when followed by domain nouns like `CONSTRAINTS`, `LIMITS`, `RANGE`, `FLOOR` within a window.
  - If both agreement and potential negation cues exist, defer to LLM fallback instead of returning False.
- In `Phase2Manager._check_unanimous_vote_agreement`:
  - Record per-agent readiness in `public_history` for traceability.

Validation After Fix
- Re-run a scenario mirroring `experiment_results_20250826_100054.json`:
  - Expect `[VOTE READINESS]` line showing unanimous agreement.
  - Secret ballot collected via `prompts.phase2_secret_ballot_vote`.
  - Consensus reached quickly on `maximizing_average` and discussion ends.
