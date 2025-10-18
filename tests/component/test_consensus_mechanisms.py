"""Component tests for Phase 2 consensus behaviour."""
from __future__ import annotations

import pytest

from core.phase2_manager import Phase2Manager
from core.phase1_manager import Phase1Manager
from tests.support import capture_process_flow_output, parametrize_languages
from utils.logging.agent_centric_logger import AgentCentricLogger
from utils.logging.process_flow_logger import create_process_logger
from tests.support.prompt_harness import PromptHarness
from tests.support.config_factory import build_experiment_configuration


def _consensus_harness() -> PromptHarness:
    config = build_experiment_configuration(agent_count=3)
    return PromptHarness(config)


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
@parametrize_languages()
async def test_phase2_consensus(language, prompt_harness_three_agents):
    harness = prompt_harness_three_agents
    harness.ensure_seed()

    participants = await harness.create_participants(language, agent_count=3)
    localized_config = harness.last_localized_config

    utility_agent = await harness.create_utility_agent(language)
    language_manager = harness.create_language_manager(language)

    agent_logger = AgentCentricLogger()
    agent_logger.initialize_experiment(participants, localized_config)

    phase1_manager = Phase1Manager(participants, utility_agent, language_manager, seed_manager=harness.seed_manager)
    with capture_process_flow_output(create_process_logger("minimal", use_colors=False)):
        phase1_results = await phase1_manager.run_phase1(localized_config, agent_logger)

    manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=localized_config,
        language_manager=language_manager,
        seed_manager=harness.seed_manager,
        agent_logger=agent_logger,
    )

    with capture_process_flow_output(create_process_logger("minimal", use_colors=False)):
        results = await manager.run_phase2(localized_config, phase1_results, agent_logger)

    assert results.discussion_result is not None
    assert results.discussion_result.final_round >= 1
