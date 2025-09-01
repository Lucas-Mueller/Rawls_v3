# Phase 2 Implementation Review

This document explains the Phase 2 (group discussion and consensus) flow and pinpoints every place participant memory is updated. Primary modules: `core/phase2_manager.py`, `core/two_stage_voting_manager.py`, `utils/memory_manager.py`, `utils/simple_memory_manager.py`, and `experiment_agents/participant_agent.py`.

## High‑Level Flow
- Entry: `Phase2Manager.run_phase2(config, phase1_results, logger)`.
- Initialize contexts from Phase 1 → run multi‑round discussion → optional prompted voting → apply principle or randomize → log detailed results → collect final rankings.

## Detailed Sequence
1) Context initialization
- `core/phase2_manager.py::_initialize_phase2_contexts`
  - Validates/sanitizes prior memory (`_validate_and_sanitize_memory`).
  - Builds `ParticipantContext` with carried `bank_balance`, validated `memory`, `memory_character_limit`, `phase=PHASE_2`.
  - Memory update: context seeded with Phase 1 memory (continuous memory).

2) Discussion rounds
- Loop per round: speaking order via `_generate_speaking_order`.
- For each participant:
  - `context.round_number = round_num`; capture `memory_before` (for logs).
  - Optional internal reasoning: `_get_participant_statement_enhanced` → `_build_internal_reasoning_prompt` → `Runner.run(...)` with timeout and retries.
  - Public statement: `_get_participant_statement_with_retry` with validation, backoff, quarantine fallback.
  - Add to `GroupDiscussionState.public_history` (neutral text if quarantined).
  - Memory update: build delta via `utils.memory_content.build_phase2_delta` then:
    - `context.memory = MemoryManager.prompt_agent_for_memory_update(...)` [core/phase2_manager.py, discussion loop].
  - Persist round in context: `update_participant_context(context, new_round=round_num)`.

3) End‑of‑round vote prompting (prompt‑based)
- `_prompt_for_vote_initiation` asks each agent if they want to vote now (short timeout, numeric 1/0 parsing).
- Memory update (decision): `SimpleMemoryManager.insert_vote_initiation_decision(context, round_num, wants_vote, language_manager)` appends a localized line to memory.
- If any agent answers “Yes”, `_conduct_voting_process` runs.

4) Voting process (two‑stage)
- Mark `discussion_state.vote_triggered = True`; log start.
- Broadcast + Memory update (phase start): `_update_all_memories_for_voting_phase("initiation", contexts, initiator_name)` → for each context:
  - `context.memory = MemoryManager.prompt_agent_for_memory_update(...)` (localized voting phase message).
- Confirmation phase: `_conduct_confirmation_phase`
  - Each participant confirms 1/0; public history recorded.
  - Memory update (per response): `SimpleMemoryManager.insert_confirmation_response(context, agrees_to_vote, language_manager)` appends to memory.
- Secret ballot: `core/two_stage_voting_manager.py`
  - Stage 1 (principle 1–4) with numeric validation, retries, timeouts.
  - Stage 2 (amount) for principles 3/4 with culturally aware amount parsing.
  - Memory update (per voter completion): `_update_participant_memory_for_voting(...)` builds a complete voting delta and calls:
    - `context.memory = MemoryManager.prompt_agent_for_memory_update(...)`.
  - `VoteResult` produced; if consensus, set `discussion_state._consensus_result` and localized message added to history.

5) Payoffs and final rankings
- Apply agreed principle or random assignment: `_apply_group_principle_and_calculate_payoffs`.
- Build detailed, multilingual “Phase 2 Final Results” with counterfactuals: `_build_phase2_detailed_results`.
- Memory update (final results):
  - `context.memory = MemoryManager.prompt_agent_for_memory_update(participant, context, f"Final Phase 2 Results: {result_content}", ...)`.
- Update balances via `update_participant_context(..., balance_change=final_earnings)` and request final ranking.

## Memory Update Touchpoints (all writes)
- Seed from Phase 1: `core/phase2_manager.py::_initialize_phase2_contexts` → `context.memory = validated_phase1_memory`.
- After each statement: `core/phase2_manager.py` (discussion loop) → `MemoryManager.prompt_agent_for_memory_update(...)` assigns `context.memory`.
- Vote initiation decision: `SimpleMemoryManager.insert_vote_initiation_decision(...)` appends to `context.memory`.
- Voting phase start broadcast: `_update_all_memories_for_voting_phase("initiation", ...)` → `MemoryManager.prompt_agent_for_memory_update(...)` per context.
- Confirmation responses: `SimpleMemoryManager.insert_confirmation_response(...)` appends to `context.memory`.
- After two‑stage vote per agent: `core/two_stage_voting_manager.py::_update_participant_memory_for_voting` → `MemoryManager.prompt_agent_for_memory_update(...)` assigns `context.memory`.
- Final results: `core/phase2_manager.py::_collect_final_rankings` → `MemoryManager.prompt_agent_for_memory_update(...)` assigns `context.memory`.

## Notes & Suggestions
- Compression and limits: `MemoryManager` auto‑compresses when near limits (15% tolerance; utility agent fallback). `SimpleMemoryManager` appends without length checks—safe due to short inserts but consider guardrails if memory grows large.
- Voting phase updates: `_update_all_memories_for_voting_phase` supports "confirmation", "secret_ballot", "results" but is only invoked for "initiation" here; consider calling for later phases for a richer memory narrative.
- Quarantine: failed statements are neutralized in public history; deltas use the post‑processed `statement`. Ensure neutralization aligns with memory deltas in multilingual flows.
