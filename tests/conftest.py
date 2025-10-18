"""Shared pytest fixtures for the Frohlich Experiment test suite."""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Tuple

import httpx
import pytest

from dotenv import load_dotenv
from tests.support import PromptHarness, build_experiment_configuration

MODE_MARKERS = {
    "ultra_fast": {"unit", "fast"},
    "dev": {"unit", "component"},
    "ci": {"unit", "component", "integration"},
    "full": {"unit", "component", "integration", "contracts", "live"},
}

LANGUAGE_REPORT_ENV = "LANGUAGE_REPORT_PATH"
PRIMARY_LANGUAGE_ENV = "LIVE_PRIMARY_LANGUAGE"
ALL_LANGUAGES_ENV = "LIVE_LANGUAGES"
# Test acceleration environment variables
FULL_INTEGRATION_TESTS_ENV = "FULL_INTEGRATION_TESTS"
DEVELOPMENT_MODE_ENV = "DEVELOPMENT_MODE"
TEST_CONFIG_OVERRIDE_ENV = "TEST_CONFIG_OVERRIDE"
SKIP_EXPENSIVE_TESTS_ENV = "SKIP_EXPENSIVE_TESTS"
TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _language_entry_factory() -> Dict[str, Any]:
    return {
        "collected": 0,
        "executed": 0,
        "skipped": 0,
        "contains_live": False,
        "skip_reasons": set(),
        "nodeids": [],
    }


LANGUAGE_ITEM_CONTEXT: Dict[str, Tuple[str, str]] = {}
LANGUAGE_COVERAGE: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(_language_entry_factory))


def pytest_addoption(parser):
    """Register CLI options for suite selection."""
    group = parser.getgroup("suite selection")
    group.addoption(
        "--mode",
        choices=tuple(MODE_MARKERS.keys()),
        help="Preset test selection (ultra_fast, dev, ci, full).",
    )


def pytest_configure(config):
    for marker, description in (
        ("component", "component-level tests exercising subsystem flows"),
        ("integration", "integration tests covering full experiment"),
        ("unit", "unit tests for pure logic"),
        ("contracts", "contract snapshot tests"),
        ("live", "tests that hit live LLM endpoints"),
        ("requires_openai", "test requires OPENAI_API_KEY for live LLM calls"),
        ("expensive", "expensive tests that may be skipped in development mode"),
        ("fast", "fast tests suitable for development workflows"),
    ):
        config.addinivalue_line("markers", f"{marker}: {description}")


@pytest.fixture(scope="session")
def openai_api_key():
    """Ensure live LLM credentials are present before executing dependent tests."""
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set; skipping live LLM-dependent tests.")

    try:
        response = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=2.0,
        )
        if response.status_code == 401:
            pytest.skip("OPENAI_API_KEY rejected (401). Configure a valid key to run live tests.")
        if response.status_code >= 500 or response.status_code == 0:
            pytest.skip(f"OpenAI API unavailable (status {response.status_code}).")
    except httpx.HTTPError as exc:
        pytest.skip(f"OpenAI API unreachable: {exc}")

    return key


@pytest.fixture
def prompt_harness(openai_api_key):
    """Provide a prompt harness backed by a slim experiment configuration."""
    from tests.support.config_factory import build_configuration_for_test_mode
    from utils.language_manager import SupportedLanguage

    # Use configuration override if available, otherwise use development mode
    config_override = _get_test_config_override()
    if config_override:
        try:
            from tests.support.config_factory import load_base_configuration, clone_config_with_language
            config = load_base_configuration(config_override)
            config = clone_config_with_language(config, SupportedLanguage.ENGLISH, agent_count=1)
        except FileNotFoundError:
            # Fall back to test mode configuration
            config = build_configuration_for_test_mode("dev", agent_count=1)
    else:
        config = build_configuration_for_test_mode("dev", agent_count=1)

    return PromptHarness(config)


@pytest.fixture
def prompt_harness_three_agents(openai_api_key):
    """Prompt harness for scenarios that need three participants."""
    from tests.support.config_factory import build_configuration_for_test_mode
    from utils.language_manager import SupportedLanguage

    # Use configuration override if available, otherwise use development mode
    config_override = _get_test_config_override()
    if config_override:
        try:
            from tests.support.config_factory import load_base_configuration, clone_config_with_language
            config = load_base_configuration(config_override)
            config = clone_config_with_language(config, SupportedLanguage.ENGLISH, agent_count=3)
        except FileNotFoundError:
            # Fall back to test mode configuration
            config = build_configuration_for_test_mode("dev", agent_count=3)
    else:
        config = build_configuration_for_test_mode("dev", agent_count=3)

    return PromptHarness(config)


