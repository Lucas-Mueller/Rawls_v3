# Testing Baseline Snapshot

This note captures the current (pre-migration) behaviour of the Frohlich testing stack so contributors have a shared point of reference before the overhaul begins.

## Invocation Patterns
- Primary command: `pytest` executed from repo root. `run_tests.py` now forwards `--mode` and `--coverage` flags directly to pytest for backward compatibility.
- Expensive suites require the following setup when invoked via pytest:
  - `OPENAI_API_KEY` (and optionally `OPENROUTER_API_KEY`, `GEMINI_API_KEY`) to enable live component/integration layers.
  - CLI toggles such as `--languages`, `--run-live`, and `--skip-expensive` now control multilingual breadth and expensive suites (environment overrides are optional).

## Runtime Characteristics (local baseline, Apple M3 Pro, Oct 2024)
| Suite | Command | Runtime | Notes |
| --- | --- | --- | --- |
| Unit + fast | `pytest tests/unit/test_fast_*` | ~3.5 min | Deterministic, heavy mocking. |
| Component (English only) | `pytest tests/component -m "component and live"` | ~13 min | ~150 OpenAI calls. |
| Integration CLI smoke | `pytest tests/integration/test_cli_live.py` | ~4 min | Spawns full experiment via subprocess. |
| Snapshots | `pytest tests/snapshots` | ~2 min | Snapshot assertions only. |

> Runtimes include existing network latency; expect variance based on OpenAI backlog and rate limits.

## Slow / Live Tests
- All component live suites (`tests/component/*_live.py`) and the CLI smoke have been tagged with both `@pytest.mark.live` and `@pytest.mark.slow`.
- These marks allow contributors to exclude them via `-m "not live and not slow"` until the migration introduces explicit CLI switches.

## Known Pain Points
- Fast tests now live alongside the main unit suite (`tests/unit/test_fast_*`), so contributors must rely on naming conventions or markers to select them quickly.
- Snapshot suites under `tests/snapshots/` still rely on handcrafted expectations instead of a shared snapshot plugin, making updates manual.
- Live and multilingual coverage now offer explicit pytest toggles (`--run-live`, `--languages`), but legacy environment variables remain for backward compatibility and can still cause surprises.

Maintaining this baseline during the transformation ensures we can measure improvements in runtime, cost, and contributor ergonomics as each phase completes.
