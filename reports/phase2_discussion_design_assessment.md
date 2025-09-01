# Phase 2 Discussion Design Assessment: Does The System Counteract Consensus?

Author: Codex CLI Assistant
Date: 2025-09-01

## Executive Summary

Your hypothesis is well-founded: elements of the Phase 2 discussion and voting design can inadvertently counteract consensus, even when agents appear to converge during discussion. In particular, the transition from discussion to the two-stage voting sequence resets critical context and enforces strict, unanimous equality (principle AND exact constraint amount) without tolerance or priming to the negotiated value. This design likely explains the behavior seen in `experiment_results_20250901_152539.json`, where agents publicly converge on “maximizing average with a floor constraint” and even an amount ($25,000), yet fail to reach consensus twice during secret ballot.

Key contributing factors:

- Secret ballot requires strict unanimity on both principle and exact constraint amount with no tolerance or correction.
- Voting prompts are generic and do not prime agents to the negotiated candidate or amount.
- Confirmation and ballot stages include brittle numeric-only validations; any malformed or alternative-but-valid choice breaks unanimity.
- End-of-round “first-Yes wins” initiation can prematurely force a vote while momentum is still forming.
- i18n and public-history formatting inject English or mixed-language markers into contexts, risking subtle confusion.

Overall, this suggests the post-discussion voting orchestration, not genuine agent preferences, is a primary cause of observed non-consensus.

---

## Evidence From The Referenced Log

File: `experiment_results_20250901_152539.json`

Excerpts from `general_information.public_conversation_phase_2`:

- Early convergence on principle and constraint:
  - Alice: “I’m willing to accept maximizing the average income with a floor constraint, with a $25,000 floor… I’m ready to vote if you are.”
  - James: Agrees multiple times with the same principle and amount ($25,000).

- Twice, a vote is initiated and confirmed, yet secret ballot reports no consensus:
  - “[VOTING INITIATED] Alice has initiated formal voting.”
  - “[VOTING CONFIRMATION] Alice: Confirmed (initiated vote)”
  - “[VOTING CONFIRMATION] James: 1”
  - “[VOTING RESULT] All participants agreed - proceeding to secret ballot”
  - “[VOTING RESULT] No consensus - agents voted for different justice principles - discussion continues”

This pattern indicates that when agents cast ballots, at least one selected a different principle or a different constraint amount than the apparent negotiated $25,000.

---

## Design Walkthrough And Code References

### 1) Discussion Flow and Memory

- Public discussion prompting and logging:
  - `_build_discussion_prompt` generates a base prompt (complex voting mode) and optionally appends an English “YOUR INTERNAL REASONING” block before the public statement.
    - File: `core/phase2_manager.py:1496–1531`
    - Risk: The appended English section and dynamic group composition strings are not localized, potentially producing mixed-language prompts.

- Statement validation and quarantine:
  - `_get_participant_statement_with_retry` enforces minimum length, timeouts, and retries; failures can be quarantined and substituted with neutral text.
    - File: `core/phase2_manager.py:170–340` (notably 228–256)
    - Behavior: Quarantined responses skip consensus detection for that turn (line ~540+), which avoids contamination but can also reduce alignment momentum.

### 2) End-of-Round Vote Initiation

- Per-participant numeric prompt (1/0):
  - `_prompt_for_vote_initiation` asks each participant if they want to vote now.
    - File: `core/phase2_manager.py:870–941`
    - Behavior: On first “Yes”, the manager immediately initiates voting and breaks the loop (line ~634, ~682–694). Remaining participants are not polled that round, which can prematurely escalate to balloting.
    - Risk: Premature initiation may freeze negotiation before constraint alignment fully stabilizes.

### 3) Confirmation Phase

- Public confirmation with strict numeric validation:
  - `_conduct_confirmation_phase` auto-confirms the initiator and requires others to respond with “1”/“0”. Any malformed response fails confirmation.
    - File: `core/phase2_manager.py:1608–1718`
    - Pros: Clear, unambiguous flow.
    - Risk: Brittle handling of format or localization can cause spurious failures that erode momentum.

