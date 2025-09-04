# Repository Guidelines

## Project Structure & Module Organization
- `core/`: Experiment orchestration (phase managers, distribution generator, originals data).
- `experiment_agents/`: Participant and utility agents.
- `config/`: YAML configs and Pydantic models (default: `config/default_config.yaml`).
- `models/`: Typed dataclasses/enums for principles, results, logging.
- `utils/`: Logging, model provider, language manager, memory, error handling, runners.
- `tests/`: Unit in `tests/unit`, integration in `tests/integration`.
- `docs/`, `reports/`, `translations/`: Documentation, analysis outputs, i18n.
- Entrypoints: `main.py` (CLI), `run_tests.py` (tests).

## Build, Test, and Development Commands
- Setup (Python 3.11+):
  - `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run experiment:
  - `python main.py` or `python main.py config/custom.yaml results/out.json`
- Run all tests:
  - `python run_tests.py` (imports + unit + integration)
- Focused runs:
  - `python run_tests.py unit` | `python run_tests.py integration`
  - Examples: `python -m unittest tests.unit.test_memory_manager -v` or `python -m unittest discover -s tests/integration -p 'test_*.py' -v`

## Coding Style & Naming Conventions
- PEP 8, 4-space indentation. Type hints on public functions.
- Naming: `snake_case` modules/functions, `PascalCase` classes, `UPPER_CASE` constants.
- Keep modules focused (< ~500–800 lines). Prefer helpers in `utils/`.
- No enforced formatter; match existing style. Run tests before PRs.

## Testing Guidelines
- Framework: `unittest` (some tests use `pytest` markers for asyncio).
- Layout: unit tests in `tests/unit/test_*.py`, integration in `tests/integration/test_*.py`.
- Aim to cover new logic, error paths, and config variants. Provide minimal repro cases.

## Commit & Pull Request Guidelines
- Commits: imperative present, scoped and concise (e.g., `core: fix phase2 retry logic`).
- Branches: `feature/<short-description>`, `fix/<issue-id>`, `chore/<task>`.
- PRs: describe purpose and key changes, include test evidence (commands/output), note config or `.env` implications, and link issues.

## Security & Configuration Tips
- Store secrets in `.env` (e.g., `OPENAI_API_KEY`, `OPENROUTER_API_KEY`); never commit keys.
- Validate YAML via `ExperimentConfiguration`; add examples under `config/`.
- Keep analysis artifacts under `reports/`; avoid sensitive data in committed outputs.

## Agent-Specific Instructions
- Add new agents under `experiment_agents/`; keep them small, focused, and typed.
- Provide configuration hooks in `config/` and update `config/default_config.yaml` if applicable.
- Add unit tests for agent behavior and integration tests for end-to-end flows.

