from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from core.services.voting_service import VotingService


class VotingServiceTranscriptTests(IsolatedAsyncioTestCase):
    async def test_invoke_voting_interaction_uses_transcript_wrapper(self):
        language_manager = MagicMock()
        utility_agent = MagicMock()
        transcript_logger = MagicMock()

        service = VotingService(
            language_manager=language_manager,
            utility_agent=utility_agent,
            transcript_logger=transcript_logger
        )

        participant = MagicMock()
        participant.name = "Voter"
        participant.agent = object()

        context = MagicMock()

        expected_result = MagicMock()
        with patch(
            "core.services.voting_service.run_with_transcript_logging",
            new=AsyncMock(return_value=expected_result)
        ) as mocked_runner:
            result = await service._invoke_voting_interaction(
                participant=participant,
                context=context,
                prompt="Prompt",
                interaction_type="vote_prompt",
                timeout_seconds=None
            )

        mocked_runner.assert_awaited_once()
        kwargs = mocked_runner.await_args.kwargs
        self.assertIs(kwargs["participant"], participant)
        self.assertEqual(kwargs["prompt"], "Prompt")
        self.assertIs(kwargs["transcript_logger"], transcript_logger)
        self.assertEqual(kwargs["interaction_type"], "vote_prompt")
        self.assertIs(result, expected_result)
        self.assertEqual(context.interaction_type, "vote_prompt")
