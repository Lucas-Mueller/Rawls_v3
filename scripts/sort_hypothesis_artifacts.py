#!/usr/bin/env python3
"""
Sort misplaced transcripts and results into the correct hypothesis folders.

Usage examples:
  Dry run (default):
    python scripts/sort_hypothesis_artifacts.py

  Apply changes:
    python scripts/sort_hypothesis_artifacts.py --apply

  Verbose output:
    python scripts/sort_hypothesis_artifacts.py --apply --verbose
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List


# Root-level patterns to gather candidates
TRANSCRIPT_ROOT_GLOB = "transcript_*.json"
RESULTS_ROOT_GLOB = "experiment_results_*.json"


@dataclass
class ArtifactMeta:
    kind: str  # "transcript" | "results"
    source_path: Path
    hypothesis_folder: str  # e.g., "hypothesis_2" or "reproducability_proof"
    subgroup: Optional[str]  # e.g., "chinese", "high", "english"; None if not applicable
    condition: str  # numeric string for most; for reproducibility, also numeric
    dest_dir: Path
    dest_filename: str


def _parse_config_info_from_transcript(json_data: dict) -> Tuple[Optional[Path], Optional[str]]:
    meta = json_data.get("experiment_metadata", {})
    config_file = meta.get("config_file")
    if not config_file:
        return None, None
    return Path(config_file), Path(config_file).name


def _parse_config_info_from_results(json_data: dict) -> Tuple[Optional[Path], Optional[str]]:
    # Results store only the basename under general_information.config_file_used in most cases
    gi = json_data.get("general_information", {})
    cfg_used = gi.get("config_file_used")
    if not cfg_used:
        return None, None
    return None, Path(cfg_used)


def _infer_hypothesis_folder_and_subgroup(config_path: Optional[Path], config_name: Path) -> Tuple[str, Optional[str]]:
    """
    Determine hypothesis folder and subgroup.
    - If config_path is provided, prefer folder parts under hypothesis_testing/.../configs
    - Fallback to parsing from config filename
    """
    # Case 1: reproducability_proof
    if config_path and "reproducability_proof" in config_path.parts:
        return "reproducability_proof", None

    # Case 2: infer from path parts when available
    if config_path:
        try:
            idx = config_path.parts.index("hypothesis_testing")
            # Expect: hypothesis_testing/<hypothesis_folder>/configs/(optional subgroup)/<file>
            hypothesis_folder = config_path.parts[idx + 1]
            # Detect subgroup: the entry after "configs" if present
            subgroup = None
            for i, part in enumerate(config_path.parts):
                if part == "configs":
                    # If another directory exists before filename, treat it as subgroup
                    if i + 2 < len(config_path.parts):
                        maybe_sub = config_path.parts[i + 1]
                        # Guard: only treat as subgroup if it's a directory name, not the filename
                        if maybe_sub != config_path.name:
                            subgroup = maybe_sub
                    break
            return hypothesis_folder, subgroup
        except (ValueError, IndexError):
            pass

    # Case 3: parse from filename when path context is absent (results)
    # Patterns like: hypothesis_2_chinese_condition_19_config.yaml
    m = re.match(r"^(hypothesis_\d+)(?:_([a-z_]+))?_condition_(\d+)_config\.ya?ml$", config_name.name)
    if m:
        hypothesis_folder = m.group(1)
        subgroup = m.group(2)
        return hypothesis_folder, subgroup

    # Reproducibility config filename pattern
    m2 = re.match(r"^reproducibility_condition_(\d+)_config\.ya?ml$", config_name.name)
    if m2:
        return "reproducability_proof", None

    raise ValueError(f"Unable to infer hypothesis/subgroup from config: {config_path or config_name}")


def _extract_condition(config_path: Optional[Path], config_name: Path) -> str:
    # Prefer filename-based extraction
    name = config_name.name

    m = re.search(r"condition_(\d+)_config", name)
    if m:
        return m.group(1)

    # Reproducibility
    m2 = re.search(r"reproducibility_condition_(\d+)_config", name)
    if m2:
        return m2.group(1)

    # Last resort: try to find "condition_X" in any part of the path
    if config_path is not None:
        m3 = re.search(r"condition_(\d+)", str(config_path))
        if m3:
            return m3.group(1)

    raise ValueError(f"Unable to determine condition from config: {config_path or config_name}")


def _dest_components(kind: str, hypothesis_folder: str, subgroup: Optional[str], config_name: Path, condition: str) -> Tuple[Path, str]:
    repo_root = Path(__file__).resolve().parents[1]
    base = repo_root / "hypothesis_testing" / hypothesis_folder

    if kind == "transcript":
        subdir = base / "transcripts"
        if subgroup:
            subdir = subdir / subgroup
        # transcripts: hypothesis_<N>_<subgroup?>_condition_<K>_transcript.json
        # Build prefix from hypothesis_folder and subgroup
        parts: List[str] = [hypothesis_folder]
        if subgroup:
            parts.append(subgroup)
        parts.append(f"condition_{condition}")
        filename = "_".join(parts) + "_transcript.json"
        return subdir, filename

    if kind == "results":
        subdir = base / "results"
        if subgroup:
            subdir = subdir / subgroup
        # results: hypothesis_<N>_<subgroup?>_condition_<K>_config_results.json
        parts = [hypothesis_folder]
        if subgroup:
            parts.append(subgroup)
        parts.append(f"condition_{condition}")
        filename = "_".join(parts) + "_config_results.json"
        return subdir, filename

    raise ValueError(f"Unknown kind: {kind}")


def _gather_root_candidates(repo_root: Path) -> Tuple[List[Path], List[Path]]:
    transcripts = sorted(repo_root.glob(TRANSCRIPT_ROOT_GLOB))
    results = sorted(repo_root.glob(RESULTS_ROOT_GLOB))
    # Only consider files actually at the repo root, not subdirectories
    transcripts = [p for p in transcripts if p.parent == repo_root]
    results = [p for p in results if p.parent == repo_root]
    return transcripts, results


def _analyze_transcript(path: Path) -> ArtifactMeta:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    config_path, config_name = _parse_config_info_from_transcript(data)
    if not config_name:
        raise ValueError(f"Transcript missing config reference: {path}")
    hypothesis_folder, subgroup = _infer_hypothesis_folder_and_subgroup(config_path, Path(config_name))
    condition = _extract_condition(config_path, Path(config_name))
    dest_dir, dest_filename = _dest_components("transcript", hypothesis_folder, subgroup, Path(config_name), condition)
    return ArtifactMeta("transcript", path, hypothesis_folder, subgroup, condition, dest_dir, dest_filename)


def _analyze_results(path: Path) -> ArtifactMeta:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    config_path, config_name = _parse_config_info_from_results(data)
    if not config_name:
        raise ValueError(f"Results missing config reference: {path}")
    hypothesis_folder, subgroup = _infer_hypothesis_folder_and_subgroup(config_path, Path(config_name))
    condition = _extract_condition(config_path, Path(config_name))
    dest_dir, dest_filename = _dest_components("results", hypothesis_folder, subgroup, Path(config_name), condition)
    return ArtifactMeta("results", path, hypothesis_folder, subgroup, condition, dest_dir, dest_filename)


def _move_file(meta: ArtifactMeta, apply: bool, overwrite: bool, verbose: bool) -> Tuple[bool, str]:
    src = meta.source_path
    dst_dir = meta.dest_dir
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / meta.dest_filename

    if dst.exists() and not overwrite:
        return False, f"SKIP exists: {src.name} -> {dst}"

    if not apply:
        return True, f"DRY-RUN: {src.name} -> {dst}"

    # Preserve times if possible
    try:
        stat = src.stat()
    except OSError:
        stat = None

    # Perform move
    if dst.exists() and overwrite:
        if verbose:
            print(f"Overwriting existing {dst}")
        dst.unlink()

    shutil.move(str(src), str(dst))

    if stat is not None:
        try:
            os.utime(dst, (stat.st_atime, stat.st_mtime))
        except OSError:
            pass

    return True, f"MOVED: {src.name} -> {dst}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sort misplaced transcripts/results into hypothesis folders")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root path")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite destination if it exists")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    repo_root: Path = args.root
    transcripts, results = _gather_root_candidates(repo_root)

    planned: List[ArtifactMeta] = []
    problems: List[str] = []

    for t in transcripts:
        try:
            planned.append(_analyze_transcript(t))
        except Exception as e:
            problems.append(f"Transcript {t.name}: {e}")

    for r in results:
        try:
            planned.append(_analyze_results(r))
        except Exception as e:
            problems.append(f"Results {r.name}: {e}")

    if args.verbose:
        print(f"Found {len(transcripts)} transcripts, {len(results)} results at root")
        if problems:
            print("Issues detected:")
            for p in problems:
                print(f" - {p}")

    # Execute moves (or dry-run)
    successes = 0
    for meta in planned:
        ok, msg = _move_file(meta, apply=args.apply, overwrite=args.overwrite, verbose=args.verbose)
        print(msg)
        if ok:
            successes += 1

    print(f"Done. {successes}/{len(planned)} processed. {'APPLIED' if args.apply else 'DRY-RUN'} mode.")

    if problems:
        print(f"Encountered {len(problems)} issues. See above.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


