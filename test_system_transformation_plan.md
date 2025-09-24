# Test System Transformation Plan

This plan describes how to evolve the current Frohlich Experiment test suite into the ideal, multilingual, LLM-parity system captured in `docs/ideal_test_system.md`. It is intentionally detailed so the work can be shared across contributors while maintaining a coherent end state.

## Status Overview
- **Phase 1 – Baseline Assessment & Governance:** ✅ Completed (2025-09-23)
- **Phase 2 – Codebase Cleanup:** ✅ Completed (2025-09-23)
- **Phase 3 – Shared Test Infrastructure:** ✅ Completed (2025-09-23)
- **Phase 4 – Suite Restructuring:** ✅ Completed (2025-09-23)
- **Phases 5–11:** ⏳ Pending

---

## 0. Guiding Outcomes
- **Parity with production**: every pathway that calls an LLM in production is exercised by the tests with the same models and prompts.
- **Multilingual fidelity**: English, Spanish, and Mandarin flows are covered in each phase of the suite (unit logic exempt where no language behaviour exists).
- **Fast, focused feedback**: core validations complete quickly; heavier acceptance/live runs are explicit opt-ins.
- **Traceable behaviours**: each failure maps cleanly to an experiment phase or service.

References: docs/ideal_test_system.md:1, docs/test_suite_gap_analysis.md:1

---

## 1. Baseline Assessment & Governance
1. **Catalogue current suites**
   - Enumerate every file under `tests/` with metadata (module under test, uses LLM?, language coverage, runtime).
   - Flag legacy scaffolding (`tests/unit/test_phase1_manager.py.bak:1`, `tests/unit/test_phase2_manager.py.bak:1`, `tests/performance/test_memory_leak_detection.py:1`).
2. **Decide retention classes**
   - Keep: logic that still matches production behaviour.
   - Rewrite: tests depending on deprecated flows (e.g., `tests/unit/test_phase2_manager.py.bak:69` referencing `TwoStageVotingManager`).
   - Archive/Delete: suites that cover dead code or synthetic mocks that conflict with LLM parity.
3. **Define run-time budgets & cadence**
   - `unit` + `component` target < 2 minutes locally.
   - `integration` nightly or pre-merge when credentials exist.
   - `live` scheduled or manual, with clear cost expectations.
4. **Establish credential policy**
   - Document `.env` expectations, rotation, and secrets handling for OpenAI/OpenRouter keys.
   - Provide fallback skip markers when keys are absent to keep contributors unblocked.

Deliverables: inventory spreadsheet, retention decisions, updated CONTRIBUTING note for secrets.

---

## 2. Codebase Cleanup
1. **Retire `.bak` and obsolete modules**
   - Replace copies with authoritative rewritten tests or delete after migration.
   - Update references in CI configs if any point to `.bak` files.
2. **Cull unused directories**
   - Remove empty/pycache-only folders (`tests/acceptance`, `tests/logging`, `tests/resilience`, `tests/services`).
   - Archive legacy validation suites (`tests/validation/`) once their scenarios
     are replaced by the layered component coverage.
3. **Archive performance/resilience experiments**
   - Move long-running suites (`tests/performance/test_multilingual_scalability.py:1`, `tests/performance/test_memory_leak_detection.py:1`) to `archive/` or convert into documented manual procedures if they remain useful.
4. **Normalize fixtures**
   - Review `tests/fixtures/` for relevance; delete outdated configs; annotate remaining ones with language coverage requirements.

Deliverables: shrinked `tests/` tree aligned with active code; changelog summarizing removals.

---

## 3. Shared Test Infrastructure
1. **Create `tests/support/` package**
   - `prompt_harness.py`: helper to instantiate real participant & utility agents with consistent seeds, temperature overrides, retry policies, and locale switching.
   - `language_matrix.py`: utilities to iterate required language combinations per suite.
   - `config_factory.py`: build minimal experiment/config objects tuned for tests (Phase1-only, Phase2-only, full experiment) with hooks for locale-specific prompts.
   - `process_capture.py`: wrappers to capture `ProcessFlowLogger` / `AgentCentricLogger` output for assertions.
2. **Credential & rate-limit utilities**
   - Central context manager to enforce request pacing and record usage metrics for live runs.
   - Automatic skip markers if required keys are missing.
3. **Assertion helpers**
   - Behavioural checks such as `assert_phase1_summary`, `assert_discussion_consensus`, `assert_payoff_distribution` operating on real artefacts.

Deliverables: new support package with tests; migration guide for consuming suites.

---

## 4. Suite Restructuring
1. **Directory layout**
   - `tests/unit`: pure Python logic (config validation, distribution math, logging formatters). No LLM calls.
   - `tests/component`: Phase managers and services executing real prompts with scoped fixtures and the prompt harness.
   - `tests/integration`: end-to-end experiment runs and CLI smoke tests using real LLMs and persisted outputs.
   - `tests/live`: extended scenarios (stress, multilingual rotations beyond smoke, regression replays) invoked manually or via scheduled jobs.
   - `tests/contracts`: golden artefacts generated via real runs (JSON schemas, log payloads).
2. **Test discovery setup**
   - Update `run_tests.py:1` to map new directories and markers (`@pytest.mark.component`, `@pytest.mark.live`).
   - Ensure `pytest.ini:1` reflects new markers and excludes.

