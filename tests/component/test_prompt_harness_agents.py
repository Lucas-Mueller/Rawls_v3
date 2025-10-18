"""Component-level smoke tests for the shared prompt harness."""
from __future__ import annotations

import pytest

from tests.support import (
    parametrize_languages,
)


@parametrize_languages()
@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_prompt_harness_provisions_agents(language, prompt_harness, openai_api_key):
    """The harness should create participants and utility agents per language."""
    seed = prompt_harness.ensure_seed()
    assert isinstance(seed, int)

    participants = await prompt_harness.create_participants(language, agent_count=1)
    assert len(participants) == 1

    participant = participants[0]
    assert participant.config.language == language.value.lower()
    assert participant.experiment_config.language == language.value

    utility_agent = await prompt_harness.create_utility_agent(language)
    assert utility_agent.experiment_language == language.value.lower()

    localized_config = prompt_harness.last_localized_config
    assert localized_config is not None
    assert localized_config.language == language.value
    assert all(agent.language == language.value.lower() for agent in localized_config.agents)
