"""Component tests for reasoning toggles and temperature detection."""
from __future__ import annotations

import pytest

from tests.support import parametrize_languages
from tests.support.config_factory import build_experiment_configuration
from tests.support.prompt_harness import PromptHarness
from tests.support.prompt_catalog import get_prompt, PRINCIPLE_CHOICE_SIMPLE


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
@parametrize_languages()
async def test_agent_reasoning_toggle(language, prompt_harness):
    harness = prompt_harness
    harness.ensure_seed()

    participants = await harness.create_participants(language, agent_count=1)
    agent = participants[0]
    assert agent.config.reasoning_enabled

    utility_agent = await harness.create_utility_agent(language)
    sample_prompt = get_prompt(PRINCIPLE_CHOICE_SIMPLE, language)
    result = await utility_agent.parse_principle_choice_enhanced(sample_prompt)
    assert result.principle is not None


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
@parametrize_languages()
async def test_temperature_detection(language):
    config = build_experiment_configuration(agent_count=1, language=language)
    config = config.model_copy(update={"agents": [config.agents[0].model_copy(update={"temperature": 0.8})]})
    harness = PromptHarness(config)
    harness.ensure_seed()

    participants = await harness.create_participants(language, agent_count=1)
    info = participants[0].temperature_info
    assert info is not None
    assert "supports_temperature" in info
