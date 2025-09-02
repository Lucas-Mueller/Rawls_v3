# Phase 2 Voting And Memory Deep Dive

This document critically assesses the Phase 2 (group discussion and consensus) flow, how voting is orchestrated, and how the memory system interacts with both phases. It uses experiment_results_20250902_142051.json as a concrete case study and maps observed outcomes back to specific code paths. It concludes with precise, code‑level recommendations.

## Executive Summary
- Phase 2 did run votes, but only when a per‑round “vote initiation” prompt is accepted and then universally confirmed. In the case study, Round 2’s ballot failed due to constraint disagreement (13k vs 14k), Round 3’s confirmation failed (one agent declined), and Round 4 reached consensus at 13k.
- Agents’ “final_vote: No vote” fields in the log are caused by a logging gap: individual ballot selections aren’t recorded to the AgentCentricLogger, so post‑discussion per‑agent vote fields are empty even when a vote occurred.
- The memory system mixes (a) LLM‑generated narrative updates, (b) selective simple insertions, and (c) phase transition deltas without a fact‑checking layer. This leads to contradictions (e.g., feasibility claims for distributions under a 13k floor) and weak guidance for constraint bargaining.
- Phase 1 memory is persisted into Phase 2 wholesale, but there’s no normalization or hard factual spine injected at the start of Phase 2; discussion summarizes are agent‑written and can drift from computed facts.

## What Happened In 2025‑09‑02T14:20‑14:33
- Consensus: true on `maximizing_average_floor_constraint` with a 13,000 floor in Round 4.
- Voting history (serialized correctly):
  - Round 2: vote initiated and confirmed; no consensus (13k vs 14k).
  - Round 3: vote initiated; confirmation failed (James: No).
  - Round 4: vote initiated and confirmed; consensus at 13k (2 votes).
- Agent logs show “final_vote: No vote” despite above, due to logger mapping not capturing per‑agent ballots.

## Phase 2 Flow: Code Walkthrough

Key modules:
- `core/phase2_manager.py` — Orchestrates discussion, vote prompting, confirmation, secret ballot, final payoff, and logging.
- `core/two_stage_voting_manager.py` — Structured two‑stage ballot (principle → amount), numeric validation, builds `VoteResult`.
- `utils/memory_manager.py`, `utils/selective_memory_manager.py`, `utils/simple_memory_manager.py` — Mixed memory update system (LLM‑generated vs direct insertions).
- `utils/agent_centric_logger.py` — Agent‑centric logs and voting history aggregation.

High‑level sequence per round (Phase 2 Manager):
1) Each participant produces a public statement with validation and retry (`_get_participant_statement_with_retry`). The system updates memory with a concise delta and logs the round.
2) End‑of‑round, each participant is asked: “Initiate vote? Yes(1)/No(0)” (`_prompt_for_vote_initiation`).
3) If any says Yes:
   - Confirmation phase: all must agree to proceed (`_conduct_confirmation_phase`). Any No (or malformed/timeout) aborts voting for that round.
   - Secret ballot: two‑stage voting for all (`_conduct_secret_ballot_phase` → `TwoStageVotingManager.conduct_full_voting_process`).
   - The `VoteResult` is appended to `GroupDiscussionState.vote_history` and reflected in public history. If unanimous on both principle and constraint, consensus is set on `GroupDiscussionResult`.
4) If consensus is reached at any point, Phase 2 concludes early; otherwise, the next discussion round begins.

Design note: automatic vote triggers from free‑form statements were explicitly removed. Only the explicit prompt can initiate voting now. This reduces false positives but increases the chance that no vote occurs until late rounds if agents don’t choose to initiate. See `phase2_manager.py` comments around “Formal voting system uses prompt‑based initiation only”.

## Voting Lifecycle Details

- Initiation: `_prompt_for_vote_initiation` uses numerical agreement detection (utility agent) to parse 1/0. Invalid inputs cause up to 3 retries, then default to No.
- Confirmation: Initiator is auto‑confirmed; others must respond 1/0; any No/invalid aborts the vote. Memory is updated with simple insertions for each confirmation response.
- Secret Ballot: `TwoStageVotingManager` asks for principle number (1–4) with strict numeric validation; for principles 3/4 it then asks for an integer amount (culturally adapted parsing, range checks). It converts results to `PrincipleChoice` and builds `VoteResult` with `vote_counts` grouped by principle+constraint.

Case Study mapping:
- Round 2: Both agreed to vote; one chose 13k and the other 14k → `vote_counts = {P3_13000: 1, P3_14000: 1}` → no consensus.
- Round 3: Confirmation failed due to a “No” response → no ballot.
- Round 4: Both chose P3 with 13k → consensus.

## Why “They Didn’t Conduct a Vote” (From a User’s Perspective)

