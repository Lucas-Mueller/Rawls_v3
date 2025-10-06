# Repository Guidelines

## Project Structure & Module Organization
- `core/` orchestrates phase managers, distribution helpers, dataset loaders; treat as pipeline backbone.
- `experiment_agents/` hosts participant agents and shared utilities; keep each agent modular with explicit typing.
- `config/` contains YAML specs and Pydantic models; `config/default_config.yaml` anchors defaults.
- `models/` provides dataclasses/enums for principles, results, logging payloads; extend rather than replace existing types.
- Tests live under `tests/unit/` and `tests/integration/`; entrypoints are `main.py` for experiments and `run_tests.py` for suites.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` boots the local environment.
- `python main.py` runs the baseline experiment; pass `python main.py config/custom.yaml results/out.json` to target custom flows.
- `python run_tests.py` executes the full matrix; append `unit` or `integration` to scope.
- `python -m unittest tests.unit.test_memory_manager -v` isolates a single module.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indents and explicit type hints on public functions.
- Modules/functions use `snake_case`; classes `PascalCase`; constants `UPPER_CASE`.
- Mirror existing formatting; use concise comments only for non-obvious intent.
- Keep new files ASCII unless an existing file already uses Unicode.

## Testing Guidelines
- Rely on `unittest`; async helpers already include necessary pytest markers.
- Name tests `test_*`, cover happy paths plus error handling and config variants.
- Prefer targeted unit coverage before integration runs; validate new YAML via `ExperimentConfiguration`.
- Run `python run_tests.py` after significant changes and before PRs.

## Commit & Pull Request Guidelines
- Write imperative commit subjects scoped by area, e.g., `core: fix phase2 retry logic`.
- Use branches like `feature/<short-description>`, `fix/<issue-id>`, or `chore/<task>`.
- PRs should summarize intent, list critical changes, link issues, and attach test evidence.

## Security & Configuration Tips
- Store secrets (e.g., `OPENAI_API_KEY`, `OPENROUTER_API_KEY`) in `.env`; never commit them.
- Place analysis artifacts in `reports/` and scrub sensitive data prior to sharing.
- Validate new configs against project models before merging defaults.

## Agent-Specific Instructions
- Add agents under `experiment_agents/` with modular behavior and explicit dependencies.
- Surface toggles through Pydantic config models and update `config/default_config.yaml` when defaults change.
- Pair agent updates with focused unit tests and, when relevant, integration runs that exercise the full flow.
