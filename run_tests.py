"""Test runner for the Frohlich Experiment."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

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

# Enhanced execution modes for Phase 3 implementation
EXECUTION_MODES = {
    "ultra_fast": {
        "description": "Ultra-fast mode: Only unit tests with minimal config (~30 seconds)",
        "test_types": ["unit"],
        "config_override": "config/test_ultra_fast.yaml",
        "language_count": 1,
        "skip_expensive": True,
        "api_calls_estimate": "0",
        "time_estimate": "< 1 minute"
    },
    "dev": {
        "description": "Dev mode: Fast feedback for development (~5 minutes)",
        "test_types": ["unit", "component"],
        "config_override": "config/fast_gpt.yaml",
        "language_count": 1,
        "skip_expensive": True,
        "api_calls_estimate": "20-50",
        "time_estimate": "< 5 minutes"
    },
    "ci": {
        "description": "CI mode: Comprehensive validation for automation (~15 minutes)",
        "test_types": ["unit", "component", "integration"],
        "config_override": "config/default_config.yaml",
        "language_count": 2,
        "skip_expensive": False,
        "api_calls_estimate": "100-200",
        "time_estimate": "< 15 minutes"
    },
    "full": {
        "description": "Full mode: Complete test suite with all optimizations (~30-45 minutes)",
        "test_types": list(DEFAULT_SEQUENCE),
        "config_override": None,
        "language_count": 3,
        "skip_expensive": False,
        "api_calls_estimate": "300-500",
        "time_estimate": "30-45 minutes"
    }
}

# Performance tracking globals
performance_stats = {
    "api_calls_made": 0,
    "tests_executed": 0,
    "suites_run": [],
    "config_used": None,
    "mode_used": None
}

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

    # Start timing
    start_time = time.time()

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

    # Report timing
    elapsed = time.time() - start_time
    print(f"✓ {description} completed in {elapsed:.2f}s")

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


def create_argument_parser() -> argparse.ArgumentParser:
    """Create enhanced argument parser for Phase 3 intelligent execution modes."""
    parser = argparse.ArgumentParser(
        description="Frohlich Experiment Test Runner - Enhanced with intelligent execution modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_get_usage_examples()
    )

    # Mode-based execution (primary interface)
    parser.add_argument(
        "--mode",
        choices=list(EXECUTION_MODES.keys()),
        help="Intelligent execution mode with optimized configurations"
    )

    # Advanced configuration options
    parser.add_argument(
        "--config",
        help="Override configuration file (takes precedence over mode-based config)"
    )

    parser.add_argument(
        "--languages",
        type=int,
        choices=[1, 2, 3],
        help="Number of languages to test (1=English only, 2=English+Spanish, 3=All)"
    )

    # Legacy interface (backward compatibility)
    parser.add_argument(
        "test_types",
        nargs="*",
        help="Specific test types to run (for backward compatibility)"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Enable coverage reporting"
    )

    # Performance and reporting options
    parser.add_argument(
        "--performance-report",
        action="store_true",
        help="Generate detailed performance report"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running tests"
    )

    return parser


def parse_args(argv: Iterable[str]) -> Dict[str, any]:
    """Enhanced argument parsing with mode-based configuration."""
    parser = create_argument_parser()

    # Handle legacy format (no -- arguments, just test types)
    argv_list = list(argv)
    if argv_list and not any(arg.startswith('--') or arg.startswith('-') for arg in argv_list):
        # Legacy mode: convert to new format
        selections, coverage = _parse_legacy_args(argv_list)
        return {
            "mode": None,
            "test_types": selections,
            "coverage": coverage,
            "config": None,
            "languages": None,
            "performance_report": False,
            "dry_run": False
        }

    args = parser.parse_args(argv_list)

    # Resolve test types based on mode or explicit specification
    if args.mode:
        test_types = EXECUTION_MODES[args.mode]["test_types"]
    elif args.test_types:
        test_types = _process_legacy_test_types(args.test_types)
    else:
        test_types = ["all"]

    return {
        "mode": args.mode,
        "test_types": test_types,
        "coverage": args.coverage,
        "config": args.config,
        "languages": args.languages,
        "performance_report": args.performance_report,
        "dry_run": args.dry_run
    }


def _parse_legacy_args(argv: list[str]) -> tuple[list[str], bool]:
    """Parse legacy argument format for backward compatibility."""
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


def _process_legacy_test_types(test_types: list[str]) -> list[str]:
    """Process explicit test types with validation."""
    processed = []
    for test_type in test_types:
        normalized = _normalize_suite(test_type)
        if normalized is None:
            _print_invalid_argument(test_type)
            sys.exit(2)
        processed.append(normalized)
    return _deduplicate(processed)


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


def generate_performance_report(total_time: float, suites_run: list[str], detailed: bool = False) -> None:
    """Generate enhanced performance report with API usage and timing analysis."""
    global performance_stats

    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)

    # Basic execution stats
    print(f"Total Execution Time: {total_time:.2f}s ({_format_duration(total_time)})")
    print(f"Suites Executed: {', '.join(suites_run)} ({len(suites_run)} total)")

    if suites_run:
        avg_time = total_time / len(suites_run)
        print(f"Average Time per Suite: {avg_time:.2f}s")

    # Mode-specific analysis
    if performance_stats["mode_used"]:
        mode_config = EXECUTION_MODES[performance_stats["mode_used"]]
        print(f"\nExecution Mode: {performance_stats['mode_used'].upper()}")
        print(f"Expected Duration: {mode_config['time_estimate']}")
        print(f"Actual vs Expected: {_compare_performance(total_time, mode_config['time_estimate'])}")
        print(f"Estimated API Calls: {mode_config['api_calls_estimate']}")

    # Configuration info
    if performance_stats["config_used"]:
        print(f"Configuration Used: {performance_stats['config_used']}")

    # Detailed breakdown
    if detailed:
        print("\n" + "-" * 50)
        print("DETAILED PERFORMANCE BREAKDOWN")
        print("-" * 50)

        # Time per suite would need to be tracked during execution
        # This is a placeholder for enhanced tracking
        for suite in suites_run:
            print(f"  {suite}: [timing would be tracked here]")

        # Environment variables set
        print("\nEnvironment Configuration:")
        relevant_env_vars = [
            "TEST_CONFIG_OVERRIDE",
            "LIVE_LANGUAGES",
            "SKIP_EXPENSIVE_TESTS",
            "RUN_LIVE_TESTS"
        ]
        for var in relevant_env_vars:
            value = os.environ.get(var, "(not set)")
            print(f"  {var}: {value}")

    print("=" * 70)


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def _compare_performance(actual_seconds: float, expected_description: str) -> str:
    """Compare actual performance against expected time description."""
    # Parse expected time ranges
    if "< 1 minute" in expected_description or "30 seconds" in expected_description:
        expected_max = 60
    elif "< 5 minutes" in expected_description:
        expected_max = 300
    elif "< 15 minutes" in expected_description:
        expected_max = 900
    elif "30-45 minutes" in expected_description:
        expected_max = 2700
    else:
        return "within expectations"

    if actual_seconds <= expected_max:
        improvement = ((expected_max - actual_seconds) / expected_max) * 100
        return f"✓ {improvement:.0f}% faster than expected"
    else:
        slowdown = ((actual_seconds - expected_max) / expected_max) * 100
        return f"⚠ {slowdown:.0f}% slower than expected"


def summary(success: bool, total_time: float = 0) -> None:
    print("\n" + "=" * 70)
    if success:
        print("🎉 ALL REQUESTED TESTS PASSED ✓")

        # Provide mode-specific success messaging
        if performance_stats["mode_used"]:
            mode = performance_stats["mode_used"]
            if mode == "ultra_fast":
                print("   Ultra-fast feedback complete - ready for continued development!")
            elif mode == "dev":
                print("   Development validation complete - safe to commit!")
            elif mode == "ci":
                print("   CI validation complete - ready for deployment!")
            elif mode == "full":
                print("   Full test suite complete - comprehensive validation successful!")
    else:
        print("❌ SOME TEST SUITES FAILED ✗")

        # Provide guidance on failure
        if performance_stats["mode_used"] in ["ultra_fast", "dev"]:
            print("   Consider running --mode ci for more comprehensive validation")
        elif performance_stats["mode_used"] == "ci":
            print("   Run --mode full for complete analysis before release")

    if total_time > 0:
        print(f"\nTotal execution time: {total_time:.2f}s ({_format_duration(total_time)})")

    print("=" * 70)
    sys.exit(0 if success else 1)


def setup_execution_environment(parsed_args: Dict[str, any]) -> Dict[str, any]:
    """Configure execution environment based on parsed arguments and mode."""
    global performance_stats

    # Determine configuration
    config_override = None
    language_count = 3  # Default to full multilingual
    skip_expensive = False

    if parsed_args["mode"]:
        mode_config = EXECUTION_MODES[parsed_args["mode"]]
        config_override = mode_config["config_override"]
        language_count = mode_config["language_count"]
        skip_expensive = mode_config["skip_expensive"]
        performance_stats["mode_used"] = parsed_args["mode"]

    # Override with explicit arguments
    if parsed_args["config"]:
        config_override = parsed_args["config"]

    if parsed_args["languages"]:
        language_count = parsed_args["languages"]

    performance_stats["config_used"] = config_override

    # Set environment variables for existing test infrastructure
    # NOTE: Be careful with TEST_CONFIG_OVERRIDE as it affects config factory behavior
    env_config = {
        "LIVE_LANGUAGES": "1" if language_count > 1 else "0",
        "SKIP_EXPENSIVE_TESTS": "1" if skip_expensive else "0",
        "TEST_PERFORMANCE_TRACKING": "1" if parsed_args["performance_report"] else "0"
    }

    # Only set config override for non-unit tests to avoid interfering with unit tests
    # that test the config factory logic directly
    if config_override and parsed_args["mode"] and "unit" not in parsed_args.get("test_types", []):
        env_config["TEST_CONFIG_OVERRIDE"] = config_override

    for key, value in env_config.items():
        if value:
            os.environ[key] = value

    return {
        "config_override": config_override,
        "language_count": language_count,
        "skip_expensive": skip_expensive,
        "env_config": env_config
    }


def print_execution_banner(parsed_args: Dict[str, any], setup_config: Dict[str, any]) -> None:
    """Print enhanced execution banner with mode and configuration info."""
    print("=" * 70)
    print("FROHLICH EXPERIMENT TEST RUNNER - ENHANCED (Phase 3)")

    if parsed_args["mode"]:
        mode_config = EXECUTION_MODES[parsed_args["mode"]]
        print(f"Execution Mode: {parsed_args['mode'].upper()}")
        print(f"Description: {mode_config['description']}")
        print(f"Expected API Calls: {mode_config['api_calls_estimate']}")
        print(f"Expected Duration: {mode_config['time_estimate']}")
    else:
        print("Execution Mode: LEGACY (backward compatibility)")

    if setup_config["config_override"]:
        print(f"Configuration Override: {setup_config['config_override']}")

    print(f"Language Testing: {setup_config['language_count']} language(s)")

    if parsed_args["coverage"]:
        print("Coverage Reporting: ENABLED")

    if parsed_args["performance_report"]:
        print("Performance Reporting: ENABLED")

    if setup_config["skip_expensive"]:
        print("Expensive Tests: SKIPPED (for speed)")

    print("=" * 70)


def handle_dry_run(parsed_args: Dict[str, any], plan: list[str]) -> None:
    """Handle dry run mode by showing execution plan without running tests."""
    print("\n🔍 DRY RUN MODE - Showing execution plan without running tests")
    print("-" * 50)

    if parsed_args["mode"]:
        mode_config = EXECUTION_MODES[parsed_args["mode"]]
        print(f"Mode: {parsed_args['mode']}")
        print(f"Expected Duration: {mode_config['time_estimate']}")
        print(f"Expected API Calls: {mode_config['api_calls_estimate']}")

    print(f"\nTest Suites to Execute: {len(plan)}")
    for i, suite in enumerate(plan, 1):
        print(f"  {i}. {suite}")

    if parsed_args["coverage"]:
        print("\nCoverage reporting would be enabled")

    print("\n✓ Dry run complete. Use without --dry-run to execute.")
    sys.exit(0)


def main() -> None:
    parsed_args = parse_args(sys.argv[1:])

    # Handle help and mode listing
    if not parsed_args["mode"] and not parsed_args["test_types"]:
        create_argument_parser().print_help()
        sys.exit(0)

    # Setup execution environment
    setup_config = setup_execution_environment(parsed_args)

    # Determine execution plan
    plan = _expand_selection(parsed_args["test_types"])

    # Handle dry run
    if parsed_args["dry_run"]:
        handle_dry_run(parsed_args, plan)

    # Start overall timing
    start_time = time.time()

    # Print enhanced banner
    print_execution_banner(parsed_args, setup_config)

    if not run_import_test():
        summary(False)

    success = True
    suites_run = []
    print()

    for suite in plan:
        if suite == "unit":
            success &= run_unit_tests(parsed_args["coverage"])
            suites_run.append(suite)
        elif suite == "component":
            success &= run_component_tests(parsed_args["coverage"])
            suites_run.append(suite)
        elif suite == "integration":
            success &= run_integration_tests(parsed_args["coverage"])
            suites_run.append(suite)
        elif suite == "contracts":
            success &= run_contract_tests(parsed_args["coverage"])
            suites_run.append(suite)
        elif suite == "live":
            flag = resolve_live_flag()
            if should_run_live(flag):
                success &= run_live_tests(parsed_args["coverage"])
                suites_run.append(suite)
            else:
                print("Live tests skipped")
        else:  # pragma: no cover - defensive
            print(f"Unknown suite '{suite}'")
            success = False
        print()

    # Calculate total time and provide enhanced performance summary
    total_time = time.time() - start_time
    performance_stats["tests_executed"] = len(suites_run)
    performance_stats["suites_run"] = suites_run

    generate_performance_report(total_time, suites_run, parsed_args["performance_report"])
    summary(success, total_time)


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


def _get_usage_examples() -> str:
    """Generate usage examples and mode descriptions."""
    examples = []
    examples.append("\nEXECUTION MODES:")

    for mode_name, mode_config in EXECUTION_MODES.items():
        examples.append(f"\n  {mode_name.upper()}:")
        examples.append(f"    Description: {mode_config['description']}")
        examples.append(f"    Test Types: {', '.join(mode_config['test_types'])}")
        examples.append(f"    API Calls: {mode_config['api_calls_estimate']}")
        examples.append(f"    Time: {mode_config['time_estimate']}")

    examples.append("\nUSAGE EXAMPLES:")
    examples.append("\n  # Ultra-fast development feedback")
    examples.append("  python run_tests.py --mode ultra_fast")
    examples.append("\n  # Development workflow (most common)")
    examples.append("  python run_tests.py --mode dev")
    examples.append("\n  # CI/CD pipeline")
    examples.append("  python run_tests.py --mode ci")
    examples.append("\n  # Complete validation before release")
    examples.append("  python run_tests.py --mode full")
    examples.append("\n  # Custom configuration")
    examples.append("  python run_tests.py --mode dev --config config/custom.yaml")
    examples.append("\n  # Performance analysis")
    examples.append("  python run_tests.py --mode ci --performance-report")
    examples.append("\n  # Legacy format (backward compatible)")
    examples.append("  python run_tests.py unit component")

    return "\n".join(examples)


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
