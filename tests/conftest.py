"""Shared pytest fixtures for the Frohlich Experiment test suite."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import httpx

from tests.support import PromptHarness, build_experiment_configuration
from dotenv import load_dotenv


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
        top_level = rel_parts[1]
        marker_names = {mark.name for mark in item.iter_markers()}
        if top_level == "component" and "component" not in marker_names:
            item.add_marker("component")
        elif top_level == "integration" and "integration" not in marker_names:
            item.add_marker("integration")
        elif top_level == "unit" and "unit" not in marker_names:
            item.add_marker("unit")
        elif top_level == "contracts" and "contracts" not in marker_names:
            item.add_marker("contracts")
