# Decision Log

## 2024-09 Testing Overhaul
- **Context:** Legacy test suites relied on unittest inheritance, ad-hoc mocks, and a bespoke runner that duplicated pytest functionality.
- **Decision:** Adopt pytest as the canonical runner, introduce shared fixtures (`tests/conftest.py`), and stub agent/runner interactions to keep tests deterministic and offline.
- **Consequences:**
  - Tests run faster and more reliably in CI with no network dependencies.
  - Developers use `python -m pytest -m "not slow"` (or Makefile shortcuts) instead of `run_tests.py`.
  - Acceptance suites operate with reusable transcripts; legacy `.bak` and template assets are quarantined under `tests/_legacy` until ported or deleted.
  - Future work (Phase B) will focus on service contract tests and resilience scenarios leveraging the same infrastructure.

## 2024-09 Phase B Contracts & Resilience
- **Context:** After stabilising the test harness we required higher-confidence coverage for refactored services and error handling.
- **Decision:** Add dedicated `@pytest.mark.contracts` and `@pytest.mark.resilience` suites covering speaking order, discussion, voting, memory, counterfactual services, and the central error handler.
- **Consequences:**
  - Service behaviour is now validated with deterministic inputs and logging assertions.
  - CI executes the new suites alongside acceptance tests, giving early signal on regressions.
  - Remaining follow-ups include counterfactual edge cases, structured prompt validation, and targeted integration flows (tracked in `codex_phase_b_tasklist.md`).

## 2025-09 Resilience & Tracing Enhancements
- **Context:** Phase B tasks expanded to cover manager-level resilience, experiment tracing metadata, and deterministic performance harnesses.
- **Decision:** Introduce shared failure fixtures (`tests/resilience/conftest.py`), add manager-focused resilience tests, patch the experiment manager to run under pytest with stubbed agents, and convert performance suites to offline/deterministic heuristics.
- **Consequences:**
  - Phase 1/Phase 2 managers now have regression tests for constraint retries and translation fallbacks.
  - Experiment tracing metadata (participant roster, language, experiment id) is validated in `tests/logging/test_experiment_tracing.py` without live network calls.
  - Performance and memory-leak regressions rely on fixtures and baselines that run in under a minute, keeping CI reliable.
