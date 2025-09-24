# Test Suite Alignment Report

This document compares the current Frohlich Experiment test suite with the
target state defined in `test_system_transformation_plan.md`. Each section
summarises the plan intent, the implementation that ships in this repository,
and any remaining gaps or follow-up work.

## Snapshot of the Current Suite

- **Structure** – Active layers live under `tests/unit`, `tests/component`,
  `tests/integration`, `tests/contracts`, and `tests/validation`. Component
  tests host both deterministic helpers and live LLM scenarios marked with
  `@pytest.mark.live`. There is no dedicated `tests/live` directory; live runs
  are parameterised within the component layer.
- **Execution tooling** – `run_tests.py` orchestrates layered selections,
  honours `RUN_LIVE_TESTS`, emits language coverage reports, and enforces per
  language execution for component/live suites (`run_tests.py`).
- **Shared infrastructure** – Reusable helpers live in `tests/support`
  (prompt harness, config factories, language matrix decorators, process flow
  capture). Pytest hooks in `tests/conftest.py` add language coverage tracking
  and credential gating.
- **Integration footprint** – The only remaining integration suite is
  `tests/integration/test_experiment_reproducibility.py`, which focuses on
  deterministic seeding and does not contact live LLM endpoints.

## Phase-by-Phase Alignment

### Phase 1 – Baseline Assessment & Governance

- **Plan target** – Catalogue the legacy suites, decide retention classes, and
  document cadence/credentials.
- **Current state** – `docs/test_baseline_assessment.md` captures the inventory
  snapshot and retention decisions, including the note that the legacy
  directory has now been removed (`docs/test_baseline_assessment.md:16`). The
  README and setup docs prescribe environment variables for OpenAI access.
- **Gaps / notes** – The cadence/governance references stay embedded in
  documentation, but there is no automated inventory tooling; updates depend on
  manual refreshes.

### Phase 2 – Codebase Cleanup

- **Plan target** – Delete `.bak` artefacts, prune empty folders, retire
  obsolete performance suites, and normalise fixtures.
- **Current state** – Legacy `.bak` suites were removed, the `tests/_legacy`
  directory no longer exists, and performance folders are archived. Fixtures
  in `tests/fixtures` were trimmed to active ones.
- **Gaps / notes** – Legacy unit suites that exercised deprecated parsing
  helpers have been removed; rebuild scenarios on top of the prompt harness if
  the coverage is still required.

### Phase 3 – Shared Test Infrastructure

- **Plan target** – Provide prompt harness utilities, language matrix helpers,
  config factories, process-log capture, credential/rate-limit helpers, and
  shared assertion modules.
- **Current state** – `tests/support/prompt_harness.py` and
  `tests/support/config_factory.py` cover harness + config creation; language
  matrix decorators live in `tests/support/language_matrix.py`; log capture is
  implemented via `tests/support/process_capture.py`; pytest fixtures guard
  credentials and log language coverage (`tests/conftest.py`).
- **Gaps / notes** – There is no shared assertion helper module (plan called
  out `assert_discussion_consensus`, etc.), and rate-limit enforcement remains
  ad-hoc; the suite skips live tests when the API is unavailable but does not
  throttle requests.

### Phase 4 – Suite Restructuring

- **Plan target** – Establish clear directories for unit, component,
  integration, live, and contract suites with predictable discovery rules.
- **Current state** – Unit, component, integration, and contract layers exist
  and are auto-marked in `tests/conftest.py`; contract tests rely on golden
  fixtures. Live scenarios run within the component layer (`tests/component`
  files suffixed with `_live.py`).
- **Gaps / notes** – There is still no dedicated `tests/live` directory or
  rotation harness; live cases are intermixed with component tests. The
  `tests/validation` namespace sits outside the plan’s topology and may need to
  be folded into the layered structure.

### Phase 5 – Coverage by Experiment Phase

- **Plan target** – Ensure Phase 1/Phase 2 flows, experiment manager, CLI,
  utilities, and contract artefacts have targeted coverage across languages.
- **Current state** – Multilingual live coverage exists for Phase 1 and Phase 2
  managers (`tests/component/test_phase1_manager_live.py`,
  `tests/component/test_phase2_manager_live.py`), discussion/voting services,
  translations, and quarantine scenarios. Unit suites exercise seed management,
  distribution math, config validation, and logging contracts. Contract tests
  snapshot distribution, memory, summary, and translation outputs
  (`tests/contracts/test_translation_regression.py`).
