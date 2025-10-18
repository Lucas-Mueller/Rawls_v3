# Testing Infrastructure Status Review

## Executive Summary
- The project now leans on pytest with a thin compatibility shim (`run_tests.py`) yet still mixes fast mocked layers with expensive live-agent verification. Environment toggles and multilingual guarantees continue to introduce operational overhead (`tests/conftest.py:56`).
- Test sources span nine directories plus several standalone scripts. Suite intent is clear (unit vs component vs integration vs contracts), yet execution paths, fixtures, and env flags differ per layer, raising the activation energy for contributors.
- Many “tests” are actually interactive scripts or research notebooks in disguise (for example `test_parallel_execution.py:78` and `test_semantic_mapping_fix.py:1`), so they never run under pytest and in some cases do not parse.
- Legacy unittest-style cases coexist with pytest idioms. Async coverage often relies on `asyncio.run` inside `unittest.TestCase`, fighting pytest’s event loop management (`tests/unit/test_memory_manager.py:20`, `tests/test_base.py:13`). This increases flake risk and obscures fixture reuse.

## Tooling & Execution Flow
- **Primary harness** – pytest exposes suite presets via a custom `--mode` option defined in `tests/conftest.py`. `run_tests.py` remains only as a compatibility shim that forwards `--mode` and `--coverage` flags.
- **pytest configuration** – `pytest.ini:1-15` enables asyncio auto-mode, strict markers, and a curated marker taxonomy. Coverage is wired for `pytest-cov`, but test files themselves are omitted from coverage reports (`pytest.ini:17-25`).

## Suite Layout & Intent
- `tests/unit/` holds configuration parsing, seed control, service helpers, logging, and deterministic logic checks. Most files still use `unittest.TestCase`, occasionally augmented with manual async runners (`tests/unit/test_reproducibility.py:18`, `tests/unit/test_memory_manager.py:20`).
- `tests/fast/` targets deterministic parsing and boundary logic using custom mocks (e.g., `-tests/fast/test_response_parsing.py:17-200`). These are true pytest modules and represent the fastest feedback loop.
- `tests/component/` exercises multi-agent flows with live dependencies. Many tests parametrize across languages and require OpenAI keys (`tests/component/test_phase2_manager_live.py:13-70`, `tests/component/test_prompt_harness_agents.py:13-37`). `pytest.mark.live` and `requires_openai` guard execution but still spin up real participants/utility agents.
- `tests/integration/` blends mocked infrastructure with subprocess execution (`tests/integration/test_cli_live.py:13-49`, `tests/integration/test_experiment_reproducibility.py:16-142`). Some rely on unittest classes, others use pytest marks.
- `tests/contracts/` and `tests/golden/` capture regression snapshots of translations, prompts, and memory behaviours (`tests/contracts/test_translation_regression.py:1-18`, `tests/golden/test_phase2_prompts.py:1-200`).
- Additional layers include `tests/component/test_phase2_quarantine.py:1-84` (mock-heavy), `tests/fixtures/` for reusable configs (`tests/fixtures/quarantine_test_fixtures.py:1-124`), `tests/support/` for harness utilities (`tests/support/prompt_harness.py:1-120`, `tests/support/mock_utilities.py:1-200`), `tests/golden/`, `tests/templates/README.md:1-32`, and `tests/utils/` stubs.
- Outside the pytest tree sit hand-run scripts (`test_parallel_execution.py:1-108`, `test_gemini_integration.py:1-120`, `test_semantic_mapping_fix.py:1-116`). They provide investigative tooling but are invisible to the automated suite and, in at least one case, contain syntax errors that prevent execution (`test_parallel_execution.py:78-83`).