def pytest_collection_modifyitems(session, config, items):
    base = Path(config.rootpath)
    skip_expensive = _skip_expensive_tests()
    development_mode = _is_development_mode()
    requested_mode = config.getoption("mode")
    enabled_markers = MODE_MARKERS.get(requested_mode, set())

    for item in items:
        try:
            path = Path(item.fspath)
        except AttributeError:
            continue
        if "tests" not in path.parts:
            continue
        rel_parts = path.relative_to(base).parts
        if len(rel_parts) < 2:
            continue
        layer = rel_parts[1]
        marker_names = {mark.name for mark in item.iter_markers()}
        fixturenames = getattr(item, "fixturenames", ())

        # Add layer-based markers automatically
        if layer == "component" and "component" not in marker_names:
            item.add_marker("component")
            marker_names.add("component")
        elif layer == "integration" and "integration" not in marker_names:
            item.add_marker("integration")
            marker_names.add("integration")
        elif layer == "unit" and "unit" not in marker_names:
            item.add_marker("unit")
            marker_names.add("unit")
        elif layer == "contracts" and "contracts" not in marker_names:
            item.add_marker("contracts")
            marker_names.add("contracts")
        elif layer == "fast" and "fast" not in marker_names:
            item.add_marker("fast")
            marker_names.add("fast")
        else:
            if "unit" not in marker_names:
                item.add_marker("unit")
                marker_names.add("unit")

        # Auto-mark expensive tests based on layer and existing markers
        if layer in ["component", "integration"] and "live" in marker_names:
            if "expensive" not in marker_names:
                item.add_marker("expensive")

        # Skip expensive tests if configured
        if skip_expensive and "expensive" in marker_names:
            item.add_marker(pytest.mark.skip(reason="Expensive test skipped (SKIP_EXPENSIVE_TESTS=1)"))

        # In development mode, skip comprehensive integration tests unless explicitly enabled
        if (development_mode and not _is_full_integration_enabled() and
            layer == "integration" and "live" in marker_names):
            item.add_marker(pytest.mark.skip(reason="Integration test skipped in development mode"))

        if requested_mode and not enabled_markers.intersection(marker_names):
            item.add_marker(
                pytest.mark.skip(reason=f"Excluded by --mode={requested_mode} preset")
            )

        if "language" not in fixturenames or not hasattr(item, "callspec"):
            continue

        language_param = item.callspec.params.get("language")
        language_name = _normalise_language(language_param)
        entry = LANGUAGE_COVERAGE[layer][language_name]
        entry["collected"] += 1
        entry["nodeids"].append(item.nodeid)
        if "live" in marker_names:
            entry["contains_live"] = True

        LANGUAGE_ITEM_CONTEXT[item.nodeid] = (layer, language_name)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    context = LANGUAGE_ITEM_CONTEXT.get(report.nodeid)
    if not context:
        return
    layer, language = context
    entry = LANGUAGE_COVERAGE[layer][language]

    if report.skipped:
        entry["skipped"] += 1
        reason = _extract_skip_reason(report)
        if reason:
            entry["skip_reasons"].add(reason)
        return

    if report.when == "call" and report.outcome in {"passed", "failed"}:
        entry["executed"] += 1


def pytest_sessionfinish(session, exitstatus):
    report_path = os.getenv(LANGUAGE_REPORT_ENV)
    if not report_path:
        return

    metadata = {
        "primary_language": _resolve_primary_language(),
        "all_languages_requested": _all_languages_requested(),
    }

    payload = {
        "coverage": {
            layer: {
                language: {
                    "collected": data["collected"],
                    "executed": data["executed"],
                    "skipped": data["skipped"],
                    "contains_live": data["contains_live"],
                    "skip_reasons": sorted(data["skip_reasons"]),
                }
                for language, data in languages.items()
            }
            for layer, languages in LANGUAGE_COVERAGE.items()
        },
        "metadata": metadata,
    }

    Path(report_path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _normalise_language(value: Any) -> str:
    if hasattr(value, "name"):
        return str(value.name).lower()
    if hasattr(value, "value"):
        candidate = getattr(value, "value")
        if isinstance(candidate, str):
            return candidate.lower()
    return str(value).lower()


def _extract_skip_reason(report: pytest.TestReport) -> str | None:
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2])
    if hasattr(longrepr, "reprcrash") and getattr(longrepr, "reprcrash") is not None:
        return str(longrepr.reprcrash.message)
    if hasattr(longrepr, "message"):
        return str(longrepr.message)
    return str(longrepr) if longrepr else None


def _resolve_primary_language() -> str | None:
    focus = os.getenv(PRIMARY_LANGUAGE_ENV)
    if not focus:
        return None
    return focus.strip().lower()


def _all_languages_requested() -> bool:
    raw = os.getenv(ALL_LANGUAGES_ENV)
    if raw is None:
        return False
    return raw.strip().lower() in TRUTHY_VALUES


def _is_development_mode() -> bool:
    """Check if we're in development mode (default True)."""
    raw = os.getenv(DEVELOPMENT_MODE_ENV, "1")  # Default to development mode
    return raw.strip().lower() in TRUTHY_VALUES


def _is_full_integration_enabled() -> bool:
    """Check if full integration tests are enabled."""
    raw = os.getenv(FULL_INTEGRATION_TESTS_ENV, "0")  # Default to disabled
    return raw.strip().lower() in TRUTHY_VALUES


def _skip_expensive_tests() -> bool:
    """Check if expensive tests should be skipped."""
    raw = os.getenv(SKIP_EXPENSIVE_TESTS_ENV, "0")  # Default to run expensive tests
    return raw.strip().lower() in TRUTHY_VALUES


def _get_test_config_override() -> str | None:
    """Get configuration override from environment variable."""
    override = os.getenv(TEST_CONFIG_OVERRIDE_ENV)
    if override and override.strip():
        return override.strip()
    return None
