import json
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from config.models import TranscriptLoggingConfig
from models import ParticipantContext, ExperimentPhase
from utils.logging.transcript_logger import TranscriptLogger, run_with_transcript_logging


class TranscriptLoggerTests(TestCase):
    """Unit tests for the TranscriptLogger service."""

    def test_record_interaction_tracks_sequence(self):
        config = TranscriptLoggingConfig(enabled=True)
        logger = TranscriptLogger(config=config, experiment_id="exp123")

        logger.record_interaction(
            agent_name="Alice",
            phase="phase_1",
            round_number=1,
            interaction_type="initial_ranking",
            instructions="instruction text",
            input_prompt="prompt"
        )
        logger.record_interaction(
            agent_name="Alice",
            phase="phase_1",
            round_number=2,
            interaction_type="demonstration",
            instructions=None,
            input_prompt=None
        )

        agent_transcript = logger.transcript.transcripts["Alice"]
        self.assertEqual(len(agent_transcript.interactions), 2)
        self.assertIn("call_1", agent_transcript.interactions)
        self.assertIn("call_2", agent_transcript.interactions)

        first_call = agent_transcript.interactions["call_1"]
        self.assertEqual(first_call.round, 1)
        self.assertEqual(first_call.instructions, "instruction text")
        self.assertEqual(first_call.input_prompt, "prompt")

        second_call = agent_transcript.interactions["call_2"]
        self.assertEqual(second_call.round, 2)
        self.assertIsNone(second_call.instructions)

    def test_save_transcript_writes_json_file(self):
        config = TranscriptLoggingConfig(enabled=True)
        logger = TranscriptLogger(config=config, experiment_id="exp456")
        logger.record_interaction(
            agent_name="Bob",
            phase="phase_2",
            round_number=3,
            interaction_type="statement",
            instructions=None,
            input_prompt="hello"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "transcript.json"
            saved_path = logger.save_transcript(output_path=str(output_path))

            self.assertEqual(saved_path, str(output_path))
            self.assertTrue(output_path.exists())

            payload = json.loads(output_path.read_text(encoding='utf-8'))
            self.assertIn("experiment_metadata", payload)
            self.assertEqual(payload["experiment_metadata"]["experiment_id"], "exp456")
            self.assertIn("Bob", payload["transcripts"])

    def test_record_interaction_accepts_missing_round(self):
        config = TranscriptLoggingConfig(enabled=True)
        logger = TranscriptLogger(config=config, experiment_id="exp789")

        logger.record_interaction(
            agent_name="Casey",
            phase="phase_2",
            round_number=None,
            interaction_type="final_ranking",
            instructions=None,
            input_prompt="prompt"
        )

        agent_transcript = logger.transcript.transcripts["Casey"]
        self.assertIn("call_1", agent_transcript.interactions)
        self.assertIsNone(agent_transcript.interactions["call_1"].round)

    def test_record_interaction_includes_response_when_configured(self):
        config = TranscriptLoggingConfig(enabled=True)
        logger = TranscriptLogger(config=config, experiment_id="exp246")

        logger.record_interaction(
            agent_name="Jordan",
            phase="phase_1",
            round_number=1,
            interaction_type="statement",
            instructions=None,
            input_prompt="prompt",
            output_response="response text"
        )

        agent_transcript = logger.transcript.transcripts["Jordan"]
        interaction = agent_transcript.interactions["call_1"]
        self.assertEqual(interaction.output_response, "response text")


class RunWithTranscriptLoggingTests(IsolatedAsyncioTestCase):
    """Async tests for the run_with_transcript_logging helper."""

    async def test_wrapper_logs_interaction_when_enabled(self):
        config = TranscriptLoggingConfig(
            enabled=True,
            include_instructions=True,
            include_input_prompts=True
        )
        logger = TranscriptLogger(config=config, experiment_id="exp789")
        context = ParticipantContext(
            name="Alice",
            role_description="Tester",
            bank_balance=0.0,
            memory="",
            round_number=1,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=50000
        )

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
                interaction_type="initial_ranking"
            )

        mock_run.assert_awaited_once()
        self.assertIs(result, mock_result)

        agent_transcript = logger.transcript.transcripts["Alice"]
        self.assertEqual(len(agent_transcript.interactions), 1)
        interaction = agent_transcript.interactions["call_1"]
        self.assertEqual(interaction.interaction_type, "initial_ranking")
        self.assertEqual(interaction.instructions, "instruction")
        self.assertEqual(interaction.input_prompt, "Prompt text")
        self.assertEqual(interaction.output_response, "Result text")

    async def test_wrapper_skips_logging_when_disabled(self):
        config = TranscriptLoggingConfig(enabled=False)
        logger = TranscriptLogger(config=config, experiment_id="exp101")
        context = ParticipantContext(
            name="Charlie",
            role_description="Tester",
            bank_balance=0.0,
            memory="",
            round_number=1,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=50000
        )

        participant = MagicMock()
        participant.name = "Charlie"
        participant.agent = object()
        participant.get_instructions_for_context.return_value = "instruction"

        mock_result = MagicMock()
        with patch("utils.logging.transcript_logger.Runner.run", new=AsyncMock(return_value=mock_result)) as mock_run:
            result = await run_with_transcript_logging(
                participant=participant,
                prompt="Prompt text",
                context=context,
                transcript_logger=logger,
                interaction_type="initial_ranking"
            )

        mock_run.assert_awaited_once()
        self.assertIs(result, mock_result)
        self.assertEqual(logger.transcript.transcripts, {})

    async def test_wrapper_omits_response_when_flag_disabled(self):
        config = TranscriptLoggingConfig(
            enabled=True,
            include_agent_responses=False,
            include_input_prompts=True
        )
        logger = TranscriptLogger(config=config, experiment_id="exp202")
        context = ParticipantContext(
            name="Bailey",
            role_description="Tester",
            bank_balance=0.0,
            memory="",
            round_number=2,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=50000
        )

        participant = MagicMock()
        participant.name = "Bailey"
        participant.agent = object()
        participant.get_instructions_for_context.return_value = "instruction"

        mock_result = MagicMock()
        mock_result.final_output = "Should not record"
        with patch("utils.logging.transcript_logger.Runner.run", new=AsyncMock(return_value=mock_result)):
            await run_with_transcript_logging(
                participant=participant,
                prompt="Prompt text",
                context=context,
                transcript_logger=logger,
                interaction_type="initial_ranking"
            )

        agent_transcript = logger.transcript.transcripts["Bailey"]
        interaction = agent_transcript.interactions["call_1"]
        self.assertIsNone(interaction.output_response)
