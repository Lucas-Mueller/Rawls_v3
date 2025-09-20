# Repository Guidelines

## Project Structure & Module Organization
- `core/` orchestrates experiments, including phase managers, distribution helpers, and original dataset loaders.
- `experiment_agents/` houses participant agents and shared utilities; keep files focused and typed.
- `config/` stores YAML configs and Pydantic models (`config/default_config.yaml` is the baseline).
- `models/` defines typed dataclasses/enums for principles, results, and logging payloads.
- `utils/` collects cross-cutting helpers (logging, language providers, memory, error handling, runners).
- Tests live under `tests/unit/` and `tests/integration/`; entrypoints are `main.py` for experiments and `run_tests.py` for suites.

## Build, Test, and Development Commands
- Create the virtualenv and install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Run the default experiment: `python main.py` or pass config/output paths (`python main.py config/custom.yaml results/out.json`).
- Execute the full test matrix: `python run_tests.py`; scope to `unit` or `integration` as needed.
- Target a specific suite via unittest discovery, e.g., `python -m unittest tests.unit.test_memory_manager -v`.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indents and type hints on public surfaces.
- Modules/functions use `snake_case`, classes `PascalCase`, and constants `UPPER_CASE`.
- Match existing formatting; add concise comments only when clarifying non-obvious logic.

## Testing Guidelines
- Primary framework is `unittest` (async cases may use `pytest` markers).
- Name tests `test_*` inside `tests/unit` or `tests/integration`; keep fixtures minimal and focused.
- Cover new logic, error paths, and config variants; run `python run_tests.py` before submitting changes.

## Commit & Pull Request Guidelines
- Commits should be imperative and scoped, e.g., `core: fix phase2 retry logic`.
- Branch naming: `feature/<short-description>`, `fix/<issue-id>`, or `chore/<task>`.
- PRs must summarize intent, highlight critical changes, link issues, and include test evidence (command + outcome). Mention config or `.env` impacts.

## Security & Configuration Tips
- Store API keys (e.g., `OPENAI_API_KEY`, `OPENROUTER_API_KEY`) in `.env`; never commit secrets.
- Validate new YAML via `ExperimentConfiguration`; place exemplars under `config/`.
- Keep analysis artifacts in `reports/`; scrub sensitive data before publishing.

## Agent-Specific Instructions
- Add new agents under `experiment_agents/`; keep behavior modular and reusable.
- Expose configuration hooks in `config/` and update `config/default_config.yaml` when defaults change.
- Pair agent updates with unit tests and, when relevant, integration scenarios covering end-to-end flows.
