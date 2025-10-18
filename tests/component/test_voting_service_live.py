"""Live component tests for the VotingService."""
from __future__ import annotations

import pytest

from core.services.voting_service import VotingService
from tests.support import parametrize_languages


@parametrize_languages()
@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_voting_service_prompt_flow(language, prompt_harness_three_agents):
    """Ensure vote initiation prompts resolve cleanly for all participants."""
    harness = prompt_harness_three_agents
    participants = await harness.create_participants(language, agent_count=3)
    utility_agent = await harness.create_utility_agent(language)
    language_manager = harness.create_language_manager(language)

    voting_service = VotingService(
        language_manager=language_manager,
        utility_agent=utility_agent,
    )

    from models import ParticipantContext, ExperimentPhase

    for participant in participants:
        context = ParticipantContext(
            name=participant.name,
            role_description=participant.config.personality,
            bank_balance=0.0,
            memory="",
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=participant.config.memory_character_limit,
        )
        wants_vote = await voting_service.prompt_for_vote_initiation(participant, context)
        assert isinstance(wants_vote, bool)
