# Hypothesis 1 Notebook + Runner Changes Report

Date: 2025-08-25

## Summary
- Consolidated and fixed imports in `hypothesis_testing/hypothesis_1/Hypothesis_1_main.ipynb`.
- Added a setup cell to define paths and constants used by the notebook.
- Removed a broken, partial import cell that remained after refactor.
- Adjusted the `runner` utility to launch experiments from the repository root so relative resources (e.g., `translations/`) resolve correctly.
- No changes were made to `main.py`.

## Files Changed
- `hypothesis_testing/hypothesis_1/Hypothesis_1_main.ipynb`
- `hypothesis_testing/utils_hypothesis_testing/runner.py`

## Notebook Changes (Hypothesis_1_main.ipynb)
1) Imports cell (first code cell)
   - Added a small helper that searches upward for the repository root (directory containing both `main.py` and `hypothesis_testing`) and inserts it into `sys.path`.
   - Consolidated all imports used in the notebook:
     - `import sys, os`
     - `from pathlib import Path`
     - `import json, random, shutil, yaml`
     - `from collections import Counter`
     - `import numpy as np`
     - `from scipy.stats import chi2_contingency`
     - `from hypothesis_testing.utils_hypothesis_testing.runner import (list_config_files, select_configs, run_configs_in_parallel)`

   Rationale: ensures local package imports work when the notebook is opened from anywhere, and groups dependencies in one place.

2) Setup cell (inserted immediately after the imports cell)
   - Defines and creates the following directories under the repo root:
     - `CONFIG_DIR = hypothesis_testing/hypothesis_1/configs_hypothesis_1`
     - `LOGS_DIR   = hypothesis_testing/hypothesis_1/logs`
     - `RESULTS_DIR= hypothesis_testing/hypothesis_1/results`
   - Provides placeholders and defaults:
     - `MODEL_LIST = ['gpt-4.1-mini', 'gpt-4o-mini', 'o3-mini', 'gpt-4o']`
     - `INCOME_CLASS_PROBS = {high: 0.05, medium_high: 0.10, medium: 0.50, medium_low: 0.25, low: 0.10}`

   Rationale: this re-introduces the paths and constants needed to generate configs and run/aggregate results in a self-contained way inside the notebook.

3) Removed broken import fragment cell
   - A dangling code cell that only contained the names `list_config_files, select_configs, run_configs_in_parallel` (without the import line) was removed.

4) Behavior restored to match the original instruction
   - The notebook now:
     - Generates 33 YAML configs with required hyperparameters and naming scheme.
     - Runs selected configs in parallel with logs in `hypothesis_testing/hypothesis_1/logs` and results in `hypothesis_testing/hypothesis_1/results`.
     - Analyzes output into the five categories (four principles + disagreement).

## Runner Changes (hypothesis_testing/utils_hypothesis_testing/runner.py)
1) Launch processes from repo root
   - In `_run_single_config(...)`, the `subprocess.Popen` invocation now includes `cwd=str(repo_root)` where `repo_root` is detected by `_repo_root()`.

   Before:
   - Child processes inherited the notebook’s current working directory (often `hypothesis_testing/hypothesis_1`).

   After:
   - Child processes start in the repository root, so relative paths used by the application (e.g., `translations/english_prompts.json` in `utils/language_manager.py`) resolve correctly.

   Rationale: Fixes `FileNotFoundError` for translations when running configs from the notebook utility, without modifying `main.py` or translation loading logic.

## Impact and Compatibility
- Notebook usage: fixed. You can now run config generation, parallel execution, and analysis directly from the notebook.
- CLI usage (`main.py`): unchanged by this patch. Running `main.py` directly continues to depend on your current working directory for resolving relative paths. Recommended usage is to run from the repository root, for example:

  ```bash
  cd /path/to/Rawls_v3
  python main.py config/default_config.yaml experiment_results.json
  ```

  Note: When `main.py` is launched via the notebook runner, the runner ensures the process starts at the repo root to avoid path issues.

## Verification Performed
- Generated sample configs in `hypothesis_testing/hypothesis_1/configs_hypothesis_1`.
- Kicked off two runs via the notebook runner and confirmed the previous translation path error was resolved by setting `cwd` to repo root.
- Verified logs are written to `hypothesis_testing/hypothesis_1/logs` with the specified naming convention and that results are written to `hypothesis_testing/hypothesis_1/results`.

## Notes and Next Steps (Non-code)
- If you plan to run `python main.py ...` from outside the repo root, consider setting your working directory to the repository root to ensure relative resources resolve correctly.
- Update `MODEL_LIST` in the notebook to reflect the exact model identifiers you intend to benchmark.
- Human outcome counts in the analysis cell are placeholders; adjust them to match your source.

