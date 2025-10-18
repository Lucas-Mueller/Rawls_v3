"""Live component tests for the MemoryService."""
from __future__ import annotations

import pytest

from core.phase2_manager import Phase2Manager
from tests.support import parametrize_languages
from models import ParticipantContext, ExperimentPhase


@parametrize_languages()
@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_memory_service_vote_updates(language, prompt_harness_three_agents):
    """Ensure MemoryService records vote decisions without truncation."""
    harness = prompt_harness_three_agents
    harness.ensure_seed()
    participants = await harness.create_participants(language, agent_count=3)
    localized_config = harness.last_localized_config

    utility_agent = await harness.create_utility_agent(language)
    language_manager = harness.create_language_manager(language)

    phase2_manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=localized_config,
        language_manager=language_manager,
        seed_manager=harness.seed_manager,
    )
    phase2_manager._initialize_services()  # Safe during tests
    memory_service = phase2_manager.memory_service

    for idx, participant in enumerate(participants):
        context = ParticipantContext(
            name=participant.name,
            role_description=participant.config.personality,
            bank_balance=0.0,
            memory="",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=participant.config.memory_character_limit,
        )
        wants_vote = idx % 2 == 0
        updated_memory = await memory_service.update_vote_initiation_decision_memory(
            participant,
            context,
            round_num=1,
            wants_vote=wants_vote,
        )
        assert isinstance(updated_memory, str)
        assert updated_memory
        assert updated_memory == context.memory
        assert len(updated_memory) > 10
