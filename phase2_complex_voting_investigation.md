Phase 2 Complex Voting – Investigation Report (experiment_results_20250826_202408.json)

Summary
- Issue: Reported that in complex mode a secret ballot occurred where one agent voted for b) (Maximizing the average) and the other for a) (Maximizing the floor), yet consensus was recorded on a).
- Finding: In this referenced run, a secret ballot did not complete. Consensus was reached via the preference-based path (not via ballots). The top-level log shows consensus on maximizing_floor while final_vote_results shows "No vote" for both agents.
- Root causes we identified:
  1) Misinterpretation of logs: "favored_principle" in per-round logs is a heuristic logger for statements, not the parsed preference used for consensus, nor a secret ballot.
  2) Real parser fragility: The complex-mode ballot parser can misclassify choices in other runs because regex patterns for principle extraction are too permissive and don’t handle bare letter votes like "a)"/"b". This could cause exactly the described failure when a secret ballot does occur.

What Actually Happened in This Run
- File: experiment_results_20250826_202408.json
  - general_information.consensus_reached: true
  - general_information.consensus_principle: "maximizing_floor"
  - general_information.final_vote_results: { "Gordon Gecko": "No vote", "Karl Marx": "No vote" }

Implication: No secret ballot was recorded. In complex mode, secret ballots are written to `discussion_state.vote_history` and mapped to names at export time. If no vote occurred, `final_vote_results` remains "No vote" per participant (see core/experiment_manager.py around lines 293–312). That’s what we see here.

Public conversation also contains:
- "[VOTING CONFIRMATION] ..." followed by "[VOTING RESULT] Confirmation failed - returning to discussion" early on. We do not see a later "[VOTING RESULT] Secret ballot consensus: ..." entry, which Phase2Manager would append if a secret ballot consensus occurred.

Therefore, the consensus on a) came from preference-based consensus, not from a secret ballot tally.

Where Complex Voting Lives (Code Map)
- Phase 2 loop and consensus paths: core/phase2_manager.py
  - Complex voting entry: `_handle_complex_voting_mode` -> confirmation -> secret ballot -> consensus (lines ~796–961)
  - Preference detection path (always runs; only returns early if voting consensus reached): collects per-round preferences and calls `UtilityAgent.check_preference_consensus` (lines ~415–474)
  - If complex voting finds consensus: it creates and stores a `VoteResult` in `discussion_state.vote_history` and appends "[VOTING RESULT] Secret ballot consensus: ..." to the public history.
- Vote parsing and consensus checks: experiment_agents/utility_agent.py
  - Secret ballot parsing: `parse_principle_choice_enhanced` + `_extract_principle_choice_direct`
  - Consensus on ballots: `check_ballot_consensus`
  - Preference detection (non-secret): `detect_preference_statement`
- Logging that may be confusing:
  - In Phase2Manager, `_extract_favored_principle` logs a simple keyword-based "favored_principle" value for the round; this is for logging only and is not used to determine consensus.

Why This Run Recorded Consensus on a)
1) No secret ballot occurred.
   - Evidence: final_vote_results shows "No vote" for both agents; no "Secret ballot consensus" entry in the public conversation log.
   - Thus, secret ballots could not have been the mechanism.

2) Preference-based consensus triggered.
   - After each participant speaks in a round, Phase2Manager detects a preference using `utility_agent.detect_preference_statement`, collects them in `discussion_state.current_round_preferences`, and if all participants have preferences for that round, it calls `check_preference_consensus`.
   - If both preferences match (same principle + same constraint amount for constraint principles), consensus is recorded immediately.
   - The file shows early `[PREFERENCE] Karl Marx: maximizing_floor`; Gordon Gecko’s logged `favored_principle` flips between A and B across rounds due to simple keyword matches. It is plausible that in the round where both preferences were parsed, both were detected as maximizing_floor, and preference-based consensus was reached.
   - Note: `favored_principle` is not the same as the parsed preference used for consensus. It’s a lightweight heuristic logger and can contradict the actual parsed preference.

Why The Reported Scenario Is Plausible Elsewhere (Real Parser Risks)
Even though this run didn’t have a secret ballot, the complex ballot parser has two issues that can cause the exact mis-recording described when a secret ballot does occur:

