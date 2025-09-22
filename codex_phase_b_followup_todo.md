# Phase B Follow-up To-Do

## 1. Finish Pytest Migration
- ☑ Catalogue remaining `unittest.TestCase` suites (see `docs/unittest_inventory.md`).
- ◐ Rewrite priority legacy suites (e.g., validation, distribution generator) using pytest fixtures — new pytest suites added under `tests/validation/` and `tests/unit/test_distribution_generator.py`.
- ☐ Remove/reduce dependency on `tests/test_base.py` and related base classes.
- ◐ Update documentation/checklists after migration (Phase A checklist reflects progress).

## 2. Structured Prompt Assertions & Integration Tests
- ☑ Introduce helper utilities for schema-based prompt validation (`tests/utils/prompt_assertions.py`).
- ☑ Replace golden prompt tests with schema/context checks (`tests/golden/test_phase2_prompts.py`).
- ☐ Build targeted integration tests exercising Phase 2 discussion/voting with real services and multilingual transcripts.

## 3. Resilience Fixture Expansion
- ☑ Add transcript scripts for malformed/timeout responses (`tests/data/acceptance/malformed_response.json`).
- ◐ Create fixtures to simulate utility agent timeouts and language manager failures (`tests/resilience/test_voting_service_resilience.py`).
- ◐ Add resilience tests covering these failure modes in Phase1/Phase2 managers and services (voting service coverage added; expand to other managers).

## 4. Automation & Pre-commit
- ☑ Provide pre-commit or invoke script that runs `make test`, `make test-acceptance`, `make test-contracts`, and `make test-resilience` (`scripts/run_all_tests.sh`, `.pre-commit-config.yaml`).
- ☑ Document usage in onboarding/testing guides (`docs/testing.md`, `docs/onboarding.md`).
