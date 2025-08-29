# Repository Guidelines

## Project Structure & Module Organization
- `core/`: Experiment orchestration (phase managers, distribution generator, original values data).
- `experiment_agents/`: Participant and utility agents.
- `config/`: YAML configs and Pydantic models; default at `config/default_config.yaml`.
- `models/`: Typed dataclasses/enums for principles, results, logging.
- `utils/`: Logging, model provider, language manager, memory, error handling, runners.
- `tests/`: `tests/unit` and `tests/integration` suites.
- `docs/`, `reports/`, `translations/`: Documentation, analysis outputs, i18n.
- Entrypoints: `main.py` (CLI), `run_tests.py` (unified test runner).

## Build, Test, and Development Commands
```bash
# Setup (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run experiment
python main.py                          # uses config/default_config.yaml
python main.py config/custom.yaml results/out.json

# Run tests
python run_tests.py                     # import + unit + integration
python run_tests.py unit | integration
python -m unittest tests.unit.test_memory_manager -v
```

## Coding Style & Naming Conventions
- Follow PEP 8; 4-space indentation. Use type hints for public functions.
- Naming: snake_case for modules/functions, PascalCase for classes, UPPER_CASE for constants.
- Keep modules focused (< ~500–800 lines); prefer small helpers in `utils/`.
- No enforced formatter; match existing style and run tests before PRs.

## Testing Guidelines
- Frameworks: `unittest` primary; some tests use pytest markers (asyncio). Prefer unittest discovery.
- Layout: place unit tests in `tests/unit/test_*.py` and integration tests in `tests/integration/test_*.py`.
- Coverage: no hard threshold; cover new logic, error paths, and config variants.
- Useful commands: `python -m unittest discover -s tests/integration -p 'test_*.py' -v`.

## Commit & Pull Request Guidelines
- Commits: imperative present tense, scoped and concise (e.g., `core: fix phase2 retry logic`).
- Branches: `feature/<short-description>`, `fix/<issue-id>`, `chore/<task>`.
- PRs: include purpose, key changes, test evidence (commands/output), and any config or `.env` implications; link issues.

## Security & Configuration Tips
- Secrets: use `.env` for `OPENAI_API_KEY` / `OPENROUTER_API_KEY`; never commit keys.
- Configs: validate YAML via `ExperimentConfiguration`; add new examples under `config/`.
