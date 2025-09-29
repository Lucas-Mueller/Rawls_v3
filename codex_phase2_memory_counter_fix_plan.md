# Phase 2 Memory Counter Fix Plan

## Diagnosis
- `MemoryManager.prompt_agent_for_memory_update()` ignores the phase/round metadata it receives. The method builds the prompt with `round_number`/`phase`, but ultimately calls `agent.update_memory(prompt, context.bank_balance)` without passing those values, so the participant agent defaults to `phase=ExperimentPhase.PHASE_1` and `round_number=0` (`utils/memory_manager.py:107-111`, `experiment_agents/participant_agent.py:226`).
- Because the temporary `ParticipantContext` constructed inside `ParticipantAgent.update_memory()` is stamped with those defaults, the instruction wrapper rendered to the LLM shows "Phase 1, Round 0" even when Phase 2 contexts supply correct counters.
- Direct callers that bypass `MemoryService` (e.g., two-stage voting fallbacks) also omit explicit counters, depending on the same broken defaulting path.

## Goals
1. Ensure every memory update prompt in Phase 2 reflects the actual discussion round and phase.
2. Preserve existing Phase 1 behaviour while avoiding redundant counter plumbing in individual call sites.
3. Provide regression coverage to prevent future reintroductions of the mismatch.

## Implementation Plan
1. **Normalize counter resolution in `MemoryManager`:**
   - Inside `prompt_agent_for_memory_update`, compute `effective_round` and `effective_phase` by falling back to the supplied `context` when explicit arguments are `None`.
   - Thread `effective_phase`/`effective_round` into both `_create_memory_update_prompt(...)` and the downstream `agent.update_memory(...)` call so the temporary context inherits the correct values.
2. **Harden direct callers:**
   - Update remaining direct usages (e.g., `core/two_stage_voting_manager.py:1155`, `_fallback_memory_update` in `core/services/counterfactuals_service.py`) to pass `round_number=context.round_number` and `phase=context.phase.value` when they are available. This keeps legacy paths consistent and documents expectations at the call site.
3. **Add regression tests:**
   - Unit test `MemoryManager.prompt_agent_for_memory_update` with a stub `ParticipantAgent` to assert that the method forwards phase/round to `agent.update_memory` when the context carries Phase 2 metadata.
   - Add a Phase 2 integration test (or extend an existing golden test) that triggers a discussion memory update and verifies the prompt header contains "Phase 2" and the correct round number.
4. **Documentation & cleanup:**
   - Note the change in the relevant maintenance report or changelog entry, instructing future contributors to rely on the shared helper rather than hand-wiring counters.

## Testing Strategy
- Run updated unit tests plus `python run_tests.py unit` to ensure no regressions.
- Execute a targeted Phase 2 integration scenario (e.g., `python run_tests.py integration --tests tests.integration.test_phase2_flow`) to confirm discussion logs and memory updates reflect correct counters.

## Risks & Mitigations
- **Risk:** Unexpected callers rely on the old default of Phase 1/round 0. *Mitigation:* Central fallback to `context` values preserves behaviour for any path that already updated the context correctly.
- **Risk:** Tests asserting exact prompt text may fail due to the phase label change. *Mitigation:* Update expectation snapshots where necessary after verifying correctness.

## Expected Outcome
Agents and analytics will see accurate Phase 2 phase/round metadata in all memory updates, eliminating the "Phase 1, Round 0" mislabeling without requiring widespread per-call fixes.
