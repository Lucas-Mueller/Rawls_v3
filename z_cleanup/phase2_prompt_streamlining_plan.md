# Phase 2 Prompt Orchestration – Updated Streamlining Plan

## Context
Following the external review (`phase2_prompt_streamlining_plan_review.md`), this document keeps the original diagnostic findings but reshapes the remediation strategy to stay aligned with the codebase’s services-first architecture and the project’s emphasis on simplicity.

## Review Feedback Synthesis
- **Agreements**
  - Hidden dependence on `ExperimentConfiguration._current_public_history` is a primary risk that must be eliminated without changing prompts (`core/phase2_manager.py:334`, `experiment_agents/participant_agent.py:289`).
  - Golden tests need to reflect the _actual_ strings produced by production services (discussion, reasoning, voting, results) so future changes are safe.
  - Prompt assembly responsibilities should remain within the existing services; duplicating orchestration in new builder layers would overcomplicate maintenance.
  - Any migration away from `_current_public_history` requires a staged plan with compatibility guards and explicit validation.
- **Partial Disagreements / Adjustments**
  - Rather than introducing large prompt-state objects, we will pass existing domain models more explicitly and add targeted helpers only if they remove real duplication.
  - Instead of a monolithic `run_turn()` method, we will extract small orchestration helpers inside `Phase2Manager` while keeping prompt construction and validation inside services.
  - Shared prompt formatting utilities remain desirable, but they will live as private helpers within services (or a `_prompt_utils` module) rather than a new public builder API.

## Guiding Principles
1. **Prompts remain byte-identical** across all supported languages unless intentionally re-baselined.
2. **Services own prompt construction**, Phase2Manager orchestrates sequencing and retries.
3. **Changes land incrementally**, each guarded by tests that capture current behaviour.
4. **Backward compatibility first**: `_current_public_history` is removed only after all consumers have migrated.

## Updated Roadmap

### Phase 1 – Baseline & Observability
1. **Service-Level Golden Tests**
   - Snapshot outputs from `DiscussionService.build_discussion_prompt`, `build_internal_reasoning_prompt`, voting prompts (`VotingService`, `TwoStageVotingManager`), results/ranking prompts (`CounterfactualsService`).
   - Cover English, Spanish, Mandarin by exercising the real `LanguageManager` with frozen translations.
   - Parameterize dynamic values (round numbers, participants) so snapshots remain stable.
2. **Integration Checks for `_current_public_history`**
   - Add a focused test ensuring Phase2Manager sets the attribute before each Runner call and clears it afterward.
   - Assert ParticipantAgent and MemoryService still read the expected history during the test harness run.

### Phase 2 – Explicit Prompt Data Flow (Compatibility Mode)
1. **Explicit History Parameters**
   - Extend service interfaces to accept `public_history` (or derived transcript text) explicitly while continuing to read `_current_public_history` as a fallback.
   - Phase2Manager passes the history argument on every call; tests confirm both paths produce identical strings.
2. **Context Header Preparation Helper**
   - Add a minimal helper in Phase2Manager (e.g., `_format_phase2_context_header`) that prepares the discussion header once per turn and stores it in the participant context, reducing repeated formatting logic.
   - ParticipantAgent prefers the pre-formatted header when present; otherwise it falls back to existing formatting.
3. **Instrumentation & Warnings**
   - Emit a debug warning when `_current_public_history` fallback is exercised, signalling remaining migration work without failing runs.

### Phase 3 – Duplication Reduction & Cleanup
1. **Retry Flow Consolidation**
   - Extract a `_execute_discussion_turn_with_retry` helper inside Phase2Manager so both initial turn execution and validation retries share the same logic path while still delegating prompt construction to DiscussionService.
2. **Voting Prompt Helpers**
   - Introduce private helper functions within `core/services/voting_service.py` (or a local `_prompt_utils`) to consolidate repeated translation lookups shared with `TwoStageVotingManager`.
3. **ParticipantContext Utility Methods**
   - Add methods such as `prepare_for_discussion()`, `prepare_for_voting()`, and `prepare_for_final_ranking()` that encapsulate the repeated field resets spotted across services.
4. **Retire `_current_public_history`**
   - Once all call sites pass explicit history and tests confirm no fallback usage, remove the attribute and associated warnings.
   - Update documentation (CLAUDE.md, prompt fix summaries) to reflect the new contract.

## Validation Strategy
- Golden tests from Phase 1 become mandatory pre-merge checks.
- CI gains targeted integration coverage for discussion/voting turn orchestration, ensuring retries and memory updates use the new helpers.
- Manual regression: run `tests/component/test_phase2_manager_live.py` and a smoke experiment to confirm runtime prompts and logs match historical output.

## Deferred Ideas (Not Pursued Now)
- Public prompt builder module.
- New prompt-state dataclasses.
- Mega-method orchestration inside services.

These remain potential future explorations if duplication persists after the incremental cleanup, but they are deliberately out of scope until simpler measures prove insufficient.

## Rollback/Contingency
- Each phase lands behind guard rails: the fallback path for `_current_public_history` stays active until removal, enabling quick revert.
- Snapshot updates require explicit approval; any accidental change will be caught immediately by failing golden tests.
