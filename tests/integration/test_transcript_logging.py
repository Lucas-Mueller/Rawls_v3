"""Integration tests for transcript logging end-to-end payloads."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.models import TranscriptLoggingConfig
from models import ExperimentPhase, ParticipantContext
from utils.logging.transcript_logger import TranscriptLogger, run_with_transcript_logging


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcript_logger_saves_agent_responses(tmp_path: Path) -> None:
    """End-to-end check that agent responses are persisted when enabled."""
    config = TranscriptLoggingConfig(
        enabled=True,
        include_input_prompts=True,
        include_agent_responses=True
    )
    transcript_logger = TranscriptLogger(config=config, experiment_id="integration-test")

    context = ParticipantContext(
        name="Delta",
        role_description="Tester",
        bank_balance=0.0,
        memory="",
        round_number=1,
        phase=ExperimentPhase.PHASE_1,
        memory_character_limit=50000
    )

    participant = MagicMock()
    participant.name = "Delta"
    participant.agent = object()
    participant.get_instructions_for_context.return_value = "Instruction"

    mock_result = MagicMock()
    mock_result.final_output = "Agent response text"

    with patch("utils.logging.transcript_logger.Runner.run", new=AsyncMock(return_value=mock_result)):
        await run_with_transcript_logging(
            participant=participant,
            prompt="Prompt text",
            context=context,
            transcript_logger=transcript_logger,
            interaction_type="statement"
        )

    output_path = tmp_path / "transcript.json"
    saved_path = transcript_logger.save_transcript(str(output_path))

    assert Path(saved_path).exists()
    payload = json.loads(Path(saved_path).read_text(encoding="utf-8"))
    call = payload["transcripts"]["Delta"]["interactions"]["call_1"]
    assert call["input_prompt"] == "Prompt text"
    assert call["output_response"] == "Agent response text"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transcript_logger_omits_agent_responses_when_disabled(tmp_path: Path) -> None:
    """Ensure agent responses are omitted when the flag is disabled."""
    config = TranscriptLoggingConfig(
        enabled=True,
        include_input_prompts=True,
        include_agent_responses=False
    )
    transcript_logger = TranscriptLogger(config=config, experiment_id="integration-test")

    context = ParticipantContext(
        name="Echo",
        role_description="Tester",
        bank_balance=0.0,
        memory="",
        round_number=1,
        phase=ExperimentPhase.PHASE_1,
        memory_character_limit=50000
    )

    participant = MagicMock()
    participant.name = "Echo"
    participant.agent = object()
    participant.get_instructions_for_context.return_value = "Instruction"

    mock_result = MagicMock()
    mock_result.final_output = "Agent response text"

    with patch("utils.logging.transcript_logger.Runner.run", new=AsyncMock(return_value=mock_result)):
        await run_with_transcript_logging(
            participant=participant,
            prompt="Prompt text",
            context=context,
            transcript_logger=transcript_logger,
            interaction_type="statement"
        )

    output_path = tmp_path / "transcript.json"
    transcript_logger.save_transcript(str(output_path))

    payload = json.loads(Path(output_path).read_text(encoding="utf-8"))
    call = payload["transcripts"]["Echo"]["interactions"]["call_1"]
    assert call["input_prompt"] == "Prompt text"
    assert call.get("output_response") is None
