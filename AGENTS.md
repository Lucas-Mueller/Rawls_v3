# Repository Guidelines

## Project Structure & Modules
- core/: Experiment orchestration (phase managers, distribution generator, original values data).
- experiment_agents/: Participant and utility agents.
- config/: YAML configs and Pydantic models; default at config/default_config.yaml.
- models/: Typed dataclasses/enums for principles, results, logging.
- utils/: Logging, model provider, language manager, memory, error handling, runners.
- tests/: Unit and integration suites under tests/unit and tests/integration.
- docs/, reports/, translations/: Documentation, analysis outputs, and i18n content.
- main.py: CLI entrypoint. run_tests.py: unified test runner.

## Build, Test, and Development
- Environment: Python 3.11+. Create venv and install deps:
  - python -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt
- Run experiment:
  - python main.py                          # uses config/default_config.yaml
  - python main.py config/custom.yaml results/out.json
- Run tests:
  - python run_tests.py                     # import + unit + integration
  - python run_tests.py unit | integration
  - python -m unittest tests.unit.test_memory_manager -v

## Coding Style & Naming
- Python style: PEP 8, 4-space indentation, type hints required for public functions.
- Naming: snake_case for modules/functions, PascalCase for classes, UPPER_CASE for constants.
- Files: keep modules focused and under ~500–800 lines; prefer small helpers in utils/.
- Formatting/Linting: no enforced formatter in repo; match existing style and run tests before PRs.

## Testing Guidelines
- Frameworks: unittest is primary; some tests use pytest markers (asyncio). Prefer unittest discovery.
- Layout: place unit tests in tests/unit/test_*.py and integration tests in tests/integration/test_*.py.
- Coverage: no hard threshold; aim to cover new logic, error paths, and configuration variants.
- Running specific areas: python -m unittest discover -s tests/integration -p 'test_*.py' -v

## Commit & Pull Requests
- Commits: imperative present tense, scoped and concise (e.g., core: fix phase2 retry logic).
- Branches: feature/<short-description>, fix/<issue-id>, chore/<task>.
- PRs: include purpose, key changes, test evidence (commands/output), and any config or .env implications; link issues.

## Security & Configuration
- Secrets: use .env for OPENAI_API_KEY / OPENROUTER_API_KEY; never commit keys.
- Configs: validate YAML via ExperimentConfiguration; prefer adding new examples under config/.
