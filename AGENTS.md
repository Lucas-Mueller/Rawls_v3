# Repository Guidelines

## Project Structure & Module Organization
- `core/` orchestrates experiment phases, data distribution, and support utilities; treat it as the pipeline backbone.
- `experiment_agents/` houses participant agents and shared utilities; keep each module modular with explicit typing.
- `config/` holds YAML specs and Pydantic models; extend `config/default_config.yaml` when adding knobs.
- `models/` defines dataclasses and enums for principles, results, and logging; extend existing types instead of replacing them.
- `utils/` and `knowledge_base/` provide shared helpers and prompt assets; scope changes and document them.
- Tests live in `tests/unit/` and `tests/integration/`; research notes and plans live under `docs/` and `reports/`.
- Entrypoints are `main.py` for experiments and `run_tests.py` for suites.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` bootstraps the environment.
- `python main.py` runs the baseline experiment; pass `python main.py config/custom.yaml results/out.json` to target custom flows.
- `python run_tests.py` executes the full test matrix; append `unit` or `integration` to scope.
- `python -m unittest tests.unit.test_memory_manager -v` isolates a single module for focused debugging.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indents, explicit public type hints, and docstrings where intent is non-obvious.
- Modules and functions use `snake_case`, classes use `PascalCase`, constants stay in `UPPER_CASE`.
- Mirror existing formatting, keep new files ASCII, and comment only when behavior is unclear.

## Testing Guidelines
- Primary framework is `unittest`; async helpers already embed required pytest markers.
- Name tests `test_*`, cover success and failure paths, and validate new YAML via `ExperimentConfiguration`.
- Run `python run_tests.py` after substantial changes and before proposing merges.

## Commit & Pull Request Guidelines
- Write imperative commit subjects scoped by area (e.g., `core: add phase2 retry telemetry`).
- Use branches like `feature/<short-description>`, `fix/<issue-id>`, or `chore/<task>` and keep histories linear.
- Pull requests should state intent, highlight critical code paths, link issues, and attach test evidence.

## Security & Configuration Tips
- Keep secrets such as `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env` and out of version control.
- Validate config changes with the Pydantic models before updating defaults.

## Agent-Specific Instructions
- Place new agents in `experiment_agents/`, expose behavior through clear methods, and declare dependencies explicitly.
- Surface toggles through the config models and update `config/default_config.yaml` when defaults shift.
- Pair agent updates with targeted unit tests and, when relevant, integration runs that exercise the whole pipeline.
