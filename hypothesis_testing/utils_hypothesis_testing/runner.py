import os
import sys
import json
import time
import queue
import signal
import shutil
import random
import logging
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List, Optional, Tuple, Dict


logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    """Best-effort detection of the repository root (parent of 'hypothesis_testing')."""
    here = Path(__file__).resolve()
    # runner.py -> utils_hypothesis_testing -> hypothesis_testing -> repo_root
    for p in [here] + list(here.parents):
        if (p / 'hypothesis_testing').is_dir() and (p / 'main.py').exists():
            # 'p' could be repo root or hypothesis_testing; prefer the one with main.py
            if (p / 'main.py').exists():
                return p
    # Fallback to cwd
    return Path.cwd().resolve()


def list_config_files(config_dir: str | Path) -> List[Path]:
    """List YAML config files in a directory, sorted naturally by name.

    Returns absolute Paths.
    """
    import re

    base = Path(config_dir)
    if not base.exists():
        return []

    def sort_key(p: Path) -> tuple[int, str]:
        """Extract numeric condition number for proper sorting."""
        match = re.search(r'condition_(\d+)_config', p.name)
        if match:
            return int(match.group(1)), p.name
        return 0, p.name  # fallback

    files = sorted([p for p in base.iterdir() if p.suffix in {".yml", ".yaml"}], key=sort_key)
    return [p.resolve() for p in files]


def select_configs(
    configs: Iterable[Path],
    include_indices: Optional[Iterable[int]] = None,
    include_names: Optional[Iterable[str]] = None,
) -> List[Path]:
    """Filter a list of config Paths by 1-based indices or name substrings.

    - include_indices: 1-based indices in the sorted list (e.g., [1,5,12])
    - include_names: substrings to match in filenames (without requiring extension)
    If both are None, returns the original list.
    """
    configs = list(configs)
    if include_indices:
        idx_set = {i for i in include_indices}
        by_idx = [cfg for i, cfg in enumerate(configs, start=1) if i in idx_set]
    else:
        by_idx = configs

    if include_names:
        needles = [n.lower() for n in include_names]
        by_name = [
            cfg for cfg in by_idx
            if any(n in cfg.stem.lower() for n in needles)
        ]
    else:
        by_name = by_idx

    return by_name


def _run_single_config(
    config_path: Path,
    logs_dir: Path,
    results_dir: Path,
    python_executable: str,
    timeout_sec: Optional[int] = None,
) -> Tuple[Path, Path, int]:
    """Run one config by invoking main.py and capture logs.

    Returns (log_path, results_path, returncode)
    """
    base_name = config_path.stem  # e.g., hypothesis_1_condition_1_config
    # Logs: exact naming convention without extension
    log_path = logs_dir / base_name.replace("_config", "_log")
    # Results: stable name derived from config
    results_path = results_dir / f"{base_name}_results.json"

    logs_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Always use absolute path to main.py relative to repo root
    main_py = _repo_root() / 'main.py'
    cmd = [python_executable, str(main_py), str(config_path), str(results_path)]

    # Ensure processes run from the repository root so relative paths inside
    # the app (e.g., "translations/english_prompts.json") resolve correctly.
    repo_root = _repo_root()

    with open(log_path, "w") as log_file:
        log_file.write(f"CMD: {' '.join(cmd)}\n")
        log_file.flush()
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
            cwd=str(repo_root),
        )
        start = time.time()
        try:
            for line in proc.stdout:  # type: ignore[attr-defined]
                log_file.write(line)
            proc.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            proc.kill()
            log_file.write("\nPROCESS TIMEOUT — killed by runner.\n")
        finally:
            rc = proc.poll()
            if rc is None:
                rc = -9
        duration = time.time() - start
        log_file.write(f"\nRETURN CODE: {rc}  DURATION: {duration:.1f}s\n")

    return log_path, results_path, rc


def run_configs_in_parallel(
    config_paths: Iterable[Path],
    concurrency: int = 2,
    logs_dir: str | Path = "hypothesis_testing/hypothesis_1/terminal_outputs",
    results_dir: str | Path = "hypothesis_testing/hypothesis_1/results",
    timeout_sec: Optional[int] = None,
    python_executable: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Run multiple configs with a limited concurrency.

    Returns a list of run result dicts with: config, log, result, returncode, ok.
    """
    # Anchor default relative directories to repository root to avoid nested paths in notebooks
    repo = _repo_root()
    logs_dir = Path(logs_dir)
    results_dir = Path(results_dir)
    if not logs_dir.is_absolute():
        logs_dir = (repo / logs_dir).resolve()
    if not results_dir.is_absolute():
        results_dir = (repo / results_dir).resolve()
    python_executable = python_executable or sys.executable

    configs = list(config_paths)
    results: List[Dict[str, object]] = []

    if concurrency < 1:
        concurrency = 1

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        future_map = {
            pool.submit(_run_single_config, cfg, logs_dir, results_dir, python_executable, timeout_sec): cfg
            for cfg in configs
        }
        for fut in as_completed(future_map):
            cfg = future_map[fut]
            try:
                log_path, results_path, rc = fut.result()
                results.append({
                    "config": str(cfg),
                    "log": str(log_path),
                    "result": str(results_path),
                    "returncode": rc,
                    "ok": rc == 0 and results_path.exists(),
                })
            except Exception as e:
                results.append({
                    "config": str(cfg),
                    "log": None,
                    "result": None,
                    "returncode": -1,
                    "ok": False,
                    "error": str(e),
                })

    return results