1) Votes happen only when a participant explicitly says “Yes” to initiate, at the end of a round. If neither initiates, no voting occurs. This is by design after removing auto‑triggers.
2) Even when initiated, a single “No” during confirmation cancels the ballot for that round. In the case study, Round 3 failed here.
3) Logging gap: Even when ballots occur, the per‑agent “final_vote” field isn’t filled, which makes it look like no vote happened from the agent sections of the JSON, despite the canonical `voting_history` being correct.

Net effect: Users may perceive “no vote” or “inconsistent voting” because:
- Votes are gated by explicit initiation + unanimous confirmation.
- Agent logs don’t reflect individual ballot choices.
- Memory narratives can under‑emphasize the formal voting status and outcomes.

## Memory System: Architecture And Pain Points

Paths:
- Phase 1: uses `MemoryManager.prompt_agent_for_memory_update` extensively to write free‑form LLM memory after each sub‑step (ranking, explanation, applications). Final Phase 1 memory is carried forward.
- Phase 2: for public statements, uses `SelectiveMemoryManager.update_memory_selective` to build concise deltas; for vote initiation decisions and confirmations, uses `SimpleMemoryManager` direct insertions (templated, no LLM); for two‑stage votes, the voting manager writes a “Two‑Stage Voting Complete” summary via `MemoryManager.prompt_agent_for_memory_update`.
- Phase transitions (initiation/confirmation/secret_ballot/results) also append templated status to memory for all participants.

Observed issues:
- Fact drift: Free‑form LLM updates can contradict computed facts (e.g., feasibility under a 13k floor). There’s no guard that verifies feasibility claims against actual distribution stats.
- Redundancy/noise: Phase transition messages + round deltas + narrative memories can bloat or drown out critical factual anchors.
- Weak constraint bargaining memory: There’s no structured “constraint frontier” block that persists across rounds, so agents don’t anchor on feasible sets by floor value. They rely on their own (fallible) narration.
- Logging/Memory mismatch: Per‑agent ballot choices are not recorded into `AgentCentricLogger` rounds, so “final_vote” remains “No vote” even after a successful ballot.

## Phase Interplay (Phase 1 → Phase 2)

- Phase 1 memory is persisted verbatim into Phase 2; the system doesn’t inject a standardized factsheet at Phase 2 start. If an agent internalized an incorrect heuristic in Phase 1, that guidance continues to shape Phase 2 statements.
- During Phase 2, selective/simple updates try to keep memory compact, but LLM‑based updates (e.g., voting summary) can reintroduce narrative drift.
- There’s no explicit reconciliation step (e.g., “verify statements against computed feasibility table for the current constraint”) to correct agent memories.

## Concrete Inconsistencies From The Case Study

- Feasibility claim: Several agent messages assert that at a 13k floor, both Dist 1 (floor 13k) and Dist 2 (floor 12k) are feasible. If feasibility means min income ≥ floor, Dist 2 is infeasible at 13k. This looks like LLM narrative drift, not system computation.
- Agent preferences vs favored principle: Alice ends with a ranking that puts P3 third, despite repeatedly favoring P3 in discussion (certainty “sure”). This reveals memory/ranking fragility post‑hoc, likely driven by narratives rather than hard constraints.
- “No vote” in agent sections despite recorded ballots in `voting_history` (Round 2 and 4). Root cause: missing per‑agent ballot logging in `TwoStageVotingManager`.

## Root Causes And Fixes

1) Voting visibility and reliability
- Root cause: Vote occurs only via explicit initiation + unanimous confirmation; agent sections miss per‑agent ballot entries.
- Fixes:
  - Add a “last‑round must‑vote” fallback: if no consensus by last round, auto‑initiate confirmation + ballot. Location: `Phase2Manager.run_phase2` end‑of‑round loop.
  - When two agents’ favored principles match (and constraint proposals are “close”), prompt a constrained negotiation prompt that proposes a midpoint or Pareto‑feasible amount before confirmation.
  - Record per‑agent ballots to logger:
    - In `core/two_stage_voting_manager.py`, after each participant finalizes their two‑stage selection, call `AgentCentricLogger.log_vote_response(...)` with the raw response and assessed choice. This enables `final_vote` extraction.
    - After consensus, call `AgentCentricLogger.update_agent_votes(...)` with per‑agent votes and timestamps.

2) Memory factuality and constraint anchoring
- Root cause: Free‑form LLM memory updates can contradict computed facts; no hard factual scaffolding.
- Fixes:
  - Inject a concise, computed “Constraint Feasibility Panel” at Phase 2 start and whenever constraints are discussed (e.g., for floors 12k/13k/14k), listing feasible distributions and their averages. Use `SimpleMemoryManager.insert_simple_status_update` with deterministic content from `DistributionGenerator`.
  - During vote rounds, append a verified “Ballot Facts” block: agreed principle, constraint, feasible set, chosen distribution, and payoff mapping. Source from the actual `VoteResult` and `DistributionGenerator.apply_principle_to_distributions`.
  - Add a lightweight “feasibility guard” to `SelectiveMemoryManager._full_memory_update`: scan proposed memory text for floor feasibility claims and auto‑append a correction header when textual claims contradict computed feasibility. Keep it non‑blocking; add “[Correction]” lines rather than refusing updates.

