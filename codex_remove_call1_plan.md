# Remove Phase 2 “Call 1” (Legacy Short Memory Update) — Implementation Plan

## Objective
Eliminate the legacy Phase 2 memory update that writes results via `participant.update_memory(...)` just before final ranking. Standardize on the MemoryService-based final-results update plus streamlined ranking collection.

## Affected Components
- `core/services/counterfactuals_service.py`
  - Private method `_get_final_ranking_task(...)` (uses `participant.update_memory`)
  - Public APIs remain: `deliver_results_and_update_memory(...)`, `collect_final_rankings_streamlined(...)`, `_get_final_ranking_task_streamlined(...)`
- Tests
  - `tests/unit/test_counterfactuals_service.py` (direct references to `_get_final_ranking_task`)
- Docs/Reports (non-blocking updates)
  - `ranking_prompt_analysis_report.md`, `ranking_redundancy_comprehensive_analysis.md` (reference old path)

## Removal Strategy
- Remove `_get_final_ranking_task(...)` and any production path that triggers `participant.update_memory` for Phase 2 final results.
- Ensure all ranking collection uses `collect_final_rankings_streamlined(...)` → `_get_final_ranking_task_streamlined(...)`, with contexts pre-updated by `deliver_results_and_update_memory(...)`.
- Update tests to call the streamlined API or to prepare contexts as the production flow does.

## Step-by-Step Changes
1) Code deletion (CounterfactualsService)
- Delete method `_get_final_ranking_task(...)` in `core/services/counterfactuals_service.py`.
- Verify no remaining references in code. The production flow in `Phase2Manager` already uses the streamlined path.

2) Test refactors
- Update `tests/unit/test_counterfactuals_service.py`:
  - Replace imports and calls to `_get_final_ranking_task` with either:
    - `collect_final_rankings_streamlined(...)` for end-to-end behavior, or
    - `_get_final_ranking_task_streamlined(...)` if a unit-level granularity is required.
  - Where needed, create minimal preconditions by invoking `deliver_results_and_update_memory(...)` to prepare contexts, or mock contexts with `context.memory` containing final results.

3) Documentation cleanup (optional but recommended)
- Replace references to `_get_final_ranking_task` in:
  - `ranking_prompt_analysis_report.md`
  - `ranking_redundancy_comprehensive_analysis.md`
- Clarify that Phase 2 always updates memory via `MemoryService.update_final_results_memory(...)` before ranking.

4) Logging and monitoring
- Confirm `deliver_results_and_update_memory(...)` includes a debug preview of the results content and logs the MemoryService path. This makes external monitors clearly show a single memory update call for results.

## Validation & Acceptance Criteria
- Repo-wide search shows no references to `_get_final_ranking_task(` or `participant.update_memory(` for Phase 2 results.
- All tests pass: `python run_tests.py` (and focused: `python run_tests.py unit`).
- A Phase 2 run shows exactly two post-discussion operations per agent:
  1) MemoryService final-results update.
  2) Ranking prompt call.
- External monitoring no longer shows the legacy “Call 1”.

## Risks & Mitigations
- Risk: Tests assuming the legacy call fail. Mitigation: Refactor tests as above.
- Risk: External tools depend on legacy call signature. Mitigation: Communicate change and provide release notes; the production path is unchanged (it already uses the streamlined flow).

## Rollback Plan
- Reintroduce `_get_final_ranking_task(...)` as a thin wrapper around the streamlined path (without memory update) if immediate rollback is needed; or temporarily mark it deprecated raising `NotImplementedError` with migration guidance.

## Execution Checklist (Commands)
- Update code and tests
- Run: `python run_tests.py`
- Focus failures in unit tests until green: `python -m unittest tests.unit.test_counterfactuals_service -v`

## Timeline
- Code removal + unit test updates: 1–2 hours
- Documentation cleanup (optional): 30–45 minutes
- Validation runs: 30 minutes
