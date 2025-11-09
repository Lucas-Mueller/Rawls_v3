"""Live component test for the Phase 1 manager using the prompt harness."""
from __future__ import annotations

import pytest

from core.phase1_manager import Phase1Manager
from tests.support import parametrize_languages, capture_process_flow_output
from utils.logging.agent_centric_logger import AgentCentricLogger
from utils.logging.process_flow_logger import create_process_logger


@parametrize_languages()
@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_phase1_manager_runs_with_live_agents(language, prompt_harness, openai_api_key):
    """Run Phase 1 with real agents and ensure core outputs look sane."""
    prompt_harness.ensure_seed()
    participants = await prompt_harness.create_participants(language, agent_count=1)
    assert participants, "Prompt harness should provision at least one participant"

    localized_config = prompt_harness.last_localized_config
    assert localized_config is not None, "Harness should expose localized configuration"

    utility_agent = await prompt_harness.create_utility_agent(language)
    language_manager = prompt_harness.create_language_manager(language)

    manager = Phase1Manager(participants, utility_agent, language_manager, seed_manager=prompt_harness.seed_manager)
    agent_logger = AgentCentricLogger()
    agent_logger.initialize_experiment(participants, localized_config)
    process_logger = create_process_logger("minimal", use_colors=False)

    with capture_process_flow_output(process_logger):
        results = await manager.run_phase1(localized_config, agent_logger, process_logger)

    assert len(results) == 1
    result = results[0]
    assert result.participant_name == participants[0].name
    assert result.total_earnings >= 0
    assert result.final_ranking is not None
    assert result.final_ranking.rankings
