# Repository Guidelines

This guide helps contributors quickly understand the repository layout, how to run and test the project, and how to contribute changes confidently.

## Project Structure & Module Organization
- `core/`: Experiment orchestration (phase managers, distribution generator, original values data).
- `experiment_agents/`: Participant and utility agents.
- `config/`: YAML configs and Pydantic models; default `config/default_config.yaml`.
- `models/`: Typed dataclasses/enums for principles, results, logging.
- `utils/`: Logging, model provider, language manager, memory, error handling, runners.
- `tests/`: Unit tests in `tests/unit`, integration in `tests/integration`.
- `docs/`, `reports/`, `translations/`: Documentation, analysis outputs, i18n.
- Entrypoints: `main.py` (CLI), `run_tests.py` (unified test runner).

## Build, Test, and Development Commands
- Setup (Python 3.11+): `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run experiment: `python main.py` or `python main.py config/custom.yaml results/out.json`
- Run all tests: `python run_tests.py` (imports + unit + integration)
- Focused runs: `python run_tests.py unit` | `python run_tests.py integration`
- Examples: `python -m unittest tests.unit.test_memory_manager -v` or `python -m unittest discover -s tests/integration -p 'test_*.py' -v`

## Coding Style & Naming Conventions
- PEP 8; 4-space indentation; include type hints on public functions.
- Naming: `snake_case` modules/functions, `PascalCase` classes, `UPPER_CASE` constants.
- Keep modules focused (< ~500–800 lines); prefer small helpers in `utils/`.
- No enforced formatter; match existing style and run tests before PRs.

## Testing Guidelines
- Primary framework: `unittest` (some tests include pytest markers for asyncio).
- Layout: unit tests in `tests/unit/test_*.py`, integration tests in `tests/integration/test_*.py`.
- Coverage: no hard threshold; cover new logic, error paths, and config variants.

## Commit & Pull Request Guidelines
- Commits: imperative present tense, scoped and concise (e.g., `core: fix phase2 retry logic`).
- Branches: `feature/<short-description>`, `fix/<issue-id>`, `chore/<task>`.
- PRs: describe purpose and key changes, include test evidence (commands/output), and note any config or `.env` implications; link issues.

## Security & Configuration Tips
- Secrets in `.env` (e.g., `OPENAI_API_KEY`, `OPENROUTER_API_KEY`); never commit keys.
- Validate YAML via `ExperimentConfiguration`; place new examples under `config/`.
- Keep analysis artifacts under `reports/`; avoid sensitive data in committed outputs.