3) Constraint bargaining guidance
- Root cause: Prompts don’t provide a structured rhythm for converging on amounts.
- Fixes:
  - Enhance `language_manager.get("prompts.phase2_discussion_prompt")` to include a short “Converge now” checklist on later rounds: “List your two acceptable floor amounts; if ranges overlap, propose midpoint and initiate vote.”
  - Add a mini‑protocol before confirmation: as initiator proposes an amount, the other agent gets an amount‑proposal prompt with numeric validation; if the counter is within ±$1,000 of initiator, the system offers midpoint and re‑prompts confirmation.

4) Post‑hoc alignment of agent logs and results
- Root cause: Agent JSON sections don’t display who voted for what.
- Fixes:
  - After `_conduct_secret_ballot_phase`, construct a per‑agent map of ballots and pass it into `logger.log_post_discussion(..., final_vote=..., vote_timestamp=...)`. Use `GroupDiscussionState.last_vote_result.votes` and `AgentCentricLogger.current_vote_round.participant_votes` as sources.
  - Ensure `AgentCentricLogger.generate_target_state()` carries these per‑agent votes into `agents[*].phase_2.post_group_discussion.final_vote` instead of “No vote”.

## File‑Level Pointers (Where To Change)

- Vote logging gap:
  - File: `core/two_stage_voting_manager.py`
    - After each participant’s successful two‑stage selection, call `self.logger.log_vote_response(participant.name, raw_response, assessed_choice, constraint_amount, parsing_success=True, vote_timestamp=datetime.now().isoformat())`.
    - After final `VoteResult`, call `self.logger.complete_vote_round(...)` if not already done by `Phase2Manager` or ensure `Phase2Manager` consolidates both.
  - File: `core/phase2_manager.py`
    - After consensus, build and pass per‑agent ballot data into `logger.log_post_discussion(...)` via `_extract_participant_vote_info` or, better, a new helper that maps `participant_name → (principle, constraint, timestamp)`.

- Must‑vote fallback:
  - File: `core/phase2_manager.py`
    - At the end of the final discussion round (if no consensus), invoke `_conduct_voting_process` unconditionally.

- Constraint feasibility panel:
  - Files: `core/distribution_generator.py` (add a helper to compute feasible distributions for a given floor), `utils/simple_memory_manager.py` (use `insert_simple_status_update`), and calls from `phase2_manager.py` on amounts frequently discussed.

- Memory correction guard:
  - File: `utils/selective_memory_manager.py`
    - In `_full_memory_update`, after LLM returns a narrative, add a small post‑processor that compares claims about feasibility against `DistributionGenerator` calculations and appends a “[Correction]” line when they diverge.

## Agent’s Perspective: What It Felt Like

As Alice/James, Phase 2 felt like:
- I argued repeatedly for P3 with a 13k floor, but my memory didn’t pin down a shared “feasible set” table. So when constraints were discussed, we kept circling around claims like “Dist 2 is feasible at 13k,” which weren’t verified.
- In Round 2, we did vote, but picking 13k vs 14k killed consensus. I didn’t get a strong prompt to converge numerically (e.g., midpoint) right then.
- In Round 3, I declined confirmation once to continue discussion, but nothing in memory strongly encouraged a concrete compromise path. My log also doesn’t show my ballot choice later, so it looks like I “never voted.”
- In Round 4, we finally agreed on 13k, but our personal logs still don’t show our actual ballots, and the summary text conflates unconstrained averages with constrained feasibility in places.

## Quick Wins (Low Risk)
- Log per‑agent ballots to `AgentCentricLogger` in `TwoStageVotingManager`.
- If no consensus by the last round, auto‑initiate confirmation + ballot.
- Insert a computed “Constraint Feasibility Panel” whenever floors are debated (e.g., 12k/13k/14k). Keep it templated and non‑LLM to prevent drift.
- Fix final agent JSON to include `final_vote` and `vote_timestamp` when available.

## Medium Wins
- Add a constraint convergence prompt (midpoint suggestion) when both choose P3 but differ on amounts.
- Post‑processor that appends “[Correction] …” to LLM memory when feasibility claims contradict computed facts.

## Stretch Goals
- Introduce a structured “facts” section at the top of agent memory that is immutable per round and machine‑maintained (distributions, feasibility by constraint, last ballot result). Keep narrative below it.
- Maintain a compact “Constraint Frontier” object in memory that agents can reference and revise (11k–15k map of who wins and why).

## Closing
The current Phase 2 design is intentionally conservative about initiating votes and tightly validates ballots. That’s good. The two biggest causes of confusion are (1) the gating (initiation + confirmation) and (2) the log/memory mismatch that hides who voted for what and allows factual drift in narratives. The changes above keep the architecture but add clarity and reliability where it will be most felt by both agents and users.

