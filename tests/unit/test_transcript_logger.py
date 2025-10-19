import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.models import TranscriptLoggingConfig
from models import ExperimentPhase, ParticipantContext
from utils.logging.transcript_logger import TranscriptLogger, run_with_transcript_logging


def _make_context(name: str = "Alice") -> ParticipantContext:
    return ParticipantContext(
        name=name,
        role_description="Tester",
        bank_balance=0.0,
        memory="",
        round_number=1,
        phase=ExperimentPhase.PHASE_1,
        memory_character_limit=50000,
    )


def test_record_interaction_tracks_sequence():
    config = TranscriptLoggingConfig(enabled=True)
    logger = TranscriptLogger(config=config, experiment_id="exp123")

    logger.record_interaction(
        agent_name="Alice",
        phase="phase_1",
        round_number=1,
        interaction_type="initial_ranking",
        instructions="instruction text",
        input_prompt="prompt",
    )
    logger.record_interaction(
        agent_name="Alice",
        phase="phase_1",
        round_number=2,
        interaction_type="demonstration",
        instructions=None,
        input_prompt=None,
    )

    agent_transcript = logger.transcript.transcripts["Alice"]
    assert len(agent_transcript.interactions) == 2
    assert "call_1" in agent_transcript.interactions
    assert "call_2" in agent_transcript.interactions

    first_call = agent_transcript.interactions["call_1"]
    assert first_call.round == 1
    assert first_call.instructions == "instruction text"
    assert first_call.input_prompt == "prompt"

    second_call = agent_transcript.interactions["call_2"]
    assert second_call.round == 2
    assert second_call.instructions is None


def test_save_transcript_writes_json_file():
    config = TranscriptLoggingConfig(enabled=True)
    logger = TranscriptLogger(config=config, experiment_id="exp456")
    logger.record_interaction(
        agent_name="Bob",
        phase="phase_2",
        round_number=3,
        interaction_type="statement",
        instructions=None,
        input_prompt="hello",
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "transcript.json"
        saved_path = logger.save_transcript(output_path=str(output_path))

        assert saved_path == str(output_path)
        assert output_path.exists()

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["experiment_metadata"]["experiment_id"] == "exp456"
        assert "Bob" in payload["transcripts"]


def test_record_interaction_accepts_missing_round():
    config = TranscriptLoggingConfig(enabled=True)
    logger = TranscriptLogger(config=config, experiment_id="exp789")

    logger.record_interaction(
        agent_name="Casey",
        phase="phase_2",
        round_number=None,
        interaction_type="final_ranking",
        instructions=None,
        input_prompt="prompt",
    )

    agent_transcript = logger.transcript.transcripts["Casey"]
    assert "call_1" in agent_transcript.interactions
    assert agent_transcript.interactions["call_1"].round is None


def test_record_interaction_includes_response_when_configured():
    config = TranscriptLoggingConfig(enabled=True)
    logger = TranscriptLogger(config=config, experiment_id="exp246")

    logger.record_interaction(
        agent_name="Jordan",
        phase="phase_1",
        round_number=1,
        interaction_type="statement",
        instructions=None,
        input_prompt="prompt",
        output_response="response text",
    )

    agent_transcript = logger.transcript.transcripts["Jordan"]
    interaction = agent_transcript.interactions["call_1"]
    assert interaction.output_response == "response text"


@pytest.mark.asyncio
async def test_wrapper_logs_interaction_when_enabled():
    config = TranscriptLoggingConfig(
        enabled=True,
        include_instructions=True,
        include_input_prompts=True,
    )
    logger = TranscriptLogger(config=config, experiment_id="exp789")
    context = _make_context("Alice")

    participant = MagicMock()
    participant.name = "Alice"
    participant.agent = object()
    participant.get_instructions_for_context.return_value = "instruction"

    mock_result = MagicMock()
    mock_result.final_output = "Result text"
    with patch("utils.logging.transcript_logger.Runner.run", new=AsyncMock(return_value=mock_result)) as mock_run:
        result = await run_with_transcript_logging(
            participant=participant,
            prompt="Prompt text",
            context=context,
            transcript_logger=logger,
            interaction_type="initial_ranking",
        )

    mock_run.assert_awaited_once()
    assert result is mock_result

    agent_transcript = logger.transcript.transcripts["Alice"]
    assert len(agent_transcript.interactions) == 1
    interaction = agent_transcript.interactions["call_1"]
    assert interaction.interaction_type == "initial_ranking"
    assert interaction.instructions == "instruction"
    assert interaction.input_prompt == "Prompt text"
    assert interaction.output_response == "Result text"


@pytest.mark.asyncio
async def test_wrapper_skips_logging_when_disabled():
    config = TranscriptLoggingConfig(enabled=False)
    logger = TranscriptLogger(config=config, experiment_id="exp101")
    context = _make_context("Charlie")

    participant = MagicMock()
    participant.name = "Charlie"
    participant.agent = object()
    participant.get_instructions_for_context.return_value = "instruction"

    mock_result = MagicMock()
    with patch("utils.logging.transcript_logger.Runner.run", new=AsyncMock(return_value=mock_result)):
        result = await run_with_transcript_logging(
            participant=participant,
            prompt="Prompt text",
            context=context,
            transcript_logger=logger,
            interaction_type="initial_ranking",
        )

    assert result is mock_result
    assert logger.transcript.transcripts == {}


@pytest.mark.asyncio
async def test_wrapper_omits_response_when_flag_disabled():
    config = TranscriptLoggingConfig(
        enabled=True,
        include_agent_responses=False,
        include_input_prompts=True,
    )
    logger = TranscriptLogger(config=config, experiment_id="exp202")
    context = _make_context("Bailey")

    participant = MagicMock()
    participant.name = "Bailey"
    participant.agent = object()
    participant.get_instructions_for_context.return_value = "instruction"

    mock_result = MagicMock()
    mock_result.final_output = "Result text"
    with patch("utils.logging.transcript_logger.Runner.run", new=AsyncMock(return_value=mock_result)):
        await run_with_transcript_logging(
            participant=participant,
            prompt="Prompt text",
            context=context,
            transcript_logger=logger,
            interaction_type="initial_ranking",
        )

    agent_transcript = logger.transcript.transcripts["Bailey"]
    interaction = agent_transcript.interactions["call_1"]
    assert interaction.output_response is None
    assert interaction.input_prompt == "Prompt text"


@pytest.mark.asyncio
async def test_wrapper_handles_experiment_error():
    config = TranscriptLoggingConfig(enabled=True)
    logger = TranscriptLogger(config=config, experiment_id="exp303")
    context = _make_context("Dana")

    participant = MagicMock()
    participant.name = "Dana"
    participant.agent = object()
    participant.get_instructions_for_context.return_value = "instruction"

    with patch(
        "utils.logging.transcript_logger.Runner.run",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        with pytest.raises(RuntimeError):
            await run_with_transcript_logging(
                participant=participant,
                prompt="Prompt text",
                context=context,
                transcript_logger=logger,
                interaction_type="initial_ranking",
            )

    assert "Dana" in logger.transcript.transcripts
    interaction = logger.transcript.transcripts["Dana"].interactions["call_1"]
    assert interaction.output_response is None
