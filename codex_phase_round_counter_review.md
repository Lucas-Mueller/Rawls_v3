# Phase & Round Counter Review

## Context primitives
- `ParticipantContext` couples agent identity, `phase`, and `round_number` so the instruction layer and memory templates can render phase-aware guidance (`models/experiment_types.py:115`). It also carries optional interaction metadata that downstream services reuse.
- Context updates clone the object through `update_participant_context`, which preserves existing `interaction_type` and only overrides `round_number`/`phase` when explicitly provided (`experiment_agents/participant_agent.py:315`). Bank balance adjustments are also funneled through this helper.
- Group-level sequencing for Phase 2 is tracked separately through `GroupDiscussionState.round_number`; every public transcript entry stamps the current discussion round into the record (`models/experiment_types.py:139`).

## Phase 1 lifecycle

### Round sequencing
| Step | `round_number` in context | Purpose | References |
| --- | --- | --- | --- |
| Initial ranking | 0 | First preference capture | `core/phase1_manager.py:251`
| Principle explanation | -1 | Learning-only pass that still flows through memory prompts | `core/phase1_manager.py:276`
| Post-explanation ranking | 0 (reset) | Second ranking immediately after the tutorial | `core/phase1_manager.py:302`
| Demonstration rounds | 1‑4 | Principle application loop with earnings updates | `core/phase1_manager.py:330`
| Final ranking | 5 | Closing preference capture before Phase 2 hand-off | `core/phase1_manager.py:390`

### How it behaves today
- Each stage manually injects a sentinel into `context.round_number` before calling the relevant `Runner.run` and memory update. The helper is invoked again afterward so downstream code sees the same `round_number`.
- The memory prompts rely on the injected values but only switch behaviour when the phase is "phase_2", so the negative/duplicated values do not affect template selection (`utils/memory_manager.py:201`).
- Phase-specific instructions in the language layer reuse `round_number` to look up snippets. Because `phase1_round0_initial_ranking`, `phase1_rounds1_4_principle_application`, and `phase1_round5_final_ranking` are currently blank strings in the English prompt file (`translations/english_prompts.json:121`), agents mostly rely on the task prompt rather than the instruction header to understand the stage.

### Observed pain points
- Reusing `0` for both ranking tasks makes the surrounding instruction scaffold indistinguishable; without peeking at the prompt body an agent cannot tell whether they are before or after the explanation (`experiment_agents/participant_agent.py:301`).
- The sentinel `-1` is only meaningful to developers. Shared utilities or analytics that assume non-negative, monotonic rounds could misinterpret this step.
- The manual pattern forces each new feature to touch multiple sites (set number, run prompt, update context), increasing the risk of drift.

## Phase 2 discussion loop

### Round sequencing
| Stage | `round_number` | Behaviour | References |
| --- | --- | --- | --- |
| Context bootstrap | 1 | Phase 2 contexts are recreated from Phase 1 output with validated memory | `core/phase2_manager.py:299`
| Discussion rounds | 1..N | `GroupDiscussionState.round_number` and every participant context are updated per loop iteration | `core/phase2_manager.py:640`
| Post-round memory | 1..N | After all statements, memory updates run while `round_number` remains set to the completed iteration | `core/phase2_manager.py:724`
| Voting prompts | current round | Vote initiation and confirmation re-use the same context, so instructions still display the current discussion round | `core/services/memory_service.py:429`
| Consensus output | final round | `GroupDiscussionResult.final_round` records where the conversation stopped | `models/experiment_types.py:207`

### How it behaves today
- Every prompt – internal reasoning, public statements, retry loops – receives a context whose `round_number` matches the live discussion cycle, so agents see "Round X of Y" headers in both the instruction layer and the short prompt (`core/services/discussion_service.py:370`).
- Discussion history appended through `GroupDiscussionState.add_statement` embeds the same round number, so transcripts remain synchronised (`models/experiment_types.py:154`).
- `update_participant_context` keeps the active `round_number` after each memory update, ensuring subsequent services (vote prompts, counterfactual delivery) still know where the agent left off (`core/phase2_manager.py:731`).

