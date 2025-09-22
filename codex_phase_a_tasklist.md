# Phase A Implementation Plan

## Legend
- ☐ Not started
- ◐ In progress
- ☑ Completed

## 1. Pytest Standardization
- ☑ Inventory all `unittest.TestCase` subclasses and prioritise migration order (tracking doc living in this checklist).
- ◐ Draft migration guides for common patterns (outline pending in docs).
- ☑ Convert the highest risk suites (parsing, memory, voting) to pytest style using new fixtures.
- ◐ Update remaining suites iteratively; track progress in this checklist.
- ◐ Replace custom base classes with shared fixtures; delete the bases once no suites depend on them.
- ☑ Update docs/README to promote `pytest` commands and note the deprecation timeline for `run_tests.py`.

## 2. Foundational Fixtures (`tests/conftest.py`)
- ☑ Introduce `tests/conftest.py` with:
  - seeded randomness fixture (`seed_rng`, auto-use)
  - tracing disable autouse fixture (`disable_tracing_env`)
  - deterministic stub runner fixture (`stubbed_runner`)
- ☑ Extract reusable transcript/script helpers into `tests/utils/stub_scripts.py` and document expected structure.
- ☑ Backfill unit tests for the `StubbedRunner` to lock behaviour (exhaustion, agent-specific queues, defaults).
- ◐ Sweep existing suites for ad-hoc stubs and switch them to the shared fixtures.
- ☑ Add optional fixtures for common config objects (e.g., minimal experiment config) to reduce duplication.

## 3. Acceptance Test Scaffolding
- ☑ Implement a stub-backed acceptance test that awaits `FrohlichExperimentManager.run_complete_experiment` and asserts against `ExperimentResults` structure.
- ☑ Create `tests/data/acceptance/` with reusable transcript YAML/JSON fixtures for common scenarios (consensus, deadlock, error recovery).
- ☑ Expand acceptance coverage to include multi-round discussion and memory updates using scripted responses.
- ☑ Configure parametrised acceptance tests to validate multiple language settings.
- ☑ Add pytest marker `acceptance` and mention it in docs/testing.md.
- ☑ Integrate acceptance suite into CI once deterministic.

## 4. Legacy Suite Cleanup
- ◐ Catalogue legacy artefacts (performance scripts, golden prompt suites) and migrate or rewrite as needed (initial relocation to `tests/_legacy/` complete; review outstanding performance/golden suites).
- ☐ Create structured assertion helpers for prompts (e.g., compare JSON schema, key presence) and refactor golden tests to use them.
- ☐ Remove duplicate/overlapping suites once new contract tests are in place.
- ☑ Update fixtures to stop importing module-level globals (e.g., `ExperimentTestFixture`) and rely on pytest fixtures instead.
- ☑ Ensure relocated legacy assets are excluded from default pytest discovery via `pytest.ini` or conftest hooks.

## 5. Developer Enablement
- ☑ Create `requirements-dev.txt` enumerating test-only dependencies (pytest, pytest-asyncio, pytest-cov, psutil, memory-profiler, etc.).
- ☑ Define a `Makefile` or `noxfile.py` with shortcuts (`test`, `test-acceptance`, `lint`) wired to the new pytest flow.
- ☑ Author `docs/testing.md` (or update README) describing new fixtures, stub runner usage, and suite invocation patterns.
- ☑ Update onboarding docs to reference the acceptance suite and fixture usage.
- ☑ Add a decision log entry explaining the move to pytest and stubbed infrastructure.

## 6. Verification & Tooling
- ☑ Configure CI workflow (GitHub Actions or equivalent) that installs `requirements-dev.txt`, runs `pytest -m "not slow"`, and uploads coverage.
- ☑ Add optional nightly/weekly job for `pytest -m acceptance` and `pytest -m slow` if needed.
- ◐ Ensure local pre-commit or invoke scripts run the acceptance smoke test before release branches (documented in `docs/testing.md`).
- ☑ Record open items for Phase B (service contracts, error resilience) after each milestone review (`codex_phase_b_tasklist.md`).