### 4) Secret Ballot: Two-Stage Voting

- Two-stage, numeric-only voting:
  - `TwoStageVotingManager.conduct_full_voting_process`:
    - Stage 1: Choose principle (1–4) with numeric-only validation.
    - Stage 2: If constraint principle (3 or 4), specify a dollar amount as a positive integer.
    - File: `core/two_stage_voting_manager.py:76–228` (setup) and `240–720` (stages)

- Consensus check requires exact identity across all ballots:
  - `_create_vote_result` groups votes by `(principle, constraint_amount)` and declares `consensus_reached` only if there is a single group (strict unanimity).
    - File: `core/two_stage_voting_manager.py:717–792`
    - Critical detail: No tolerance on constraint amounts, and no correction stage.

- Missing tolerance/correction despite settings:
  - `Phase2Settings` defines `constraint_tolerance` and a “constraint correction” feature, but TwoStageVotingManager ignores these.
    - File: `config/phase2_settings.py:58–86` (constraint tolerance), `88–112` (correction settings)
    - Impact: A minor divergence (e.g., 24000 vs 25000; or null vs 25000) will cause non-consensus, even after visible agreement.

- Generic prompts do not prime negotiated candidate:
  - Prompts retrieved via `language_manager` are generic (“Which of the four principles…”, “Respond with ONLY the number…”). They do not include the negotiated principle or the agreed $25,000.
    - Files: `translations/*_prompts.json` keys `two_stage_principle_selection` and `two_stage_amount_specification` (e.g., `translations/english_prompts.json:81–82, 109–111`)
    - Impact: Agents can revert to original preferences; nothing nudges them to vote the compromise.

### 5) i18n and Public History Artifacts

- Mixed-language system reminder inserted into public history:
  - In your log, `[系统提醒] Reminder: …` was injected mid-discussion.
  - The current implementation uses hard-coded English/Spanish/Mandarin messages for reminders rather than translation keys; the label/tag is also not localized.
    - File: `core/phase2_manager.py:1061–1079`
    - Impact: Mixed-language context can confuse models; at minimum it’s inconsistent with otherwise English conversations.

- English-only public-history tags:
  - “[VOTING INITIATED]”, “[VOTING CONFIRMATION]”, “[VOTING RESULT]”, “[VOTING ERROR]” are built as English templates.
    - File: `core/phase2_manager.py:1001, 1646, 1681, 1691, 1702, 1712, 1716, 1760, 1787, 1819`
    - File: `models/experiment_types.py:188–191` (“[VOTE RESULT] Vote conducted - Consensus: …”)
    - Impact: i18n mismatch and possible subtle model bias.

### 6) Reproducibility/Order Effects

- Speaking order uses NumPy RNG independent from `seed_manager`:
  - `_generate_speaking_order` does a `np.random.choice` without tying to `seed_manager`’s RNG.
    - File: `core/phase2_manager.py:760–792`
    - Impact: Subtle non-determinism in conversational momentum can flip near-consensus cases.

---

## Likely Root Causes Of “Converged Then No Consensus”

1) Strict unanimity on principle and exact amount with no tolerance or reconciliation
   - Code: `core/two_stage_voting_manager.py:_create_vote_result` (717–792)
   - Design ignores `Phase2Settings.constraint_tolerance` and “constraint correction” settings.
   - Even a minor mismatch (e.g., $25,000 vs $20,000; null vs $25,000; or mis-typed amount) breaks consensus.

2) Generic, decontextualized ballot prompts
   - Code: `core/two_stage_voting_manager.py` two-stage prompts via `language_manager` are generic.
   - No priming/anchoring to “the principle/amount just discussed”.
   - Agents easily revert to first-choice principle, undermining negotiated compromise.

3) Premature vote initiation on first “Yes”
   - Code: `core/phase2_manager.py:_prompt_for_vote_initiation` (870–941) and vote initiation logic around 634–694.
   - Early initiation truncates natural convergence—e.g., you start ballot before reconciling the exact amount.

4) Brittle numeric-only validation and i18n artifacts
   - Confirmation and ballot require strict numeric formats; any minor deviation fails.
   - Mixed-language tags/messages in public history can reduce model reliability.

