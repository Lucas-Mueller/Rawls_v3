# Test System Review

## Current State Overview
- **Entry Points**: `run_tests.py` orchestrates unit, integration, and regression suites, running a bespoke import smoke test before dispatching to either `pytest` or the legacy `unittest` discovery fallback. Coverage flags only work when pytest is present.
- **Framework Usage**: Majority of unit/integration suites inherit from custom `unittest.TestCase` bases (`tests/test_base.py`, `tests/test_multilingual_base.py`) while selectively mixing pytest features (`pytest.skip`, tmp_path fixtures, markers). Several async tests wrap `asyncio.run` manually instead of using pytest-asyncio or `IsolatedAsyncioTestCase`.
- **Suite Layout**: `tests/` contains intermingled categories (`unit`, `integration`, `regression`, `performance`, `validation`, `golden`, `utils`, `templates`). Numerous artifacts (`*.bak`, templates, report generators) live alongside executable tests and blur responsibility boundaries.
- **Support Infrastructure**: Heavy fixture modules (e.g., `tests/fixtures/phase2_parsing_fixtures.py`) expose multilingual datasets. Async base classes provide caching, parity checks, and tracing suppression logic, creating sizable inheritance chains. Performance suites pull optional deps (`psutil`, `memory_profiler`, plotting libs) and emit reports under `tests/performance/`.
- **Automation & Tooling**: `pytest.ini` enables asyncio auto-mode and marker strictness, yet marker usage is inconsistent. Coverage config omits tests by default but the runner requests `--cov=.` for entire repo. No evidence of CI wiring inside repo; tests write artifacts locally and expect mutable state.

## Key Issues & Risks
| Severity | Category | Finding |
| --- | --- | --- |
| High | Framework drift | Hybrid pytest/unittest patterns cause brittle async handling (`asyncio.run` inside synchronous tests), prevent fixture reuse, and induce duplicated base logic.
| High | Test execution | `run_tests.py` reimplements functionality already handled by pytest, adds slow import smoke test, and obscures failure output. Coverage flagging is unreliable without pytest.
| High | Suite hygiene | Legacy files (`*.bak`, templates masquerading as tests, report generators in `tests/`) inflate discovery time and make signal-to-noise low. Some tests (e.g., `tests/performance`) generate files and require optional dependencies, breaking default runs.
| Medium | Data management | Fixture modules cache large language datasets with global state, risking cross-test pollution and high cognitive load for contributors.
| Medium | Assertions quality | Several tests log custom result lists or rely on threshold heuristics instead of precise assertions, weakening regression guarantees.
| Medium | Marker discipline | Pytest markers defined in `pytest.ini` are rarely applied; suite selection relies on directory layout rather than marker expressions, hindering targeted runs.
| Low | Environment setup | Tracing disablement is reasserted in every test via custom base classes; this could move to fixtures or pytest `autouse` hooks for clarity.

## Systematic Improvement Plan

### Phase 1: Stabilize Execution Path
1. Standardize on pytest as the primary runner; document `python -m pytest` entry point and retire unittest discovery fallbacks.
2. Replace `run_tests.py` with a thin wrapper (or remove entirely) that delegates to pytest, optionally supporting coverage via env vars or tox/nox session.
3. Introduce a minimal `poetry`/`pip` extra or `requirements-dev.txt` capturing test-time dependencies (pytest-asyncio, pytest-cov, psutil, etc.) so installs are deterministic.
4. Add a GitHub Actions (or equivalent) workflow that runs unit + integration targets with markers and reports coverage.

### Phase 2: Clean Up the Suite Layout
1. Quarantine non-test assets (`templates`, report generators, analysis scripts) under `tests/_legacy/` or `tools/` to keep discovery paths clean.
2. Delete or archive `*.bak` modules; confirm history in VCS before removal.
3. Move golden artifacts and fixtures to `tests/fixtures/` or `tests/data/` and load them via helper utilities to avoid import-time side effects.
4. Enforce `tests/unit`, `tests/integration`, `tests/regression`, `tests/performance` directories to contain only executable tests; add `__init__.py` only where required.

### Phase 3: Modernize Test Authoring Patterns
1. Refactor async tests to use pytest-asyncio (`@pytest.mark.asyncio`) or `async` fixtures; remove manual `asyncio.run` usage.
2. Convert base classes like `AsyncMultilingualTestBase` into composable pytest fixtures; move tracing disablement into a session-scoped fixture.
3. Replace custom result logging inside tests (e.g., `test_result` collectors) with direct assertions and, where necessary, parametrized pytest tests.
4. Introduce helper fixtures/factories for multilingual datasets instead of large static caches; ensure each test receives isolated copies to prevent cross-test mutation.
5. Annotate suites with markers (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.) to align with `pytest.ini` expectations and ease targeted runs.

### Phase 4: Improve Coverage & Regression Signals
1. Establish a baseline coverage threshold (e.g., 75%) enforced via `pytest --cov --cov-fail-under`.
2. Audit regression/performance suites and decide which belong in CI vs. manual profiling. Extract heavy performance monitoring into standalone scripts invoked via dedicated make/poetry tasks.
3. Add representative unit tests for critical modules currently lacking coverage (e.g., core distribution helpers, config loaders) to reduce reliance on broad integration flows.
4. Document expected data fixtures and add schema validation to catch drift early.

### Phase 5: Document & Maintain
1. Update `README.md` / `docs/` with new testing instructions, dependency setup, and suite expectations.
2. Provide contributor guidelines that describe how to add tests, when to use integration vs. regression suites, and how to run selective checks locally.
3. Schedule periodic test hygiene reviews (quarterly) to prune deprecated suites and ensure fixtures remain representative.

## Immediate Action Checklist
- [ ] Decide on pytest standardization and install missing plugins (`pytest-asyncio`, `pytest-cov`).
- [ ] Create `requirements-dev.txt` (or similar) with test-only dependencies.
- [ ] Remove `.bak` files and relocate templates/scripts out of discovery paths.
- [ ] Refactor a pilot module (e.g., `tests/unit/test_memory_manager.py`) to pytest async style and use fixtures.
- [ ] Configure CI pipeline to run `pytest -m "unit or integration"` and report coverage.
- [ ] Document new workflow in repository docs.

## Observed Quick Wins
- Move tracing disable toggles into a pytest `conftest.py` with `autouse` fixture for clarity.
- Replace manual `sys.path` manipulation in integration tests with relative imports or packaging configuration.
- Gate performance/report-generation tests behind `pytest.mark.slow` and exclude by default.
- Introduce `tests/conftest.py` to centralize multilingual fixture provisioning and reduce duplication across suites.

## Residual Risks
- Performance suites depend on optional native libraries; ensure CI either installs them or skips gracefully via markers.
- Large fixture refactors may invalidate cached expectations (golden files); plan for staggered migration to avoid blocking feature work.
- Converting base classes to fixtures requires careful sequencing to avoid outages in ongoing experiments; schedule work in parallel branches with thorough review.