## Fixtures, Helpers, and Language Instrumentation
- `tests/conftest.py:42-198` auto-registers layered markers, enforces skip policies driven by `SKIP_EXPENSIVE_TESTS`, and tracks multilingual coverage. It also injects live credential gating via `openai_api_key`, which performs an actual HTTP probe (`tests/conftest.py:56-77`).
- Prompt harness fixtures (`tests/conftest.py:80-122`) construct real agent configurations through `tests.support.config_factory` and `tests.support.prompt_harness` to spin up LLM-facing participants. These fixtures honour optional overrides from `TEST_CONFIG_OVERRIDE`.
- Language parametrization flows through `tests/support/language_matrix.py:28-153`, which interprets `LIVE_PRIMARY_LANGUAGE`, `LIVE_LANGUAGES`, `DEVELOPMENT_MODE`, and `FULL_INTEGRATION_TESTS`. Smart decorators decide whether suites run 1, 2, or 3 locales, influencing both runtime and language coverage metrics.
- Snapshot and regression tooling relies on bespoke data builders: `tests/support/mock_utilities.py:1-200` supplies richly instrumented mock agents, while `tests/support/process_capture.py:1-34` captures structured logging for assertions.

## Environment & External Dependencies
- Live layers require `OPENAI_API_KEY` (and optionally `OPENROUTER_API_KEY`, `GEMINI_API_KEY`). The `openai_api_key` fixture actively calls the OpenAI Models endpoint to short-circuit tests when unavailable (`tests/conftest.py:56-75`), so running component/integration suites offline is impossible without editing fixtures.
- Mode selection is now purely marker-based; contributors must still manage `LIVE_LANGUAGES`, `SKIP_EXPENSIVE_TESTS`, and `TEST_CONFIG_OVERRIDE` manually, which can surprise newcomers because behaviour shifts with environment state alone (`tests/conftest.py:124-166`).
- `tests/support/config_factory.py:1-160` and derived helpers depend on actual YAML specs (`config/default_config.yaml`, `config/test_ultra_fast.yaml`). Several tests perform disk IO to write temporary configs (`tests/integration/test_cli_live.py:25-44`).

## Coverage & Reporting Posture
- Coverage reports omit all test modules (`pytest.ini:17-21`), so the project focuses on production code only. Coverage enforcement is driven manually via `pytest --cov`.
- Language coverage remains a first-class metric: component and live suites can emit a JSON summary when `LANGUAGE_REPORT_PATH` is set, but enforcement now relies on contributors opting in rather than the wrapper enforcing it automatically.

## Pain Points & Outdated Patterns
- **Mixed frameworks and manual async orchestration** – Many “unit” modules inherit from `unittest.TestCase` yet run under pytest, manually driving `asyncio.run` per test (`tests/unit/test_memory_manager.py:85-148`). This pattern sidesteps pytest-asyncio and can leak event loops or mask fixture errors. Base classes in `tests/test_base.py:13-66` perpetuate the unittest heritage.
- **Live-by-default component tests** – Component coverage depends on real LLM agents (`tests/component/test_phase2_manager_live.py:13-70`, `tests/component/test_phase2_manager_live.py:34-57`). With no recorded mocks, CI cannot exercise them unless secrets are injected, dramatically limiting automated assurance.
- **Uncollected diagnostic scripts** – Files like `test_parallel_execution.py:78-83`, `test_gemini_integration.py:28-120`, and `test_semantic_mapping_fix.py:1-116` are labelled as tests but live outside the pytest discovery tree. One is syntactically invalid, so even manual invocation fails. Their presence inflates perceived coverage while delivering none.
- **Wrapper expectations** – Historical documentation still references legacy runner behaviours. Until the cleanup completes, contributors may reach for the shim and expect features (config overrides, performance reports) that no longer exist.
- **Environment-driven branching** – Skip logic lives in multiple layers (`run_tests.py:318-364`, `tests/conftest.py:124-166`, `tests/support/language_matrix.py:83-141`). Understanding which tests run requires tracing env defaults, especially with `DEVELOPMENT_MODE` defaulting to “on” (`tests/support/language_matrix.py:97-141`).
- **Fragmented test data ownership** – Golden files, fixtures, and configs are distributed across `tests/golden/`, `tests/fixtures/`, and `tests/support/`, with overlapping responsibilities. There is little documentation tying them together beyond the template README (`tests/templates/README.md:1-32`).

## Adequacy & Coverage Observations
- Deterministic logic is reasonably exercised through mocks (`tests/fast/`, many `tests/unit/` modules), but end-to-end flows that avoid live APIs are scarce. For instance, no offline component test asserts the orchestration around the prompt harness without contacting OpenAI.
- Reproducibility/integration cases (`tests/integration/test_experiment_reproducibility.py:16-214`) stop short of running full experiments unless API keys are injected, so the critical seed semantics rely on manual inspection rather than automated enforcement.
- Contract-style suites (`tests/contracts/`, `tests/golden/`) help detect prompt regressions, yet they manually construct translation dictionaries or mocks instead of snapshotting production language assets, increasing maintenance cost.
- There is no single source of truth describing how to run subsets; contributors must read templates or code to understand language parametrization or fixture lifecycles.

