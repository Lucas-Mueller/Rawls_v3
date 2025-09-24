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

LANGUAGE_REPORT_ENV = "LANGUAGE_REPORT_PATH"
PRIMARY_LANGUAGE_ENV = "LIVE_PRIMARY_LANGUAGE"
ALL_LANGUAGES_ENV = "LIVE_LANGUAGES"
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


def pytest_configure(config):
    for marker, description in (
        ("component", "component-level tests exercising subsystem flows"),
        ("integration", "integration tests covering full experiment"),
        ("unit", "unit tests for pure logic"),
        ("contracts", "contract snapshot tests"),
        ("live", "tests that hit live LLM endpoints"),
        ("requires_openai", "test requires OPENAI_API_KEY for live LLM calls"),
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
    config = build_experiment_configuration(agent_count=1)
    return PromptHarness(config)


@pytest.fixture
def prompt_harness_three_agents(openai_api_key):
    """Prompt harness for scenarios that need three participants."""
    config = build_experiment_configuration(agent_count=3)
    return PromptHarness(config)


def pytest_collection_modifyitems(session, config, items):
    base = Path(config.rootpath)
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

        if layer == "component" and "component" not in marker_names:
            item.add_marker("component")
        elif layer == "integration" and "integration" not in marker_names:
            item.add_marker("integration")
        elif layer == "unit" and "unit" not in marker_names:
            item.add_marker("unit")
        elif layer == "contracts" and "contracts" not in marker_names:
            item.add_marker("contracts")

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
