"""Validation tests for preference statement detection letter rejection."""
from __future__ import annotations

import pytest

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple
from utils.language_manager import create_language_manager, SupportedLanguage

pytestmark = pytest.mark.contracts


@pytest.fixture
async def utility_agent():
    manager = create_language_manager(SupportedLanguage.ENGLISH)
    agent = UtilityAgent(experiment_language="english", language_manager=manager)
    await agent.async_init()
    return agent


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "statement",
    [
        "My choice is principle a",
        "Mi elección es principio b",
        "我选择 principle c",
        "I elijo principio d",
    ],
)
async def test_letter_responses_rejected_immediately(utility_agent, statement):
    result = await utility_agent.detect_preference_statement(statement)
    assert result is None


@pytest.mark.asyncio
async def test_valid_preference_detected(monkeypatch, stubbed_runner, utility_agent):
    response = (
        '{"preference_detected": true, "principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}'
    )
    stubbed_runner.register("Response Parser", [response])

    async def _stub(agent, prompt, context=None):
        return await stubbed_runner.run(agent, prompt, context)

    monkeypatch.setattr("experiment_agents.utility_agent.run_without_tracing", _stub)

    result = await utility_agent.detect_preference_statement("I prefer maximizing the floor income")
    assert result is not None
    assert result.principle == JusticePrinciple.MAXIMIZING_FLOOR
