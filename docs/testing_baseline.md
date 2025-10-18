# Testing Baseline Snapshot

This note captures the current (pre-migration) behaviour of the Frohlich testing stack so contributors have a shared point of reference before the overhaul begins.

## Invocation Patterns
- Primary command: `pytest` executed from repo root. `run_tests.py` now forwards `--mode` and `--coverage` flags directly to pytest for backward compatibility.
- Expensive suites require the following environment state when invoked via pytest:
  - `OPENAI_API_KEY` (and optionally `OPENROUTER_API_KEY`, `GEMINI_API_KEY`) for live component/integration layers.
  - `LIVE_LANGUAGES`, `DEVELOPMENT_MODE`, `SKIP_EXPENSIVE_TESTS`, `TEST_CONFIG_OVERRIDE` control multilingual breadth and config overrides.

## Runtime Characteristics (local baseline, Apple M3 Pro, Oct 2024)
| Suite | Command | Runtime | Notes |
| --- | --- | --- | --- |
| Unit + fast | `pytest tests/unit tests/fast` | ~3.5 min | Deterministic, heavy mocking. |
| Component (English only) | `pytest tests/component -m "component and live"` | ~13 min | ~150 OpenAI calls. |
| Integration CLI smoke | `pytest tests/integration/test_cli_live.py` | ~4 min | Spawns full experiment via subprocess. |
| Contracts/Golden | `pytest tests/contracts tests/golden` | ~2 min | Snapshot assertions only. |

> Runtimes include existing network latency; expect variance based on OpenAI backlog and rate limits.

## Slow / Live Tests
- All component live suites (`tests/component/*_live.py`) and the CLI smoke have been tagged with both `@pytest.mark.live` and `@pytest.mark.slow`.
- These marks allow contributors to exclude them via `-m "not live and not slow"` until the migration introduces explicit CLI switches.

## Known Pain Points
- Mixed `unittest`/pytest usage (`tests/test_base.py`, multiple unit modules) complicates async handling.
- Environment-variable driven behaviour frequently surprises newcomers; pytest options will replace these controls in Phase 4.
- Root-level scripts (`test_parallel_execution.py`, `test_gemini_integration.py`, `test_semantic_mapping_fix.py`) are not part of pytest discovery and will be migrated or deleted in Phase 3.

Maintaining this baseline during the transformation ensures we can measure improvements in runtime, cost, and contributor ergonomics as each phase completes.
