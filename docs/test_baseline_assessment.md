# Test Suite Baseline Assessment

Date: 2025-09-23

## Suite Inventory Snapshot

| Location | Focus | LLM Calls | Languages Exercised | Runtime Notes | Retention Decision |
| --- | --- | --- | --- | --- | --- |
| `tests/unit/` | Parsing helpers, config validation | Mixed (many mock or patch LLMs) | Primarily English; sporadic Mandarin/Spanish strings | Fast (~seconds) | Keep core logic; rewrite anything using mocks for LLM parsing |
| `tests/component/` | Subsystem flows (prompt harness, Phase managers, Phase2 services) | Mixed: many live agents, some deterministic helpers | English, Spanish, Mandarin | Moderate (per-language runs) | Continue migrating remaining service scenarios; keep assertions structural |
| `tests/integration/` | End-to-end experiment, error recovery | Heavy monkeypatching of `Runner.run` and utility parsers | English dominant; a few Mandarin/Spanish fixtures mocked | Slow (minutes when run fully) | Keep only true E2E flows; migrate service checks to component layer |
| `tests/contracts/` | Snapshot-style regression checks | None (pure file comparisons) | N/A | Fast | Keep; convert to contract snapshots later |
| `tests/performance/` | Scalability, resource usage (threads, psutil) | No | N/A | Very slow (tens of minutes) | Archive; convert to manual/perf playbooks |
| `tests/utils/test_performance_optimization.py` | Tutorial on timing patterns | No | N/A | N/A | Archive (guidance only) |
| `tests/acceptance`, `tests/logging`, `tests/resilience`, `tests/services` | Empty placeholders (`__pycache__` only) | N/A | N/A | N/A | Delete directories |
| `tests/_legacy/` | Old validation fixtures | No | English | N/A | Evaluate in later phase (likely archive) |

## Retention & Rewrite Matrix

- **Keep + modernise**: deterministic unit logic (distribution math, config models, language manager fallbacks), regression fixtures.
- **Rewrite**: Phase1/Phase2 manager tests, integration flows, any test relying on patched `Runner.run` or mock JSON payloads.
- **Archive/Delete now**: `.bak` suites, performance harness, empty directories, tutorial files.

## Runtime Targets & Cadence

- `unit` + `component` (future) should complete in < 2 minutes locally.
- `integration` runs nightly or before release; expect 5–10 minutes with real models across three languages.
- `live` acceptance (stress/multilingual rotations) scheduled weekly; budget 30–40 minutes with cost monitoring.

## Credential & Secrets Policy

- All suites requiring LLM access read `OPENAI_API_KEY` and optional `OPENROUTER_API_KEY` from `.env` (never committed).
- `run_tests.py` must skip LLM-dependent suites gracefully when credentials are absent, emitting actionable warnings.
- Contributors document expected token costs for each live suite; CI jobs enforce per-run cost ceilings via environment configuration.

## Immediate Cleanup Actions (Phases 1–2)

- Remove legacy `.bak` test files under `tests/unit/` and `tests/integration/`.
- Delete empty placeholder directories under `tests/`.
- Archive `tests/performance/` and `tests/utils/test_performance_optimization.py` for reference.
- Introduce `tests/component/` backed by prompt harness pilots; promote `tests/regression/` to `tests/contracts/`.
- Track remaining legacy fixtures (`tests/_legacy/`) for evaluation in later phases.
- Continue migrating Phase 2 scenarios from `tests/integration/` into `tests/component/` (memory, voting, counterfactual coverage now live).

This document will be refreshed as subsequent phases restructure the suite.