## Ancillary Assets
- Templates (`tests/templates/`) and prompt harness utilities (`tests/support/prompt_harness.py:1-120`) encode institutional knowledge but are not cross-referenced from the README or developer docs, limiting discoverability.
- Numerous JSON transcripts (`transcripts/`, `transcript_*.json`) and reports in root suggest manual logging of prior failures, yet they are not integrated into automated regression tests.

---
This document captures the current state; future redesign should aim to decouple live dependencies, consolidate fixtures, and simplify runner semantics while preserving the multilingual guarantees that motivated the existing architecture.

## Alignment With Simplicity & Focus Goals
- **Single testing interface** – Rely on `pytest` directly. Drop `unittest` style bases (`tests/test_base.py:13`) and rewrite async tests to use `pytest.mark.asyncio`, eliminating the fallback path and manual loop juggling (`tests/unit/test_memory_manager.py:85`).
- **Keep runner minimal** – Retain a thin compatibility wrapper at most; ensure documentation pushes contributors toward direct pytest usage so there is no ambiguity about execution flow.
- **Keep tests under `tests/`** – Convert or retire standalone scripts:
  - `test_parallel_execution.py:1` → either promote to `tests/integration/test_parallel_execution.py` with pytest assertions or delete (currently broken at `test_parallel_execution.py:78-83`).
  - `test_gemini_integration.py:1` → fold critical coverage into targeted unit/component tests; otherwise remove.
  - `test_semantic_mapping_fix.py:1` → migrate insights into documentation or a hypothesis notebook; delete as executable test.
- **Clarify suite hierarchy** – Retain four layers but simplify names:
  - `tests/unit/` – pure functions/mocks only, pytest style.
  - `tests/component/` – can stay live; gate with a single `--run-live` flag rather than env sprawl.
  - `tests/integration/` – prefer end-to-end flows that can run offline by default, flip opt-in markers when API keys are present.
  - `tests/contracts/` & `tests/golden/` – merge into `tests/snapshots/` with pytest snapshot tooling to cut duplication.
- **Streamline fixtures** – Collapse language management into one helper module. Remove implicit environment toggles such as `DEVELOPMENT_MODE` defaults (`tests/support/language_matrix.py:97-141`). Instead, pass desired language matrices through pytest options (`pytest_addoption`) to make behaviour explicit.
- **Live test policy** – Allow live suites, but enforce clear opt-in via command-line markers. Provide minimal mocked equivalents so CI can run fast smoke tests without secrets.

## Proposed Implementation Phases
1. **Collapse tooling**
   - Strip `run_tests.py` to a minimal shim or delete in favour of direct `pytest` usage documented in `README.md`.
   - Remove the fallback branch and legacy args (`run_tests.py:300-408`).
2. **Unify test style**
   - Port `unittest` modules to pytest functions/classes.
   - Delete `tests/test_base.py` once tracing enforcement is handled via fixtures (`tests/conftest.py` can set envs in `pytest_configure`).
3. **Normalize suite layout**
   - Migrate or delete root-level scripts.
   - Merge `tests/contracts/` and `tests/golden/` into a snapshots suite with shared fixtures.
   - Audit `tests/support/` for redundant factories; document remaining helpers.
4. **Simplify environment knobs**
   - Replace env-based skip switches with pytest options (`--skip-expensive`, `--languages=en,es`).
   - Update fixtures to consume these options instead of env vars.
   - Document live test expectations and required secrets in a single section of the repo README.
5. **Rationalize coverage**
   - Decide whether to keep language coverage JSON. If required, encapsulate it as a pytest plugin rather than ad-hoc files generated per suite.
   - Ensure coverage configuration aligns with the simplified suite (adjust `pytest.ini` once directories change).

Executing the phases in order delivers a lean, pytest-first testing stack that still honours multilingual and live execution needs while eliminating redundant fallbacks and stray scripts.*** End Patch
