# Testing Transformation Plan

This plan sequences the work required to simplify the testing stack, retire fallbacks, and converge on a focused, pytest-first suite with explicit live coverage controls. Each stage lists objectives, concrete tasks, ownership suggestions, and exit criteria. Use a feature branch (e.g., `test-overhaul/<phase>`) per stage to keep the migration manageable.

## Guiding Principles
- **Pytest everywhere**: no `unittest` discovery, no manual async loops. All suites and fixtures use pytest idioms.
- **Single entry point**: contributors run `pytest` (plus optional flags) directly. Additional tooling (tox/nox, CI scripts) wraps pytest without reinventing logic.
- **Explicit live controls**: live/API-heavy suites exist but are triggered via pytest markers/CLI switches instead of environment gymnastics.
- **Tests live in `tests/`**: supporting scripts either join the tree as proper pytest modules or move into `docs/` for reference.
- **Deterministic fast feedback**: every pull request runs fast, deterministic suites by default; live coverage runs on demand or on a schedule.

---

## Phase 0 – Preparation & Communication
- **Objective**: baseline current suite behaviour and align contributors on upcoming changes.
- **Tasks**
  - Capture current pytest invocation patterns, runtime, and flake points (docs already drafted in `testing_infrastructure_status.md`).
  - Announce scope in `docs/contributing/testing.rst` and internal channels; collect constraints from stakeholders owning live suites.
  - Tag existing long-running or flaky tests with `@pytest.mark.slow` / `@pytest.mark.live` to aid triage.
- **Exit Criteria**
  - Shared understanding documented in `docs/` with sign-off from maintainers.
  - Slow/live markers present on all expensive suites.
- **Status**: Completed (pytest baseline snapshot and slow/live tagging captured in Oct 2024)

---

## Phase 1 – Eliminate Legacy Runners & Fallbacks
- **Objective**: make pytest the only runner; remove `unittest` discovery and env-based defaults baked into `run_tests.py`.
- **Tasks**
  1. Replace `run_tests.py` with either:
     - A minimal shim that forwards arguments to pytest, or
     - Documentation for direct `pytest` usage, deleting the script entirely.
  2. Remove fallback branch invoking `unittest.discover` (`run_tests.py:135-154`).
  3. Port execution modes (`ultra_fast`, `dev`, etc.) into pytest CLI options or tox envs:
     - Implement `pytest_addoption` in `tests/conftest.py` to parse `--mode` or explicit `--languages` / `--skip-expensive`.
     - Update docs to reflect the new invocation style.
  4. Delete JSON language-report enforcement from `run_tests.py`; prepare pytest plugin equivalent (phase 4).
- **Ownership**: Testing infra maintainer.
- **Exit Criteria**
  - CI and local workflows invoke pytest directly.
  - No code path uses `unittest` discovery.
  - Modes/env defaults handled via pytest options.
- **Status**: Completed (run_tests.py shim and pytest `--mode` option landed in Oct 2024)

---

## Phase 2 – Standardise Test Style & Fixtures
- **Objective**: convert all suites to idiomatic pytest and centralise tracing/env setup.
- **Tasks**
  1. Rewrite `tests/test_base.py` logic as pytest fixtures:
     - Move tracing disablement to `pytest_configure` or session fixture.
     - Delete the `TracingDisabledTestCase` and `AsyncTracingDisabledTestCase` bases.
  2. Port `unittest.TestCase` modules to pytest functions/classes (`tests/unit`, portions of `tests/integration`).
  3. Replace `asyncio.run` blocks with `pytest.mark.asyncio` and fixture-based event loop usage.
  4. Audit fixture scopes; convert repeated setup/teardown into fixtures in `tests/conftest.py` or dedicated factory modules.
  5. Replace remaining synchronous wrappers that call `asyncio.run` in snapshot suites (e.g., `tests/snapshots/golden/test_memory_service_consistency.py`) with pytest-asyncio tests or helper fixtures.
- **Ownership**: Module owners per directory with infra lead guidance.
- **Exit Criteria**
  - No test imports `unittest`.
  - Async tests rely on pytest async features.
  - Tracing/env setup comes from fixtures, not base classes.
