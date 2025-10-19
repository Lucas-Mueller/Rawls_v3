# Testing Infrastructure Status Review

## Executive Summary
- Pytest is now the sole runner; `run_tests.py` (run_tests.py:1-68) simply forwards `--mode` and `--coverage` to `python -m pytest`, while contributors interact with pytest directly.
- Test suites are consolidated under `tests/` with markers auto-applied in `tests/conftest.py:83-181`. Unit, component, integration, and snapshot layers are separated, and snapshot suites now read golden baselines from disk via lightweight helpers (no external pytest plugins required).
- Live coverage remains opt-in: `--run-live` combines with `@pytest.mark.live` to guard network-heavy suites such as `tests/component/test_phase2_manager_live.py:1-109`, yet meaningful component and integration coverage still depends on OpenAI credentials.
- Remaining friction centers on keeping workflow documentation aligned across README, `docs/TEST_ACCELERATION_GUIDE.md`, and onboarding templates, plus ensuring live-suite scheduling guidance is reflected in CI automation.

## Tooling & Execution Flow
- **Primary harness** – `run_tests.py` (run_tests.py:1-68) builds the pytest command and no longer contains any unittest discovery fallback.
- **CLI & marker wiring** – `tests/conftest.py:83-214` registers `--mode`, `--run-live`, `--skip-expensive`, and language options, disables tracing globally, and injects layer markers so discovery aligns with directory layout.
- **pytest configuration** – `pytest.ini:1-28` enables asyncio auto mode, enforces strict markers, and excludes `tests/**` from coverage. `tests/conftest.py:260-334` handles skip logic and language bookkeeping, while `tests/conftest.py:352-379` optionally writes language coverage JSON when `LANGUAGE_REPORT_PATH` is set.

## Suite Layout & Intent
- `tests/unit/` focuses on deterministic logic, configuration parsing, seed management, and memory helpers; the fast smoke suites live alongside the rest of the directory (`tests/unit/test_fast_*`).
- `tests/component/` drives multi-agent flows through the prompt harness (`tests/component/test_reasoning_and_temperature.py:1-64`, `tests/component/test_phase2_manager_live.py:1-109`) and requires real API access for assertions.
- `tests/integration/` verifies experiment orchestration and CLI behaviour with pytest functions (`tests/integration/test_experiment_reproducibility.py:1-120`, `tests/integration/test_cli_live.py:1-72`) instead of unittest classes.
- `tests/snapshots/` consolidates contract and golden suites using on-disk baselines; translation data now flows through real `LanguageManager` instances so snapshots track production assets.
- Supporting assets live in `tests/fixtures/`, `tests/support/`, `tests/templates/`, and `tests/utils/`; `tests/test_multilingual_base.py` documents best practices for forthcoming multilingual suites.

## Fixtures, Helpers, and Language Instrumentation
- `tests/conftest.py:184-270` defines session-level fixtures for credential gating, prompt harness creation, and automatic skip/marker behaviour tied to `--mode` and expense flags.
- Language selection flows through `tests/support/language_matrix.py:1-150`, which consumes pytest options to expose helpers like `parametrize_languages` and `smart_parametrize_languages`.
- Prompt harness utilities (`tests/support/prompt_harness.py`, `tests/support/config_factory.py`) clone experiment configurations and coordinate seeds so live tests remain reproducible.

## Environment & External Dependencies
- Live suites require `OPENAI_API_KEY` (and optionally `OPENROUTER_API_KEY`, `GEMINI_API_KEY`); `openai_api_key` performs an HTTP probe before enabling tests.
- Default `--mode` presets skip live and expensive suites unless contributors pass `--run-live`; credentials alone no longer trigger legacy environment behaviour.
- Integration fixtures read real YAML specs (`config/default_config.yaml`, `config/test_ultra_fast.yaml`), and some tests create temporary configs on disk (`tests/integration/test_cli_live.py:24-55`).

## Live Suite Catalogue & Scheduling
- **Historical runtimes** below draw from the Oct 2024 Apple M3 Pro baseline noted in `docs/testing_baseline.md`. A full `pytest tests/component -m "component and live"` run averaged ~13 minutes for English-only execution (~150 OpenAI calls).
- The table summarises currently collected live suites; runtimes are coarse buckets derived from observed call counts and fixture complexity. All suites respect `--run-live` and the language selectors exposed in `tests/conftest.py`.

