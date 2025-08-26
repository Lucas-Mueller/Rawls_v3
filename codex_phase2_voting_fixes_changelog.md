Title: Phase 2 Voting Detection and Readiness Fixes (Codex Changelog)

Summary
- Fixes a unanimity misclassification that prevented voting when agents mentioned “no constraints” in their agreement replies.
- Adds public “[VOTE READINESS] … (Unanimous: …)” records to the discussion history.
- Marks vote proposals in the public history and on the last DiscussionStatement.
- Tightens the vote-agreement prompt to request bare Yes/No responses.
- Improves logging’s vote-intention heuristic to avoid conflating “no constraints” with refusal.

Motivation
- In experiment_results_20250826_100054.json, both agents repeatedly proposed voting on the same principle, but no vote was conducted and “No vote” was recorded for both. Root cause: the agreement detector treated “NO” in the domain phrase “no constraints” as disagreement, blocking unanimity.

Changes

1) Context-aware agreement detection
- File: experiment_agents/utility_agent.py
- Function: UtilityAgent.detect_agreement_multilingual
- What:
  - Adds decisive agreement tokens (YES/I AGREE/LET’S VOTE/etc.) that return True unless explicit refusal patterns are present.
  - Introduces refusal regexes (e.g., “NO.”, “NOT READY”, “NEED MORE”) with word boundaries.
  - Adds domain exceptions (e.g., “NO CONSTRAINTS”) that do not negate agreement.
  - If both agreement and ambiguous negation cues appear, defers to the LLM fallback instead of defaulting to disagreement.

2) Public readiness logging
- File: core/phase2_manager.py
- Function: _check_unanimous_vote_agreement
- What:
  - After analyzing all replies, appends a line to public_history: “[VOTE READINESS] Alice: YES, Bob: NO … (Unanimous: False)”.
  - Maintains existing debug logs; improves observability in exported public conversation.

3) Proposal marking in public history
- File: core/phase2_manager.py
- Location: After detecting vote proposal in _run_group_discussion
- What:
  - Sets DiscussionStatement.contains_vote_proposal = True on the last statement.
  - Appends “[VOTE PROPOSAL] Proposed by <AgentName>” to public_history.

4) Agreement prompt tightened
- File: translations/english_prompts.json
- Key: prompts.phase2_vote_agreement
- What:
  - Instructs agents to respond with only “Yes” or “No” and to avoid adding principle details (e.g., “no constraints”).

5) Logging heuristic improved (non-blocking)
- File: utils/agent_centric_logger.py
- Function: MemoryStateCapture.extract_vote_intention
- What:
  - Uses explicit voting phrases and excludes domain phrases like “no constraints”.
  - Note: Runtime gating already uses UtilityAgent; this change narrows the gap between logging and behavior.

Behavioral Impact
- Agreements that include “no constraints” will no longer be misclassified as disagreement.
- The public conversation will show readiness outcomes, helping diagnose any future detection issues.
- Vote proposals are explicitly visible in public history, aiding traceability.
- Agents are nudged to reply with bare Yes/No, reducing classifier ambiguity.

Risks and Mitigations
- Risk: Some borderline refusals may bypass rule-based checks. Mitigated by LLM fallback whenever mixed signals exist.
- Risk: Prompt change could affect multilingual phrasing. The detector still supports semantic fallback and non-English agreement tokens.
- Risk: Exposing readiness publicly could influence agent behavior. This matches the stated ideal process.

Suggested Follow-ups (optional)
- Use the Utility Agent’s detection results to populate memory deltas (vote_intention/is_vote_round) for richer internal traces.
- Consider adding a small retry/backoff for agreement detection to mitigate transient LLM variance.

Files Modified
- experiment_agents/utility_agent.py
- core/phase2_manager.py
- translations/english_prompts.json
- utils/agent_centric_logger.py

Authored by: Codex CLI
Date: 2025-08-26

