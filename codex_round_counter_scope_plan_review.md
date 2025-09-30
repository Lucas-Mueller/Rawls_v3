# Round Counter Scope Plan Review

## Issue Summary
- Plan seeks to confine `ParticipantContext.round_number` to genuine application/discussion loops to remove misleading metadata in other sub-phases.

## Codebase Alignment
- `ParticipantContext.round_number` is a required `int` across the model and update helper, so every context clone today assumes a numeric payload (`models/experiment_types.py:121`, `experiment_agents/participant_agent.py:329`).
- Phase 1 prompts already use dedicated keys; the current sentinel values in the instruction helper are merely a thin mapping layer (`utils/language_manager.py:285`).
- Phase 2 instruction scaffolding formats "Round X of Y" headers directly from the context’s counter, and discussion history logging mirrors the same value (`experiment_agents/participant_agent.py:273`, `utils/language_manager.py:548`).
- Memory updates consume the round number to pick templates and to stamp agent telemetry; they treat missing/`None` rounds as first-round fallbacks (`utils/memory_manager.py:98`).

## Critical Feedback
- **Critical – Data model conflict:** Resetting `round_number` to `None` requires widening the core schema plus every instantiation site; without that sweep `ParticipantContext` will fail validation, and `update_participant_context` will silently reapply the stale integer (`models/experiment_types.py:121`, `experiment_agents/participant_agent.py:329`).
- **Critical – Instruction regressions:** Clearing the counter for voting/final ranking makes the instruction layer print "Round None" and drops the discussion header entirely, because both `_generate_dynamic_instructions` and the translation templates expect an integer (`experiment_agents/participant_agent.py:273`, `utils/language_manager.py:548`).
- **Critical – Phase 1 scope inflation:** Swapping sentinel integers for new stage-specific accessors forces translation churn across every locale even though stage prompts already exist; the plan ignores that the task prompts are already keyed by stage and only the instruction shim maps numbers to those keys (`core/phase1_manager.py:251`, `utils/language_manager.py:295`).
- **Important – Memory/template coupling:** Memory prompts rely on the numeric round to detect first-pass cases and to keep audit trails coherent; forcing `None` pushes a wave of defensive logic into `MemoryManager` and downstream analytics (`utils/memory_manager.py:98`).
- **Important – Logging/data parity:** Agent-centric logs, vote analytics, and discussion transcripts all assume integer rounds; introducing `None` or new labels without a shared stage enum risks splitting the data set and undoing the analytics fixes already queued up in the previous review (`utils/logging/agent_centric_logger.py:192`).

## Recommendations
- Keep the numeric counter authoritative and address the misleading scaffolding by enriching context metadata (e.g., a `stage` enum or by reusing `interaction_type`) rather than nulling the counter; this keeps instructions and logs aligned with existing helpers.
- Populate the existing stage-specific translations (`phase1_round0_initial_ranking`, etc.) so agents see differentiated headers without touching the counter wiring, and add a dedicated post-discussion/voting header in the language layer instead of blanking the number.
- If you need to hide the round label during voting, route those prompts through a dedicated formatter that swaps in a "Voting Stage" banner while leaving `round_number` intact for telemetry.

## Alternative Approaches
- Introduce a lightweight `PhaseStage` enum alongside the existing counter so sub-phases can be labelled explicitly; migrate instructions/logging to prefer the enum when present, falling back to the numeric round for continuity.
- Add a helper on `Phase2Manager` that snapshots `discussion_state.round_number` after the loop and then bumps contexts to a deterministic "results" round (e.g., `final_round + 1`), keeping integers monotonic while signalling the stage change in copy.