Deliverables: reorganized directories, updated tooling, passing discovery run proving empty shells exist.

---

## 5. Coverage by Experiment Phase
### Phase 1 (Individual Familiarization)
- **Component tests**
  - Drive `Phase1Manager` via real agents in all three languages using concise prompts; assert rankings, memory updates, earnings accumulation (core/phase1_manager.py:20).
  - Validate memory guidance styles and distribution generator integration.
- **Integration**
  - Ensure Phase1 results feed Phase2 contexts correctly (core/experiment_manager.py:157).

### Phase 2 (Group Discussion & Consensus)
- **Component tests**
  - Exercise `Phase2Manager` full discussion loop with multilingual prompts, ensuring the speaking order, discussion, voting, counterfactual services operate with real responses (core/phase2_manager.py:20).
  - Include consensus reached vs. not reached scenarios and error-recovery paths.
- **Acceptance**
  - Capture logs for each language, confirm transparency outputs, class assignments.

### Experiment Manager & CLI
- **Integration tests**
  - Run `FrohlichExperimentManager.run_complete_experiment` end-to-end with minimal config for each language; verify result serialization, process logger integration, trace IDs (core/experiment_manager.py:64, main.py:20).
  - CLI invocation `python main.py config/test_stub.yaml tmp_output.json` ensures environment-based logging and output file creation per language.

### Utilities & Logging
- **Unit tests**
  - Deterministic coverage for config parsing (`config/models.py:1`), distribution generation (`core/distribution_generator.py`), seed manager, logging formatters, error handling decorators.
- **Contract suites**
  - Snapshot process flow logs and results JSON for regression alerts; regenerate via controlled live calls when changes are intentional.

Deliverables: new tests covering each bullet; documentation referencing scenario names and expected runtime.

---

## 6. Multilingual Strategy
1. **Language matrix enforcement**
   - Provide decorator (e.g., `@language_matrix(['english','spanish','mandarin'])`) to run a component test across locales automatically.
2. **Prompt curation**
   - Maintain short, deterministic prompts per language for Phase1/Phase2 to reduce variability.
3. **Locale-specific assertions**
   - Validate translations via `language_manager` outputs (core/services/discussion_service.py:15) to ensure prompts remain valid.
4. **Rotation policy for heavy suites**
   - `tests/live` rotates primary language focus per run (e.g., Monday=Spanish, Tuesday=Mandarin) while ensuring smoke coverage always includes all languages.

Deliverables: documentation and utilities enforcing language coverage; updated contributing guide explaining expectations.

---

## 7. Tooling & Automation
1. **`run_tests.py` overhaul**
   - Add commands: `unit`, `component`, `integration`, `live`, `contracts` with combinations.
   - Respect `RUN_LIVE_TESTS` env var; default to running live suites when credentials present, otherwise skip with warning.
2. **CI pipeline updates**
   - Configure workflows: quick checks (unit+component), nightly integration (all languages), scheduled live acceptance.
   - Ensure secrets injection for CI, plus cost caps.
3. **Reporting**
   - Aggregate results per language; fail builds if any locale’s component suite is skipped unintentionally.

Deliverables: updated scripts, CI YAML, sample reports.

---

## 8. Migration of Existing Tests
1. **Port high-value logic**
 - Translate existing assertion logic from `.bak` files into new component suites, swapping mocks for live agents.
 - Preserve insights from parsing tests by transforming them into contract checks or prompt regression tests that use real outputs.
  - Relocate legacy unit suites that relied on removed parsing helpers to `archive/tests_unit_legacy` once their behaviour is covered by modern harness-based tests.
2. **Document staged removal**
   - Track migration progress; delete legacy files once equivalent coverage in new structure exists.
3. **Knowledge transfer**
   - Record rationale for discarded tests to avoid reintroducing anti-patterns (heavy sleeps, manual JSON mocks).

Deliverables: migration checklist, PRs aligning removal with new coverage, historical notes in repo wiki or docs.

---

## 9. Long-term Maintenance
1. **Playbook**
   - Update/review README sections
   - Update the documentation in docs


Deliverables: living documentation

---

## 10. Success Criteria
- `run_tests.py unit component` completes < 2 minutes locally with no skipped language coverage.
- Integration suite passes for English/Spanish/Mandarin using real LLM calls and produces validated artefacts.
- Legacy `.bak` files and deprecated directories removed from main branch.
- Multilingual contract snapshots stored and updated through deliberate processes.
- Contributors can add new experiment behaviours by extending factories/harnesses rather than inventing ad hoc mocks.

---

## 11. Sequencing Recommendation
1. Phases 1–2 (Assessment & Cleanup) — foundation.
2. Phase 3 (Support infrastructure) — unlocks subsequent work.
3. Phase 4–5 (Restructuring + coverage) — iterative per experiment phase.
4. Phase 6–7 (Multilingual enforcement & tooling) — layered once core suites exist.
5. Phase 8–9 (Migration & maintenance) — ongoing alongside implementation.

One release cycle (4–6 weeks) should accommodate initial rollout, with parallel streams for coverage and tooling.

---

Prepared for stakeholders and implementers driving the transformation effort.