- **Status**: Completed (Jan 2025) – pytest fixtures handle tracing, all tests rely on pytest-asyncio, and snapshot contracts no longer call `asyncio.run` (`tests/snapshots/golden/test_memory_service_consistency.py`).

---

## Phase 3 – Restructure Suite Layout & Remove Stray Scripts
- **Objective**: ensure every executable test lives under `tests/` and clarify suite boundaries.
- **Tasks**
  1. ✅ Remove or relocate top-level helper scripts (parallel execution, Gemini integration, semantic mapping demos).
 2. ✅ Introduce shared snapshot helpers for `tests/snapshots/` (on-disk baselines) so regression suites are easier to refresh without external plugins.
  3. ✅ Fold the fast feedback tests into `tests/unit/test_fast_*` and retire the separate directory.
  4. Review `tests/support/`, `tests/fixtures/`, `tests/templates/` for redundancy, moving docs/templates into `docs/` if unused by pytest.
- **Ownership**: Test content owners with infra oversight.
- **Exit Criteria**
  - Root-level `test_*.py` scripts removed or relocated.
  - Snapshot suites consolidated with shared fixtures and supported by reusable tooling.
- **Status**: Completed (Jan 2025) – snapshot suites now rely on `LanguageManager` to load real translation assets, manual dictionaries are gone, and remaining redundancy reviews for templates/support are tracked separately.

---

## Phase 4 – Simplify Live & Language Controls
- **Objective**: replace environment-variable driven behaviour with explicit pytest options and markers.
- **Tasks**
  1. ✅ Introduce pytest options (in `conftest.py`) for:
     - `--languages` (comma-separated, default `en`),
     - `--run-live` / `--no-run-live` to toggle live API calls,
     - `--skip-expensive` / `--no-skip-expensive` to control expensive suites.
  2. ✅ Update language parametrisation helpers (`tests/support/language_matrix.py`) to consume these options rather than legacy env vars.
  3. ✅ Rewrite skip logic in `pytest_collection_modifyitems` to use option flags.
  4. ✅ Document usage in `README.md` / contributor docs.
  5. Review CI pipelines to pass appropriate flags for PR vs scheduled runs.
- **Ownership**: Testing infra maintainer.
- **Exit Criteria**
  - No tests read legacy env knobs.
  - Running `pytest` without flags executes fast, deterministic suites (unit + non-live component snapshots).
  - `pytest --run-live --languages=en,es,zh` re-enables live multilingual coverage.
- **Status**: Completed (Nov 2024) - CLI options now drive execution; legacy env toggles are ignored for live/expensive/language selection.

---

## Phase 5 – Live Suite Rationalisation
- **Objective**: Keep live coverage but limit it to targeted, opt-in tests.
- **Tasks**
  1. Catalogue all live tests (`pytest.mark.live`); classify into:
     - Essential smoke (keep),
     - Redundant/duplicated coverage (refactor or remove).
  2. For essential live suites:
     - Ensure they respect `--run-live`.
     - Compose them to use minimal agent counts / rounds unless full runs are indispensable.
  3. Provide snapshot or mocked equivalents for CI runs where possible.
  4. Schedule nightly/weekly job running `pytest --run-live --languages=en,es,zh`.
- **Ownership**: Feature owners for live functionality plus infra team.
- **Exit Criteria**
  - Live tests run only when `--run-live` set.
  - Live suite list documented with purpose and expected runtime.
  - CI executes live suites on agreed cadence; PR pipeline runs fast subsets.
- **Status**: In progress - live suites are catalogued with recommended nightly/weekly cadence (`testing_infrastructure_status.md`), yet mocked CI equivalents and automation for the schedule still need implementation.

---

## Phase 6 – Snapshot & Contract Modernisation
- **Objective**: ensure regression suites are maintainable and aligned with production assets.
- **Tasks**
  1. Adopt a reproducible snapshot mechanism (shared helpers writing on-disk baselines); convert manual JSON/text comparisons in `tests/snapshots/`.
  2. Create snapshot fixtures for critical outputs:
     - Phase 2 prompts,
     - Memory transcripts,
     - Translation keys.
  3. Align snapshot data with production sources (no handcrafted translations in tests).
  4. Document snapshot refresh workflow (helper script or documented regeneration commands).
