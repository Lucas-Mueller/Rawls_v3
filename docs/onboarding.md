# Onboarding Checklist

1. Install dependencies:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```
2. Review `docs/testing.md` for fixture usage and test commands.
3. Run the default suites before pushing changes:
   ```
   make test
   make test-acceptance
   make test-contracts
   make test-resilience
   ```
   or run the combined script `./scripts/run_all_tests.sh` (also used by the optional pre-commit hook).
4. When adding tests:
   - Prefer pytest fixtures over unittest base classes.
   - Use `stubbed_runner` (see `tests/utils/stubbed_runner.py`) to script LLM responses.
   - Store reusable transcripts in `tests/data/acceptance/`.
5. Legacy assets live in `tests/_legacy/`; port them to pytest before re-enabling.