- Overly permissive/fragile regex patterns:
  - In `UtilityAgent._compile_principle_patterns`, the patterns for `maximizing_average` use global negative lookaheads like `(?!.*(?:constraint|floor|range|with))`. That means if the response text contains the word “floor” anywhere, the `maximizing_average` match is suppressed, even when the agent is clearly choosing average. Conversely, patterns for `maximizing_floor` match any occurrence of “floor” in the text, without robust anchoring to a declared choice phrase.
  - Example failure mode: "My ballot choice is b) maximizing the average income (not the floor)" can cause `maximizing_average` detection to fail (because "floor" is present somewhere in the string) and `maximizing_floor` to match (because "floor" appears), flipping a b) into a) in the parser.

- No direct support for bare letter responses:
  - `_extract_principle_choice_direct` requires phrases like “option a” or semantic content. It does not match bare letter ballots like "a)", "b", "(b)", which the prompt might still elicit from some agents. In such cases, the parser falls back to an LLM parse (`parse_principle_choice`), which is unanchored and can default incorrectly.

Together these issues can produce exactly the reported outcome in other runs that actually conduct secret ballots: one agent answers “b” or “b) … not the floor”, the other “a”, and both get parsed as a) → false consensus.

Evidence Pointers
- Complex ballot path and logging:
  - core/phase2_manager.py: `_conduct_secret_ballot_phase` creates a `VoteResult` and appends “[VOTING RESULT] Secret ballot consensus: …” if it reaches consensus. No such line appears in this file.
  - core/experiment_manager.py: builds `final_vote_results` by mapping the last `vote_history` entry to participant names. Here it emitted "No vote" for both, matching "no secret ballot".
- Preference consensus path:
  - core/phase2_manager.py: collects `current_round_preferences` and runs `utility_agent.check_preference_consensus`. That is the only plausible consensus source in this run.
- Heuristic favored principle (can be misleading):
  - core/phase2_manager.py: `_extract_favored_principle` uses substring checks (e.g., “average income”, “floor income”). This is only for logging; do not treat it as ballot or as the actual parsed preference.

Recommendations (Fixes and Hardening)
1) Anchor ballot parsing to a strict, structured format.
   - Update the secret ballot prompt to require the first line: `CHOICE: a|b|c|d` and (for c/d) a separate line `CONSTRAINT: $<amount>`.
   - Parse only those first lines for choice; treat the rest as reasoning only.

2) Add direct letter mapping in the parser.
   - In `_extract_principle_choice_direct`, first check for a leading letter token: `^[\s\[(]*([abcdABCD])[)\].]?\b` and map a→floor, b→average, c→average_floor_constraint, d→average_range_constraint. This prevents fallback to the LLM for bare letter ballots.

3) Remove global negative lookaheads and tighten context windows.
   - For `maximizing_average`/`maximizing_floor`, match within a narrow window after the choice phrase (e.g., the first sentence, or specifically the substring after “My ballot choice is …”).
   - Do not use `(?!.*floor)`-style global blocks; they misfire when agents mention other options in their reasoning.

4) Prefer “focus window” parsing for choices.
   - Reuse the ranking parser’s `_identify_principle_in_text` strategy: focus on the first sentence or first ~150–200 chars after the explicit “choice” label.

5) Clarify and separate logging signals.
   - Keep `favored_principle` as an informational tag, but add a separate field (e.g., `parsed_preference`) that logs the actual PrincipleChoice used for preference-based consensus. This will reduce confusion when inspecting logs.

6) Optional: Validate secret ballot consensus with a lightweight cross-check.
   - If both the public conversation and the ballots indicate contradictory directions (e.g., one agent’s recent parsed preference conflicts), emit a warning and store it in the report (already partially supported via `validate_consensus_against_discussion`).

Closing Notes
- The referenced run did not reach consensus via secret ballot; the consensus was derived from preference detection after discussion. However, the ballot parser patterns are indeed vulnerable to the scenario described. Implementing the above fixes will:
  - Make secret ballot parsing robust to letter-only answers.
  - Prevent global keyword collisions from flipping b→a in presence of the word “floor”.
  - Make logs less ambiguous by separating heuristic “favored” tags from the actual parsed signals used for consensus.

