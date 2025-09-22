# Testing Guide (Phase A Foundations)

This repository now standardises on `pytest` for all suites. The legacy `unittest` base
classes and bespoke runners remain temporarily for backwards compatibility, but new work
should follow the structure outlined below.

## Running Tests
- Default command: `python -m pytest -m "not slow"`
- Run acceptance smoke test: `python -m pytest tests/acceptance -m acceptance`
- Collect coverage: `python -m pytest --cov=core --cov=experiment_agents --cov=utils`

## Shared Fixtures
Located in `tests/conftest.py` and auto-injected where appropriate:

- `disable_tracing_env` *(autouse)*: disables OpenAI Agents SDK tracing to keep test logs clean.
- `seed_rng` *(autouse)*: seeds Python and NumPy RNGs. Override via `PYTEST_RANDOM_SEED` env var.
- `stubbed_runner`: patches `agents.Runner.run` with a deterministic scriptable stub (see `tests/utils/stubbed_runner.py`).
  - Register responses per agent with `stubbed_runner.register("Agent Name", ["json", ...])`.
  - Optional `register_default` covers agents without explicit scripts.
- `stub_create_agent` *(autouse)*: replaces dynamic temperature detection for participant & utility
  agents with lightweight in-memory stubs to avoid network calls.
- `reset_asyncio_loop`: helper fixture to cancel pending tasks after async tests.
- `minimal_experiment_config`: returns the smallest valid experiment configuration for smoke tests.
- `transcripts_root`: exposes the acceptance transcript directory for test code that needs it.
- Resilience helpers (see `tests/resilience/conftest.py`):
  - `failing_language_manager`: raises `KeyError` to exercise translation fallbacks.
  - `timeout_utility_agent`: simulates utility-agent timeouts for managers/services.
  - `malformed_json_transcript`: representative malformed payload for parser hardening.

## Resilience Playbook
- `tests/resilience/test_phase_manager_resilience.py` covers Phase 1 constraint re-prompts and Phase 2 translation fallbacks using the shared fixtures above.
- Existing voting-service tests now reuse the shared failure fixtures to keep scenarios consistent.
- When introducing new failure modes, prefer adding data/fixtures alongside the existing ones so suites remain deterministic.

## Acceptance Testing Skeleton
`tests/acceptance/test_experiment_happy_path.py` runs the complete experiment manager with
stubbed phase managers, asserting on `ExperimentResults`. Extend this suite for richer
scenario coverage without touching the production orchestration logic.

Reusable transcripts for acceptance tests live under `tests/data/acceptance/`. Use
`tests/utils/stub_scripts.load_and_register` to load them into the shared `stubbed_runner`.
Add new transcripts as JSON `{ "AgentName": ["message 1", ...] }` objects.

## Additional Suites & Markers
- `@pytest.mark.contracts`: service contract and logging tests located under `tests/services/` and `tests/logging/`.
- `@pytest.mark.resilience`: error-handling and retry scenarios located under `tests/resilience/`, including manager-level retries and translation fallbacks.
- Run `python -m pytest -m contracts` or `python -m pytest -m resilience` when validating robustness locally or in CI.

## Automation
- Use `scripts/run_all_tests.sh` to execute the full matrix (unit/integration, acceptance, contracts, resilience).
- A pre-commit hook configuration (`.pre-commit-config.yaml`) is provided; install with `pre-commit install` to ensure the suite runs before commits land.

## Next Steps
- Gradually migrate legacy `unittest` suites to pytest-style async tests.
- Replace golden string comparisons with structural assertions.
- Tag long running/performance suites with `@pytest.mark.slow` and exclude from default runs.
- Run `make test` and `make test-acceptance` before publishing release branches or opening PRs to
  guarantee both smoke and acceptance suites remain green.

## Targeted Integration Flow
- `tests/logging/test_experiment_tracing.py` exercises `FrohlichExperimentManager.run_complete_experiment` with stubbed agents/services. It validates trace metadata (participant roster, experiment id, language) and ensures experiment results remain well-formed without network dependencies.

Refer to `codex_phase_a_tasklist.md` for the remaining tasks required to finish Phase A.