| Module | Scope | Languages under default run | Runtime bucket (EN) | Suggested cadence |
| --- | --- | --- | --- | --- |
| `tests/component/test_phase1_manager_live.py` | Phase 1 orchestration smoke | primary (`en`) | Medium (~2-4 min) | Nightly (`pytest --mode=full --run-live --languages=en`) |
| `tests/component/test_phase2_manager_live.py` | Full Phase 2 loop with three agents | primary (`en`) | Long (5-7 min) | Nightly (`--languages=en`), Weekly multilingual (`--languages=en,es,zh`) |
| `tests/component/test_phase2_mixed_languages_live.py` | Multilingual harness validation | smart matrix (en + secondary) | Long (6-8 min) | Weekly multilingual run |
| `tests/component/test_reasoning_and_temperature.py` | Reasoning toggles & temperature probes | smart matrix | Medium (~3-4 min) | Nightly (`--languages=en`), Weekly multilingual |
| `tests/component/test_voting_service_live.py` | Voting workflow contract | smart matrix | Medium (~2-3 min) | Nightly (`--languages=en`) |
| `tests/component/test_memory_service_live.py` | Memory updates via live agents | smart matrix | Medium (~2-3 min) | Nightly (`--languages=en`) |
| `tests/component/test_manipulator_service_live.py` | Manipulator detection guardrails | smart matrix | Medium (~2-3 min) | Nightly (`--languages=en`) |
| `tests/component/test_counterfactuals_service_live.py` | Counterfactual generation sanity checks | primary (`en`) | Short (<2 min) | Nightly |
| `tests/component/test_language_logging_live.py` | Language logging instrumentation | smart matrix | Short (<2 min) | Nightly |
| `tests/component/test_prompt_harness_agents.py` | Prompt harness integration | smart matrix | Medium (~2-3 min) | Nightly |
| `tests/component/test_utility_agent_parsing_live.py` | Utility agent parsing fidelity | smart matrix | Medium (~3-4 min) | Nightly |
| `tests/component/test_consensus_mechanisms.py` | Consensus and escalation paths | smart matrix | Medium (~3-4 min) | Nightly |
| `tests/integration/test_cli_live.py` | CLI smoke via subprocess | primary (`en`) | Medium (~4 min) | Nightly (`pytest --mode=full --run-live --languages=en`) |

- **Scheduling recommendation**
  - **Nightly**: `pytest --mode=full --run-live --languages=en -m "live"` to cover all suites in the table using the primary language only.
  - **Weekly (e.g., Sunday 02:00 UTC)**: `pytest --mode=full --run-live --languages=en,es,zh -m "live"` to refresh multilingual coverage.
  - Capture runtimes in CI logs and update this table quarterly to keep estimates current.

## Coverage & Reporting Posture
- Coverage excludes all test modules and helper scripts (`pytest.ini:17-28`); contributors opt in to reports via `pytest --cov`.
- When `LANGUAGE_REPORT_PATH` is populated, `tests/conftest.py:352-379` writes a multilingual coverage summary, but no automated consumer currently ingests the JSON.

## Pain Points & Outstanding Work
- Snapshot suites rely on LanguageManager lookups for translation content; remaining follow-up is to keep baselines regenerated when translation assets change and to document the manual snapshot helper workflow.
- Live suite catalogue and cadence are documented, yet CI still needs dedicated jobs that run the nightly and weekly commands.
- Guidance on combining `--mode`, language overrides, and live toggles is spread across README.md, `docs/TEST_ACCELERATION_GUIDE.md`, and templates, making onboarding heavier than necessary.

## Adequacy & Coverage Observations
- Unit and fast suites provide healthy deterministic coverage (`tests/unit/test_memory_manager.py`, `tests/unit/test_fast_*`), but there is no offline component smoke test for the prompt harness.
- Integration reproducibility tests stop short of real agent execution without credentials (`tests/integration/test_experiment_reproducibility.py:87-118`), so seed semantics rely on manual live runs.
- Snapshot coverage now flows through on-disk baselines driven by LanguageManager outputs; remaining work is to keep fixtures synchronized with translation updates and document the regeneration process.

## Ancillary Assets
- Templates in `tests/templates/` and the reference module `tests/test_multilingual_base.py` encode process knowledge but are not cross-linked from README or contributor docs.
- Historical transcripts (`transcripts/`, `transcript_*.json`) provide manual context for prior experiments but remain outside automated regression flows.

---
This snapshot reflects the post–phase 4 state of the testing overhaul. Upcoming work will focus on rationalising live coverage, modernising snapshot data, formalising coverage reporting, and tightening contributor guidance.
