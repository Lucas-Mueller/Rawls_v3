from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.phase1_manager import Phase1Manager
from models import ExperimentPhase, ParticipantContext


@pytest.mark.asyncio
async def test_invoke_phase1_interaction_uses_transcript_wrapper():
    participant = MagicMock()
    participant.name = "TestAgent"
    participant.agent = object()

    transcript_logger = MagicMock()
    manager = Phase1Manager(
        participants=[participant],
        utility_agent=MagicMock(),
        language_manager=MagicMock(),
        error_handler=MagicMock(),
        seed_manager=MagicMock(),
        transcript_logger=transcript_logger,
    )

    context = ParticipantContext(
        name="TestAgent",
        role_description="Tester",
        bank_balance=0.0,
        memory="",
        round_number=1,
        phase=ExperimentPhase.PHASE_1,
        memory_character_limit=50000,
    )
    context.interaction_type = "previous"

    mocked_result = MagicMock()
    with patch("core.phase1_manager.run_with_transcript_logging", new=AsyncMock(return_value=mocked_result)) as mocked_runner:
        result = await manager._invoke_phase1_interaction(
            participant=participant,
            context=context,
            prompt="Prompt",
            interaction_type="initial_ranking",
        )

    mocked_runner.assert_awaited_once()
    called_kwargs = mocked_runner.await_args.kwargs
    assert called_kwargs["participant"] is participant
    assert called_kwargs["prompt"] == "Prompt"
    assert called_kwargs["interaction_type"] == "initial_ranking"
    assert called_kwargs["transcript_logger"] is transcript_logger

    assert result is mocked_result
    assert context.interaction_type == "previous"
