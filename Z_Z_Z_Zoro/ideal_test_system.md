# Ideal Test Architecture for the Frohlich Experiment

- **Fast feedback**: keep the default test run under ~2 minutes by isolating slow, integration-heavy checks into explicit suites.
- **LLM parity**: whenever production code invokes an LLM, the corresponding tests do too—no mocking the model layer; instead, constrain prompts, capture transcripts, and rely on guardrails for reproducibility.
- **Multilingual fidelity**: every suite that touches language-aware behaviour exercises English, Spanish, and Mandarin paths (or documents why a subset is acceptable) so regressions surface early.
- **Behaviour-first**: assert on observable outcomes (state transitions, logging payloads, persisted results) rather than implementation details.
- **Traceable flow**: make it easy to connect a failing test to the experiment phase/step it represents.
- **Simple to extend**: each new feature slots into an obvious layer with ready-to-use fixtures and helpers.

## Suite Topology
1. **Unit Tests (`tests/unit/`)** – pure logic that does not talk to the model layer.
   - Config & model validation (Pydantic field rules, seed generation, YAML loader).
   - Utilities (`distribution_generator`, `principle_name_manager`, `seed_manager`, `language_manager`, logging formatters).
   - Error-handling helpers (categorisation, retry policies, serialization).
   - Phase services for non-LLM routines (e.g., speaking order shuffling) using deterministic data.
2. **Component Tests (`tests/component/`)** – asynchronous managers with real LLM interactions kept minimal and purposeful.
   - `Phase1Manager` drives actual participant agents through concise prompts to verify memory/earnings pipelines in all supported languages.
   - `Phase2Manager` runs discussion → voting → payout loops with production prompts, guarded by scoped configs, rate limiting, and multilingual assertions.
   - Counterfactual & voting services collaborate on shared state contracts while still delegating parsing to real `UtilityAgent` calls in each language variant.
3. **Integration Tests (`tests/integration/`)** – high-level flows over trimmed configs with real agents.
   - Default path uses production agents and real LLM calls against minimal fixtures, asserting on experiment summary and persisted payloads across languages.
   - CLI smoke (`python main.py config/test_stub.yaml tmp_output.json`) with environment fixtures to confirm logging + file output using live model interactions in at least one non-English locale per run.
   - Regression guard for error-path recovery (e.g., injected transient failure handled by `handle_experiment_errors`) while letting the model produce natural language responses reflective of multilingual scenarios.
4. **Live Acceptance (`tests/live/`)** – stress and multilingual coverage suites that deliberately exercise the same endpoints as production under throttled, well-defined scenarios, including rotating language matrices.
5. **Contract/Acceptance Snapshots (`tests/contracts/`)** – opt-in snapshots for public artefacts (results JSON schema, logging payload structure) using lightweight golden files generated from real LLM interactions.

## Supporting Infrastructure
- **Test doubles** live under `tests/support/`:
- `PromptHarness` utilities to standardise how real participant/utility agents are instantiated for tests (consistent seeds, retry windows, logging hooks, language overrides).
- Factories for `ExperimentConfiguration`, `Phase1Results`, `GroupDiscussionState` with deterministic scaffolding while leaving message generation to the models, including helpers for spinning multilingual configs.
- Helpers for capturing `ProcessFlowLogger` events and agent-centric logs so assertions use observable artefacts from real calls, tagged by language for easy triage.
- Live helpers to provision real-model agents when `RUN_LIVE_TESTS=1` (loads API keys, enforces rate limiting, records latency stats) and fall back to skipping suites if credentials are absent, while guaranteeing representative language coverage per run.
- **Common assertions** module for shared checks (e.g., `assert_discussion_round`, `assert_payoff_distribution`).
- **Async test harness** built on `unittest.IsolatedAsyncioTestCase`; use `asyncio.run` only within helpers.
- **Seed fixture** ensuring reproducibility by defaulting `SeedManager` to a fixed seed per test.
- **File sandbox** utilities to create temporary output directories using `tempfile.TemporaryDirectory` context managers.

## Coverage Matrix
- **Configurations**: YAML loader, per-agent validation, logging config, derived seed logic.
- **Phase 1**: initial ranking flow, memory updates, repeated application outcome math, final choice recording.
- **Phase 2**: speaking order strategies, discussion prompt generation, voting consensus detection, counterfactual payoff computation, transparency outputs.
- **Experiment Manager**: init path (agents created once), process logging handshake, tracing metadata, result serialization, consensus summary.
- **Error Handling & Logging**: `handle_experiment_errors` decorator behaviour, `AgentCentricLogger` capture structure, process logger colour toggles.
- **Utilities**: distribution generation edge cases, principle keyword lookups, language manager fallbacks, seed derivation.

## Execution Profiles
- `python run_tests.py unit` → runs unit + component suites (default CI target).
- `python run_tests.py integration` → heavy flows that exercise real LLM paths; runs nightly or before releases.
- `RUN_LIVE_TESTS=0 python run_tests.py integration` → optional flag to skip suites that need credentials (defaults to running when keys present).
- `python run_tests.py contracts` → opt-in; refresh snapshots when intentional changes occur using regenerated artefacts from live agents.

## Maintenance Workflow
- New feature → add/extend factories, write unit/component tests first, follow with integration coverage if the public flow changes.
- When touching prompts or logging schemas, update contract snapshots with review of diffs.
- Keep fake agents simple; if a scenario needs richer behaviour, add explicit behaviour flags instead of copying real agent logic.
- Document any long-running integration tests with expected runtime so maintainers can triage slowdowns early.