- **Ownership**: Contract/golden test maintainers with infra support.
- **Exit Criteria**
  - Snapshot tests share tooling and documentation.
  - No duplicated translation dictionaries in test code.
  - Snapshot update process documented and reviewed.
- **Status**: In progress - snapshots now pull from real translation assets via shared helpers, but we still need to document the manual update workflow and consolidate the remaining template/support utilities.

---

## Phase 7 – Coverage & Telemetry Cleanup
- **Objective**: provide clear coverage reporting without bespoke JSON plumbing.
- **Tasks**
  1. Decide whether multilingual execution coverage is still required; if yes, reimplement as a pytest plugin emitting structured output or hooking into pytest reports.
  2. Update `pytest.ini` to reflect final directory structure and coverage behaviour (include/exclude rules).
  3. Integrate coverage thresholds into CI (e.g., `pytest --cov --cov-fail-under=XX`).
  4. Remove ad-hoc language coverage JSON generation from codebase.
- **Ownership**: Infra team.
- **Exit Criteria**
  - Coverage reports generated via pytest-cov only.
  - Language coverage decisions documented (plugin or retired).
  - CI enforces agreed coverage thresholds.
- **Status**: Not started - pytest-cov remains opt-in, the language coverage JSON written by `tests/conftest.py:352-379` still lacks a consumer, and thresholds/automation need to be defined.

---

## Phase 8 – Documentation & Onboarding
- **Objective**: ensure contributors fully understand the new testing workflow.
- **Tasks**
  1. Update `README.md` and `docs/` sections:
     - Running fast suites vs live suites.
     - Available pytest options and markers.
     - Snapshot update procedure.
  2. Refresh templates in `tests/templates/` to reflect pytest style (or remove if unused).
  3. Record short Loom/Screencast or CLI transcript demonstrating new workflow (optional but helpful).
  4. Audit existing docs (e.g., `docs/component_suite_acceleration_plan.md`) and reconcile with new structure.
- **Ownership**: Docs owner with infra input.
- **Exit Criteria**
  - Documentation references only the new workflow.
  - Templates and examples match the final style.
  - Onboarding checklists updated.
- **Status**: In progress - README.md and several guides cover `--mode` usage, yet pieces like `tests/templates/` and onboarding checklists still mirror pre-migration workflows and require updates; snapshot helper docs also need to be added.

---

## Phase 9 – Cleanup & Retrospective
- **Objective**: finish remaining polish and capture lessons learned.
- **Tasks**
  1. Remove deprecated env variables, helper functions, and unused factories uncovered during migration.
  2. Ensure tests follow a consistent naming convention (`test_<module>.py`).
  3. Run repository-wide lint/format to stabilise style.
  4. Host a retrospective: capture what went well, what to monitor, and any future enhancements (e.g., property-based tests, fuzzing).
- **Ownership**: Infra team with contributor feedback.
- **Exit Criteria**
  - Codebase free of obsolete test utilities.
  - Consistent test naming/style enforced.
  - Retrospective notes stored under `docs/` or `reports/`.
- **Status**: Not started - cleanup sweeps, naming enforcement, and the retrospective documentation are still outstanding.

---

## Deliverables Summary
| Phase | Deliverable |
| --- | --- |
| 0 | Communication plan, slow/live markers |
| 1 | Pytest-only runner, updated CLI usage |
| 2 | Pytest-native tests/fixtures |
| 3 | Clean suite layout, no stray scripts |
| 4 | Pytest options controlling languages/live |
| 5 | Curated live suites with opt-in |
| 6 | Unified snapshot tooling |
| 7 | Simplified coverage reporting |
| 8 | Updated documentation & templates |
| 9 | Final cleanup & retrospective |

Executing the phases sequentially (with limited overlap where sensible) will transform the current complex infrastructure into a focused, efficient testing system that matches the desired simplicity and maintains critical coverage.
