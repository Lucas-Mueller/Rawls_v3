"""Live component test for Phase 2 manager using the prompt harness."""
from __future__ import annotations

import pytest

from core.phase1_manager import Phase1Manager
from core.phase2_manager import Phase2Manager
from tests.support import parametrize_languages, capture_process_flow_output
from utils.logging.agent_centric_logger import AgentCentricLogger
from utils.logging.process_flow_logger import create_process_logger


@parametrize_languages()
@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_phase2_manager_runs_with_live_agents(language, prompt_harness_three_agents):
    """Run Phase 2 end-to-end with live agents and validate structural outputs."""
    harness = prompt_harness_three_agents
    harness.ensure_seed()
    participants = await harness.create_participants(language, agent_count=3)
    assert len(participants) == 3

    localized_config = harness.last_localized_config
    assert localized_config is not None

    utility_agent = await harness.create_utility_agent(language)
    language_manager = harness.create_language_manager(language)

    agent_logger = AgentCentricLogger()
    agent_logger.initialize_experiment(participants, localized_config)

    phase1_manager = Phase1Manager(participants, utility_agent, language_manager, seed_manager=harness.seed_manager)
    phase1_process_logger = create_process_logger("minimal", use_colors=False)
    with capture_process_flow_output(phase1_process_logger):
        phase1_results = await phase1_manager.run_phase1(localized_config, agent_logger, phase1_process_logger)

    assert len(phase1_results) == len(participants)

    phase2_manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=localized_config,
        language_manager=language_manager,
        agent_logger=agent_logger,
        seed_manager=harness.seed_manager,
    )
    phase2_process_logger = create_process_logger("minimal", use_colors=False)
    with capture_process_flow_output(phase2_process_logger):
        phase2_results = await phase2_manager.run_phase2(
            localized_config,
            phase1_results,
            agent_logger,
            phase2_process_logger,
        )

    assert phase2_results is not None
    assert len(phase2_results.payoff_results) == len(participants)
    assert set(phase2_results.payoff_results.keys()) == {p.name for p in participants}
    for value in phase2_results.payoff_results.values():
        assert isinstance(value, (int, float))

    discussion = phase2_results.discussion_result
    assert discussion is not None
    assert discussion.final_round >= 1
    assert isinstance(discussion.consensus_reached, bool)

    if discussion.consensus_reached and discussion.agreed_principle:
        assert discussion.agreed_principle.principle is not None