### Observed pain points
- Contexts retain the last `interaction_type` set by the discussion service. When they are cloned after memory updates, that stale flag rides along; downstream callers must remember to clear it (for example, final rankings do so manually in `core/services/counterfactuals_service.py:821`).
- The looping code expects everyone to speak every round and only marks a round “complete” after post-round memory updates. If a participant continually fails validation the round counter still advances, but their contexts never log a statement, leading to an asymmetry between `round_number` and agent-specific history.

## Voting and consensus instrumentation
- Vote initiation prompts piggyback on the discussion context. They attempt to log requests by checking for `context.current_round_number`, but `ParticipantContext` only exposes `round_number`, so the logging branch never executes (`core/services/voting_service.py:193`). As a result, vote initiation data must be recovered indirectly from the agent logs.
- Memory entries for vote decisions, confirmations, and ballot steps stamp the round they received via the `round_num` argument, so history survives even when logging is silent (`core/services/memory_service.py:429`).

## Phase 2 results and final ranking
- After consensus, `deliver_results_and_update_memory` adjusts balances and replaces memory content but leaves `round_number` untouched (`core/services/counterfactuals_service.py:547`). Contexts therefore still reflect the last discussion round when results are delivered.
- Immediately before requesting the final ranking, the streamlined path clears several fields, including `context.round_number = None`, to avoid discussion-mode formatting (`core/services/counterfactuals_service.py:821`). Because `language_manager.get_phase2_instructions` simply forwards the value into the header (`utils/language_manager.py:303`, `translations/english_prompts.json:124`), agents see “Round None of N”, and tooling that expects integers must defensively handle `None`.
- There is no dedicated phase or sub-phase for the results/ballot stage, so both context instructions and downstream analytics must infer the stage from prompts rather than from the counters.

## Cross-cutting observations
- Counter management is entirely manual: every call site sets the number, updates memory, then re-clones the context. There is no shared state machine that knows which stage should follow the last, so adding a new sub-phase requires adjusting multiple scattered assignments.
- Negative or duplicated round values are not validated anywhere. If auxiliary services later assume monotonic, positive rounds (for example, when plotting progress), they must special-case Phase 1’s tutorial pass.
- Because `update_participant_context` keeps `interaction_type` intact, callers must remember to reset it when moving between fundamentally different tasks. Forgetting to do so can lead to mismatched templates or tool availability.

## Overall assessment
- Phase 1 and Phase 2 counters progress without skipping values during normal execution, so the core loops behave as intended. Agents do receive correct per-round prompts, and memory entries are stamped with aligned numbers.
- However, the counter semantics are implicit and spread across several modules. Agents occasionally receive confusing scaffolding (“Round None”, identical headers for both rankings), and instrumentation gaps like the unused `current_round_number` reduce visibility into vote behaviour.

## Recommendations

1. **Introduce explicit stage enums or descriptors.** Replace magic integers (`-1`, `0`, `5`) with a `Phase1Stage`/`Phase2Stage` enum and extend `ParticipantContext` with a `stage` or `sub_phase` field. Centralising the transitions would let `language_manager` deliver precise instructions without relying on sentinel numbers.
2. **Provide a context update utility that simultaneously sets `round_number`, clears stale interaction metadata, and records stage changes.** This would remove the need for repeated manual resets and reduce the risk of leaking `interaction_type` across tasks.
3. **Fix vote logging by using `context.round_number` (or by attaching `current_round_number` when contexts are built).** This one-line change in `core/services/voting_service.py:193` would re-enable round-level analytics for initiation attempts.
4. **Give the post-discussion flow its own counters.** Either introduce a `PHASE_2_RESULTS` phase or reserve a dedicated round label (e.g., `round_number = discussion_result.final_round + 1`) with matching instruction copy so agents know they have left the discussion loop.
5. **Differentiate the two Phase 1 ranking prompts in the instruction layer.** Populate `phase1_round0_initial_ranking` and add a new key for the post-explanation ranking so the instruction scaffold mirrors the narrative agents read in the prompts.
6. **Guard against non-numeric round values in shared utilities.** Where wrappers ingest `round_number`, add light validation or defaulting to keep analytics resilient if future changes introduce new sentinel values.

Addressing these points would make the agent experience clearer, simplify counter management, and shrink the number of places that must change when new sub-phases or retries are added.
