# Phase C Plan — Completing Pytest Migration & Integration Coverage

_Context: Phase A delivered the pytest backbone/acceptance harness, and Phase B added service contracts plus initial resilience coverage. Phase C focuses on closing the remaining gaps so the overall test strategy in `codex_test_system_overhaul.md` is fully realised._

## Legend
- ☐ Not started
- ◐ In progress
- ☑ Completed

## 1. Complete Pytest Migration
- Discovery & Triage
  - ☑ Generate inventory of remaining `unittest.TestCase` suites (`docs/unittest_inventory.md`).
  - ☑ Tag each suite with priority (High: blockers for refactors, Medium: moderate, Low: informational) and note dependencies (fixtures, golden files).
- High-Priority Conversions (target early)
- ☑ `tests/unit/test_cultural_context.py` → convert to pytest, reuse shared fixtures for utility agent/language manager (legacy file archived under `tests/_legacy/`).
- ☑ `tests/unit/test_regional_formats.py` → consolidate repetitive cases using parametrization (evaluate necessity/replace with targeted coverage).
- ☑ `tests/unit/test_translation_validation.py` → switched to pytest with shared language fixtures.
- Medium-Priority Conversions
  - ☐ Parsing/constraint suites (`test_multilingual_parsing.py`, `test_phase2_principle_parsing_multilingual.py`, `test_phase2_ballot_parsing_corrections.py`).
  - ☐ Distribution/config suites (`test_constraint_correction.py`, `test_config_file_logging.py`, `test_voting_history_structures.py`).
  - ☐ Integration flows (`tests/integration/test_multilingual_agent_parsing.py`, `tests/integration/test_mixed_model_experiment.py`).
- Low-Priority/Legacy
  - ☐ Validation letter-rejection archives (decide whether to delete or port selected scenarios).
  - ☐ Performance templates under `tests/_legacy/templates` (confirm archival vs. rewrite).
- Base Class Retirement
  - ☑ Identify remaining references to `tests/test_base.py` and custom async bases (see dependent list below).
  - ☑ Replace with pytest fixtures (`disable_tracing_env`, `stubbed_runner`, `minimal_experiment_config`).
  - ☑ Delete `tests/test_base.py` once no longer needed.
- Documentation & Tracking
  - ☐ Update `codex_phase_a_tasklist.md` as conversions land.
  - ☐ Record migration patterns (common fixture conversions, async refactors) in `docs/testing.md`.

## 2. Structured Prompt/Schema Assertions
- ☐ Expand `tests/utils/prompt_assertions.py` with JSON schema or dataclass comparison helpers.
- ☐ Replace remaining golden prompt/format tests with structural assertions (e.g., `tests/golden/test_memory_service_consistency.py`).
- ☐ Ensure multilingual prompt variants use the new helpers to avoid brittle snapshots.

## 3. Targeted Integration Scenarios
- ☐ Build pytest-based integration tests running Phase 2 with real services, using the stubbed runner and transcripts.
- ☐ Cover multilingual flows (English/Spanish/Mandarin) and verify `ExperimentResults` plus service artefacts (discussion history, vote counts).
- ☐ Document new integration fixtures/utilities in `docs/testing.md`.

## 4. Expanded Resilience Coverage
- ☐ Add reusable fixtures/transcripts for utility agent timeouts, malformed JSON, and language manager failures beyond voting service.
- ☐ Write resilience tests for `Phase1Manager` and `Phase2Manager` covering retries/degenerate scenarios.
- ☐ Update CI/Makefile targets if new markers are introduced.

## Reporting
- ☐ Summarise completed work in `docs/DECISIONS.md` and update `codex_phase_b_tasklist.md` upon completion.

### Test Base Retirement – Dependent Suites
- ☑ `tests/test_multilingual_base.py` (multilingual fixture provider)
- ☑ `tests/performance/test_resource_usage.py`
- ☑ `tests/performance/test_multilingual_scalability.py`
- ☑ `tests/performance/test_multilingual_performance.py`
- ☑ `tests/performance/test_memory_leak_detection.py`
- ☑ `tests/performance/test_performance_regression.py`

_Recent work: performance suites now rely on stubbed `UtilityAgent` helpers and deterministic timing, allowing us to drop `tests/test_base.py` entirely while keeping regression baselines in `tests/performance/baselines.json`._
