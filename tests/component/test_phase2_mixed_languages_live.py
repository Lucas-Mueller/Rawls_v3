"""Live component tests for mixed-language Phase 2 flows."""
from __future__ import annotations

import pytest

from core.phase1_manager import Phase1Manager
from core.phase2_manager import Phase2Manager
from tests.support import capture_process_flow_output, PromptHarness, build_experiment_configuration
from utils.language_manager import SupportedLanguage
from utils.logging.agent_centric_logger import AgentCentricLogger
from utils.logging.process_flow_logger import create_process_logger


def _build_mixed_language_harness() -> PromptHarness:
    config = build_experiment_configuration(agent_count=3)
    languages = [SupportedLanguage.SPANISH.value.lower(), SupportedLanguage.ENGLISH.value.lower(), SupportedLanguage.MANDARIN.value.lower()]
    updated_agents = [agent.model_copy(update={"language": lang}) for agent, lang in zip(config.agents, languages)]
    mixed_config = config.model_copy(update={"agents": updated_agents})
    return PromptHarness(mixed_config)


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_phase2_mixed_language_discussion(openai_api_key):
    harness = _build_mixed_language_harness()
    harness.ensure_seed()

    participants = await harness.create_participants(
        SupportedLanguage.ENGLISH,
        agent_count=3,
        initialize=True,
        preserve_config_languages=True,
    )
    localized_config = harness.last_localized_config

    utility_agent = await harness.create_utility_agent(SupportedLanguage.ENGLISH)
    language_manager = harness.create_language_manager(SupportedLanguage.ENGLISH)

    agent_logger = AgentCentricLogger()
    agent_logger.initialize_experiment(participants, localized_config)

    phase1_manager = Phase1Manager(participants, utility_agent, language_manager, seed_manager=harness.seed_manager)
    with capture_process_flow_output(create_process_logger("minimal", use_colors=False)):
        phase1_results = await phase1_manager.run_phase1(localized_config, agent_logger)

    phase2_manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=localized_config,
        language_manager=language_manager,
        seed_manager=harness.seed_manager,
        agent_logger=agent_logger,
    )

    with capture_process_flow_output(create_process_logger("minimal", use_colors=False)):
        results = await phase2_manager.run_phase2(localized_config, phase1_results, agent_logger)

    assert results.discussion_result is not None
    assert results.discussion_result.final_round >= 1
    assert len(results.discussion_result.discussion_history) > 0
