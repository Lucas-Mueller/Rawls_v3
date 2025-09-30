# Round Counter Stage-Awareness Plan

## Objective
Clarify when `ParticipantContext.round_number` is displayed without removing the numeric counter that downstream logging and memory systems rely on. We supplement the counter with explicit stage metadata so instructions can highlight application/discussion rounds while other sub-phases present stage-specific copy instead of misleading round labels.

## Key Considerations
- `ParticipantContext.round_number` is required (`models/experiment_types.py:121`); `update_participant_context` always clones a numeric value.
- Instruction helpers (`experiment_agents/participant_agent.py:270`, `utils/language_manager.py:455`) and logging/memory services (`utils/memory_manager.py:98`, `utils/logging/agent_centric_logger.py:192`) expect an integer.
- Phase 1 already exposes stage-specific translations (`phase1_round0_initial_ranking`, etc.); we can leverage those directly instead of mapping synthetic integers.

## Proposed Updates
1. **Introduce stage metadata**
   - Add a lightweight enum or string field (e.g., `context.stage`) set by phase managers to describe the current sub-phase (`initial_ranking`, `demonstration_round`, `voting`, `final_ranking`).
   - Default to `None` where legacy flows are unchanged so existing code paths continue to work.

2. **Instruction layer adjustments**
   - Update `_generate_dynamic_instructions` to prefer stage-specific templates when `context.stage` is set.
   - Continue passing the numeric round to discussion/application prompts so headers like "Round X of Y" remain intact.
   - For non-round stages (voting, final ranking, results delivery) provide dedicated instruction keys keyed off the new stage rather than manipulating the counter.

3. **Phase manager wiring**
   - Phase 1: set `context.stage` prior to each ranking/explanation step; maintain round numbers only inside the existing `for round_num in range(1, 5)` loop.
   - Phase 2: set `context.stage` to `discussion` during the loop, then transition to stages such as `voting`, `results`, `final_ranking` while leaving the last discussion `round_number` untouched for telemetry.

4. **Language assets**
   - Add minimal stage-specific entries (e.g., `context_stage_voting_prompt`) across translations; reuse existing content where possible to avoid churn.
   - Leave current round-based strings intact for discussion/application use.

5. **Logging & memory alignment**
   - Continue recording numeric rounds for analytics; extend logs to capture the optional stage label when present.
   - Ensure memory templates that key off round 1 continue to do so; no change required beyond passing through the new stage when helpful.

6. **Testing & validation**
   - Extend unit tests for instruction generation to cover stage-aware paths.
   - Run Phase 1/Phase 2 integration checks verifying:
     - Application/discussion steps still show rounds.
     - Voting/results/final ranking display stage names instead of "Round None".
     - Logging output continues to report integer rounds while optionally showing stage labels.

## Deliverables
- Stage metadata added to participant contexts and propagated by phase managers.
- Instruction helpers updated to use stage-specific templates.
- Translations augmented with concise stage strings.
- Updated unit/integration tests validating both round-based and stage-based prompts.
