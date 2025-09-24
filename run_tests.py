"""Test runner for the Frohlich Experiment."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).parent
TEST_DIRS = {
    "unit": ROOT / "tests" / "unit",
    "component": ROOT / "tests" / "component",
    "integration": ROOT / "tests" / "integration",
    "contracts": ROOT / "tests" / "contracts",
}
DEFAULT_SEQUENCE: tuple[str, ...] = ("unit", "component", "integration", "contracts", "live")
VALID_TEST_TYPES = set(DEFAULT_SEQUENCE + ("regression", "all"))
REQUIRED_LANGUAGES: tuple[str, ...] = ("english", "spanish", "mandarin")
LANGUAGE_REPORT_ENV = "LANGUAGE_REPORT_PATH"
TRUTHY = {"1", "true", "yes", "on"}
FALSY = {"0", "false", "no", "off"}

# Disable OpenAI Agents SDK tracing for test execution
os.environ.setdefault("OPENAI_AGENTS_DISABLE_TRACING", "1")
os.environ.setdefault("OPENAI_DISABLE_TRACING", "true")

try:  # pragma: no cover - optional helper
    from agents import set_tracing_disabled

    set_tracing_disabled(True)
except ImportError:  # pragma: no cover - optional helper
    pass


def has_pytest() -> bool:
    try:
        import pytest  # type: ignore

        return True
    except ImportError:
        return False


def _pytest_cmd(marker: str | None, path: Path, coverage: bool) -> list[str]:
    cmd = [sys.executable, "-m", "pytest", "-q"]
    if marker:
        cmd.extend(["-m", marker])
    cmd.append(str(path))
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=term-missing"])
    return cmd


def _run_pytest(
    description: str,
    marker: str | None,
    path: Path,
    coverage: bool,
    *,
    enforce_languages: bool = False,
    layer: str | None = None,
) -> bool:
    print(f"Running {description}...")
    if not path.exists():
        print(f"{path} not found; skipping {description}.")
        return True

    env = os.environ.copy()
    report_file: Path | None = None
    if enforce_languages:
        handle = tempfile.NamedTemporaryFile(prefix=f"language_{layer or path.name}_", suffix=".json", delete=False)
        report_file = Path(handle.name)
        handle.close()
        env[LANGUAGE_REPORT_ENV] = str(report_file)
        env.setdefault("LIVE_PRIMARY_LANGUAGE", "english")
        env.setdefault("LIVE_LANGUAGES", "0")

    if has_pytest():
        cmd = _pytest_cmd(marker, path, coverage)
    else:
        print("pytest not available. Falling back to unittest discovery.")
        if coverage:
            print("Coverage reporting requires pytest-cov. Running without coverage.")
        cmd = [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(path),
            "-p",
            "test_*.py",
            "-v",
        ]
        # If pytest is missing there is nothing to enforce
        if enforce_languages:
            report_file = None

    result = subprocess.run(cmd, cwd=ROOT, env=env)
    success = result.returncode == 0

    if report_file is not None:
        success &= _verify_language_report(report_file, layer or path.name)
        try:
            report_file.unlink(missing_ok=True)
        except FileNotFoundError:
            pass

    return success


def run_unit_tests(coverage: bool) -> bool:
    return _run_pytest("unit tests", "unit", TEST_DIRS["unit"], coverage)


def run_component_tests(coverage: bool) -> bool:
    return _run_pytest(
        "component tests",
        "component",
        TEST_DIRS["component"],
        coverage,
        enforce_languages=True,
        layer="component",
    )


def run_integration_tests(coverage: bool) -> bool:
    return _run_pytest("integration tests", "integration", TEST_DIRS["integration"], coverage)


def run_contract_tests(coverage: bool) -> bool:
    return _run_pytest("contract tests", "contracts", TEST_DIRS["contracts"], coverage)


def run_live_tests(coverage: bool) -> bool:
    return _run_pytest(
        "live tests",
        "live",
        TEST_DIRS["component"],
        coverage,
        enforce_languages=True,
        layer="live",
    )


def run_import_test() -> bool:
    print("Testing imports...")
    try:
        from models import JusticePrinciple, IncomeDistribution  # noqa: F401
        from config import ExperimentConfiguration  # noqa: F401
        from core import DistributionGenerator, Phase1Manager, Phase2Manager  # noqa: F401
        from experiment_agents import UtilityAgent, create_participant_agent  # noqa: F401
        from utils import MemoryManager, AgentCentricLogger  # noqa: F401

        dist = IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000)
        assert dist.get_floor_income() == 12000
        assert dist.get_average_income() == 21600

        config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
        assert config.agents

        print("✓ Core imports succeeded")
        return True
    except Exception as exc:  # pragma: no cover - diagnostic helper
        print(f"✗ Import test failed: {exc}")
        import traceback

        traceback.print_exc()
        return False


def parse_args(argv: Iterable[str]) -> tuple[list[str], bool]:
    selections: list[str] = []
    coverage = False
    for arg in argv:
        if arg == "--coverage":
            coverage = True
            continue
        normalized = _normalize_suite(arg)
        if normalized is None:
            _print_invalid_argument(arg)
            sys.exit(2)
        selections.append(normalized)

    if not selections:
        selections = ["all"]

    return _deduplicate(selections), coverage


def should_run_live(explicit: bool | None) -> bool:
    if explicit is not None:
        return explicit
    if os.getenv("OPENAI_API_KEY"):
        return True
    print("Skipping live tests (no OPENAI_API_KEY). Set RUN_LIVE_TESTS=1 to force.")
    return False


def resolve_live_flag() -> bool | None:
    raw = os.getenv("RUN_LIVE_TESTS")
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in TRUTHY:
        return True
    if value in FALSY:
        return False
    print(f"Unrecognized RUN_LIVE_TESTS='{raw}'. Expected one of {sorted(TRUTHY | FALSY)}.")
    return None


def summary(success: bool) -> None:
    print("=" * 60)
    if success:
        print("ALL REQUESTED TESTS PASSED ✓")
    else:
        print("SOME TEST SUITES FAILED ✗")
    print("=" * 60)
    sys.exit(0 if success else 1)


def main() -> None:
    selections, coverage = parse_args(sys.argv[1:])
    plan = _expand_selection(selections)

    print("=" * 60)
    print("FROHLICH EXPERIMENT TEST RUNNER")
    if coverage:
        print("Running with coverage reporting")
    print("=" * 60)

    if not run_import_test():
        summary(False)

    success = True
    print()

    for suite in plan:
        if suite == "unit":
            success &= run_unit_tests(coverage)
        elif suite == "component":
            success &= run_component_tests(coverage)
        elif suite == "integration":
            success &= run_integration_tests(coverage)
        elif suite == "contracts":
            success &= run_contract_tests(coverage)
        elif suite == "live":
            flag = resolve_live_flag()
            if should_run_live(flag):
                success &= run_live_tests(coverage)
            else:
                print("Live tests skipped")
        else:  # pragma: no cover - defensive
            print(f"Unknown suite '{suite}'")
            success = False
        print()

    summary(success)


def _normalize_suite(value: str) -> str | None:
    if value not in VALID_TEST_TYPES:
        return None
    if value == "regression":
        return "contracts"
    return value


def _expand_selection(requested: Sequence[str]) -> list[str]:
    if "all" in requested:
        return list(DEFAULT_SEQUENCE)
    ordered: list[str] = []
    for item in requested:
        if item in DEFAULT_SEQUENCE and item not in ordered:
            ordered.append(item)
    return ordered


def _deduplicate(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def _print_invalid_argument(value: str) -> None:
    expected = ", ".join(sorted(VALID_TEST_TYPES | {"--coverage"}))
    print(f"Unrecognized argument '{value}'. Expected one of: {expected}")


def _verify_language_report(report_path: Path, layer: str) -> bool:
    if not report_path.exists():
        print(f"✗ Expected language report at {report_path} but none was written.")
        return False

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"✗ Language report {report_path} is not valid JSON: {exc}")
        return False

    coverage = payload.get("coverage", {})
    metadata = payload.get("metadata", {})
    layer_data = coverage.get(layer)
    if not layer_data:
        print(f"✗ Language report does not contain entries for layer '{layer}'.")
        return False

    required_languages = _resolve_required_languages(metadata)
    print("Language execution summary:")
    missing: list[str] = []

    for language in required_languages:
        info = layer_data.get(language)
        collected = info.get("collected", 0) if info else 0
        executed = info.get("executed", 0) if info else 0
        skipped = info.get("skipped", 0) if info else 0
        print(f"  - {language:<8} collected={collected:>2} executed={executed:>2} skipped={skipped:>2}")
        if executed == 0:
            missing.append(language)

    if missing:
        print(f"✗ Missing language coverage for: {', '.join(missing)}")
        return False

    print("✓ All required languages executed at least once.")
    return True


def _resolve_required_languages(metadata: dict[str, object]) -> tuple[str, ...]:
    if metadata.get("all_languages_requested"):
        return REQUIRED_LANGUAGES
    primary = metadata.get("primary_language")
    if primary:
        return (str(primary).lower(),)
    return REQUIRED_LANGUAGES


if __name__ == "__main__":
    main()