5) Order and non-determinism in speaking
   - NumPy RNG not controlled by `seed_manager` can alter turn-taking and timing, shifting fragile convergence.

Given the log’s narrative convergence and repeated ballot failure, items (1) and (2) are the primary culprits. This is much more consistent with a design artifact than genuine preference reversal.

---

## Is This Genuine Agent Behavior?

Unlikely. The discussion shows explicit verbal agreement on both principle and amount; both agents declare readiness to vote. A genuine reversal would usually appear in text prior to the ballot. Instead, ballots silently diverge, which is typical when a generic numeric prompt asks the model to choose “best principle” rather than “vote the agreed principle and amount”. Combined with strict unanimity checks, the system strongly biases toward “no consensus” despite apparent agreement.

---

## Recommendations

1) Prime ballots with the negotiated candidate and amount
   - Add contextualized ballot prompts: “Based on the discussion, the group is proposing [Principle X] with [$Y]. Confirm your vote (1–4).” For amount stage, pre-fill or say “The discussed floor was $25,000; confirm or enter your amount.”

2) Implement constraint tolerance and correction
   - Use `Phase2Settings.constraint_tolerance` to allow small differences.
   - If amounts are within tolerance, treat as consensus; otherwise, trigger a one-turn reconciliation prompt (constraint correction) before declaring failure.

3) Require alignment check before secret ballot
   - Insert a light-weight “consent-to-proposal” step: ask each agent to restate the principle and amount they understand as the current proposal. If all match, proceed to secret ballot.

4) Avoid “first-Yes wins”; collect all initiation responses
   - Poll all participants for vote initiation within the round; proceed only if some threshold is met (e.g., majority or unanimity) to ensure readiness.

5) Tighten i18n throughout
   - Route all public-history tags and reminder messages through `language_manager` keys.
   - Remove mixed-language artifacts and English-only inserts in prompts (e.g., “YOUR INTERNAL REASONING”).

6) Stabilize speaking order RNG
   - Use `seed_manager` for NumPy RNG or unify on Python RNG for deterministic runs.

7) Telemetry and guardrails
   - Log the exact ballot contents per participant (internally, in debug logs) when consensus fails to directly observe mismatches (principle vs amount vs malformed).

---

## Direct Code References (Paths and Highlights)

- Discussion prompting and i18n:
  - `core/phase2_manager.py:1496–1531` (`_build_discussion_prompt`) – English “YOUR INTERNAL REASONING”; dynamic English group composition.
  - `core/phase2_manager.py:1061–1079` (`_get_voting_reminder_message`) – hard-coded reminder strings per language, not translation keys.
  - `models/experiment_types.py:188–191` (“[VOTE RESULT] …”) – English-only public-history tag.

- Vote initiation and confirmation:
  - `core/phase2_manager.py:870–941` (`_prompt_for_vote_initiation`) – immediate break on first “Yes”; strict numeric parsing.
  - `core/phase2_manager.py:1608–1718` (`_conduct_confirmation_phase`) – auto-confirm initiator; strict numeric validation; malformed response fails whole phase.

- Secret ballot (two-stage voting):
  - `core/two_stage_voting_manager.py:240–720` – stage implementations and validations (numeric-only; positive integer amount).
  - `core/two_stage_voting_manager.py:717–792` – strict unanimity on `(principle, constraint_amount)`; no tolerance/correction.
  - `config/phase2_settings.py:58–112` – `constraint_tolerance` and correction settings defined but not used by TwoStage manager.

- Reproducibility and order effects:
  - `core/phase2_manager.py:760–792` – speaking order uses NumPy RNG independent of `seed_manager`.

---

## Conclusion

The observed “convergence, then sudden non-consensus” is best explained by the current voting orchestration design rather than genuine agent preference shifts. The system transitions from a negotiated-discussion context to decontextualized, strict unanimity ballots with no tolerance and no priming, which reliably produces non-consensus even in cases of apparent agreement. Implementing the recommendations above should significantly reduce these failure modes and better reflect genuine consensus when it emerges in discussion.

