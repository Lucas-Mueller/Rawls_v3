# Repository Guidelines

## Project Structure & Module Organization
- `core/` orchestrates phase managers, distribution helpers, and dataset loaders.
- `experiment_agents/` hosts participant agents plus shared utilities; keep modules typed and focused.
- `config/` holds YAML configs and Pydantic models; `config/default_config.yaml` is the baseline.
- `models/` stores dataclasses and enums for principles, results, and logging payloads.
- `utils/` aggregates logging, language providers, memory, error handling, and runner helpers.
- Tests live in `tests/unit/` and `tests/integration/`; entrypoints are `main.py` for experiments and `run_tests.py` for suites.

## Build, Test, and Development Commands
- Bootstrap the virtualenv: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Run the default experiment pipeline: `python main.py`, or pass paths such as `python main.py config/custom.yaml results/out.json`.
- Execute the full test matrix: `python run_tests.py`; append `unit` or `integration` to limit scope.
- Target a specific module: `python -m unittest tests.unit.test_memory_manager -v`.

## Coding Style & Naming Conventions
- Adhere to PEP 8 with four-space indents and explicit type hints on public functions.
- Use `snake_case` for modules and functions, `PascalCase` for classes, `UPPER_CASE` for constants.
- Mirror existing formatting; reserve concise comments for non-obvious intent.

## Testing Guidelines
- Rely on `unittest`; async helpers may introduce `pytest` markers already wired in.
- Name all tests `test_*`, keep fixtures minimal, and cover error paths plus config variants.
- Run `python run_tests.py` (or the scoped suite) before pushing and again pre-PR.

## Commit & Pull Request Guidelines
- Write imperative, scoped commits that mention the touched area, e.g., `core: fix phase2 retry logic`.
- Branch naming: `feature/<short-description>`, `fix/<issue-id>`, or `chore/<task>`.
- Pull requests should summarize intent, list critical changes, link issues, and paste test evidence.

## Security & Configuration Tips
- Store API keys such as `OPENAI_API_KEY` and `OPENROUTER_API_KEY` in `.env`; never commit secrets.
- Validate new YAML with `ExperimentConfiguration` before merging; keep exemplars under `config/`.
- Place analysis artifacts in `reports/` and scrub sensitive content prior to sharing.

## Agent-Specific Instructions
- Add new agents under `experiment_agents/`, keeping behavior modular with explicit dependencies.
- Surface toggles via the `config/` Pydantic models and adjust `config/default_config.yaml` when defaults shift.
- Pair agent changes with targeted unit tests and, when relevant, integration runs that exercise the full flow.