- **Gaps / notes** – There is no live integration test for
  `FrohlichExperimentManager.run_complete_experiment` or the CLI entry point;
  `tests/integration/test_experiment_reproducibility.py` is deterministic and
  bypasses LLM calls. Acceptance logging per language is partially covered in
  component tests but not in end-to-end form. The suite still lacks artefact
  documentation for each scenario’s expected runtime.

### Phase 6 – Multilingual Strategy

- **Plan target** – Enforce language matrices, curate deterministic prompts,
  assert locale-specific outputs, and rotate heavy live suites by locale.
- **Current state** – Language parameterisation is centralised through
  `parametrize_languages` and enforced via the language coverage report hook in
  `tests/conftest.py`. Component tests assert translated outputs and logging
  snippets (e.g., `tests/component/test_language_logging_live.py`). The
  harness seeds runs to reduce variability.
- **Gaps / notes** – There is no rotation policy for heavy suites or a
  dedicated `tests/live` schedule; prompt curation guidelines exist in code but
  not in documentation. Locale-specific assertions focus on structural checks
  rather than validating full translations, so prompt drift detection remains a
  manual exercise.

### Phase 7 – Tooling & Automation

- **Plan target** – Enhance `run_tests.py`, configure CI workflows, and report
  per-language execution.
- **Current state** – The runner now supports layered selections, coverage
  toggles, and language-report validation; a sample report is checked in at
  `reports/language_report_example.json`. Pytest hooks emit JSON coverage per
  run.
- **Gaps / notes** – GitHub workflows were intentionally removed for this
  project, so the CI pipeline portion of Phase 7 remains out of scope. Beyond
  generating JSON, there is no aggregation/reporting pipeline.

### Phase 8 – Migration of Existing Tests

- **Plan target** – Port high-value logic into the new layers, track removals,
  and document knowledge transfer.
- **Current state** – The coverage plan in `docs/phase5_coverage_plan.md`
  records where migrated scenarios now live, and the old integration suites
  were deleted. Component/unit replacements cover the migrated behaviours.
- **Gaps / notes** – A formal migration ledger and rationale write-up for
  discarded suites have not been authored; oral history lives in PRs and the
  coverage plan.

### Phase 9 – Long-term Maintenance

- **Plan target** – Refresh README/docs playbooks and keep documentation
  aligned with the runner.
- **Current state** – README, installation, quickstart, and contributor guides
  describe the new runner modes, environment variables, and rate-limit
  troubleshooting (`README.md`, `docs/getting-started/installation.rst`,
  `docs/contributing/development-setup.rst`).
- **Gaps / notes** – The plan’s broader vision for metrics dashboards and
  scheduled audits is still aspirational; no automated runtime/cost tracking or
  cadence checklist exists beyond documentation notes.

### Phase 10 – Success Criteria Check-in

- **Plan target** – Fast unit/component runs (<2 minutes), integration suite
  exercising all languages with real LLM calls, removal of deprecated suites,
  deliberate contract workflow, and extensible harness-driven tests.
- **Current state** – Deprecated suites are gone, and contributors now reuse
  harness utilities. However, `python run_tests.py unit component` currently
  fails because Phase 7 coverage work is still in flight, and integration suites
  are not yet live/multilingual. Contract tests exist but the refresh process is
  only partially documented (`docs/contract_test_playbook.md`).
- **Gaps / notes** – The runtime budget and multilingual integration target
  remain unmet; additional implementation work is required before the success
  criteria can be satisfied.

### Phase 11 – Sequencing & Future Work

- **Observation** – Work continues broadly along the recommended sequencing,
  but remaining items (integration coverage, live rotation, metrics cadence)
  should be prioritised before expanding into new experiment behaviours.

## Key Follow-ups

1. Expand the CLI smoke (now in `tests/integration/test_cli_live.py`) with
   additional language rotations once live credentials are available.
2. Establish a lightweight cadence checklist and metrics aggregation process
   (even a manual dashboard) to complete the long-term maintenance vision from
   Phase 9 and reinforce the success criteria.
