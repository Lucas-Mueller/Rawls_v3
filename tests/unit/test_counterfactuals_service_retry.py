"""
Unit Tests for CounterfactualsService Phase 2 Retry Mechanism

Comprehensive tests for the intelligent retry functionality implemented in
CounterfactualsService, including configuration-driven behavior, callback
functionality, memory integration, and error handling.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import List, Dict, Optional, Any

from core.services.counterfactuals_service import CounterfactualsService
from config import ExperimentConfiguration
from config.phase2_settings import Phase2Settings
from models import (
    PrincipleRanking, RankedPrinciple, JusticePrinciple, CertaintyLevel,
    ParticipantContext, IncomeClass
)
from utils.selective_memory_manager import MemoryEventType
from utils.parsing_errors import create_parsing_error

from tests.support.mock_utilities import (
    MockLanguageManager, MockUtilityAgent, MockLogger, MockSeedManager,
    MockMemoryService, MockParticipantAgent, MockParticipantContext,
    create_mock_participants, create_mock_contexts, MockLanguage
)


@pytest.fixture
def mock_config_with_retry():
    """Create ExperimentConfiguration with retry enabled."""
    config = Mock(spec=ExperimentConfiguration)
    config.enable_intelligent_retries = True
    config.max_participant_retries = 2
    config.memory_update_on_retry = True
    config.retry_feedback_detail = "detailed"
    config.memory_guidance_style = "narrative"
    return config


@pytest.fixture
def mock_config_without_retry():
    """Create ExperimentConfiguration with retry disabled."""
    config = Mock(spec=ExperimentConfiguration)
    config.enable_intelligent_retries = False
    config.max_participant_retries = 0
    config.memory_update_on_retry = False
    config.retry_feedback_detail = "concise"
    config.memory_guidance_style = "structured"
    return config


@pytest.fixture
def mock_service_dependencies():
    """Create mock dependencies for CounterfactualsService."""
    return {
        "language_manager": MockLanguageManager(MockLanguage.ENGLISH),
        "settings": Phase2Settings.get_default(),
        "logger": MockLogger(),
        "seed_manager": MockSeedManager(42),
        "memory_service": MockMemoryService()
    }


@pytest.fixture
def mock_participant_and_context():
    """Create mock participant agent and context."""
    participant = MockParticipantAgent("TestAgent", language="english")
    context = MockParticipantContext("TestAgent", language="english")
    context.memory = "Initial test memory"
    return participant, context


@pytest.fixture
def mock_utility_agent_with_retry():
    """Create mock utility agent with retry methods."""
    utility_agent = Mock()
    utility_agent.parse_principle_ranking_enhanced = AsyncMock()
    utility_agent.parse_principle_ranking_enhanced_with_feedback = AsyncMock()
    return utility_agent


class TestRetryConfigurationDrivenBehavior:
    """Test retry mechanism configuration-driven behavior."""

    def test_service_initialization_with_retry_config(self, mock_service_dependencies, mock_config_with_retry):
        """Test service initializes correctly with retry configuration."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        assert service.config is mock_config_with_retry
        assert service.config.enable_intelligent_retries is True
        assert service.config.max_participant_retries == 2
        assert service.config.memory_update_on_retry is True

    def test_service_initialization_without_retry_config(self, mock_service_dependencies, mock_config_without_retry):
        """Test service initializes correctly without retry configuration."""
        service = CounterfactualsService(
            config=mock_config_without_retry,
            **mock_service_dependencies
        )

        assert service.config is mock_config_without_retry
        assert service.config.enable_intelligent_retries is False
        assert service.config.max_participant_retries == 0
        assert service.config.memory_update_on_retry is False

    def test_service_initialization_without_config(self, mock_service_dependencies):
        """Test service initializes correctly with no config (backward compatibility)."""
        service = CounterfactualsService(
            config=None,
            **mock_service_dependencies
        )

        assert service.config is None

    @pytest.mark.asyncio
    async def test_collect_final_rankings_uses_retry_when_enabled(self, mock_service_dependencies, mock_config_with_retry, mock_utility_agent_with_retry):
        """Test that collect_final_rankings uses retry method when enabled."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participants = [MockParticipantAgent("Alice")]
        contexts = [MockParticipantContext("Alice")]
        utility_agent = mock_utility_agent_with_retry

        # Mock the retry method to track calls
        expected_ranking = PrincipleRanking(
            rankings=[
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
            ],
            certainty=CertaintyLevel.VERY_SURE
        )

        with patch.object(service, '_get_final_ranking_task_with_retry', new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = expected_ranking

            result = await service.collect_final_rankings_streamlined(
                contexts=contexts,
                participants=participants,
                utility_agent=utility_agent
            )

        # Verify retry method was called
        mock_retry.assert_called_once_with(participants[0], contexts[0], utility_agent)
        assert "Alice" in result
        assert result["Alice"] == expected_ranking

    @pytest.mark.asyncio
    async def test_collect_final_rankings_uses_streamlined_when_disabled(self, mock_service_dependencies, mock_config_without_retry, mock_utility_agent_with_retry):
        """Test that collect_final_rankings uses streamlined method when retry is disabled."""
        service = CounterfactualsService(
            config=mock_config_without_retry,
            **mock_service_dependencies
        )

        participants = [MockParticipantAgent("Bob")]
        contexts = [MockParticipantContext("Bob")]
        utility_agent = mock_utility_agent_with_retry

        expected_ranking = PrincipleRanking(
            rankings=[
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
            ],
            certainty=CertaintyLevel.SURE
        )

        with patch.object(service, '_get_final_ranking_task_streamlined', new_callable=AsyncMock) as mock_streamlined:
            mock_streamlined.return_value = expected_ranking

            result = await service.collect_final_rankings_streamlined(
                contexts=contexts,
                participants=participants,
                utility_agent=utility_agent
            )

        # Verify streamlined method was called instead of retry
        mock_streamlined.assert_called_once_with(participants[0], contexts[0], utility_agent)
        assert "Bob" in result
        assert result["Bob"] == expected_ranking

    @pytest.mark.asyncio
    async def test_collect_final_rankings_uses_streamlined_when_no_config(self, mock_service_dependencies, mock_utility_agent_with_retry):
        """Test that collect_final_rankings uses streamlined method when no config provided."""
        service = CounterfactualsService(
            config=None,
            **mock_service_dependencies
        )

        participants = [MockParticipantAgent("Carol")]
        contexts = [MockParticipantContext("Carol")]
        utility_agent = mock_utility_agent_with_retry

        with patch.object(service, '_get_final_ranking_task_streamlined', new_callable=AsyncMock) as mock_streamlined:
            mock_streamlined.return_value = Mock()

            await service.collect_final_rankings_streamlined(
                contexts=contexts,
                participants=participants,
                utility_agent=utility_agent
            )

        # Verify streamlined method was called (fallback behavior)
        mock_streamlined.assert_called_once()


class TestRetryCallbackFunctionality:
    """Test retry callback functionality."""

    @pytest.mark.asyncio
    async def test_retry_callback_successful_execution(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test successful retry callback execution."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        # Mock Runner.run for successful retry response
        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "1. Maximizing Floor\n2. Maximizing Average\n3. Floor Constraint\n4. Range Constraint"
            mock_runner.run = AsyncMock(return_value=mock_result)

            # Mock successful parsing on retry
            expected_ranking = PrincipleRanking(
                rankings=[
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4)
                ],
                certainty=CertaintyLevel.SURE
            )

            utility_agent.parse_principle_ranking_enhanced_with_feedback.return_value = expected_ranking

            result = await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

        assert result == expected_ranking
        utility_agent.parse_principle_ranking_enhanced_with_feedback.assert_called_once()

        # Verify callback parameters
        call_args = utility_agent.parse_principle_ranking_enhanced_with_feedback.call_args
        assert call_args[1]['max_retries'] == 3  # max_participant_retries + 1
        assert call_args[1]['participant_retry_callback'] is not None

    @pytest.mark.asyncio
    async def test_retry_callback_with_memory_updates_enabled(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test retry callback with memory updates enabled."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        # Mock the utility agent to trigger retry callback
        retry_callback = None

        async def capture_callback(*args, **kwargs):
            nonlocal retry_callback
            retry_callback = kwargs.get('participant_retry_callback')
            return Mock()

        utility_agent.parse_principle_ranking_enhanced_with_feedback.side_effect = capture_callback

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "Retry response with ranking"
            mock_runner.run = AsyncMock(return_value=mock_result)

            await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

            # Test the captured callback
            assert retry_callback is not None

            # Test callback execution with memory updates
            with patch.object(service, '_update_memory_with_retry_experience', new_callable=AsyncMock) as mock_memory_update:
                callback_result = await retry_callback("Your response format was incorrect. Please provide a ranking.")

                assert callback_result == "Retry response with ranking"
                mock_memory_update.assert_called_once_with(
                    participant, context, "Your response format was incorrect. Please provide a ranking.", "Retry response with ranking"
                )

    @pytest.mark.asyncio
    async def test_retry_callback_with_memory_updates_disabled(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test retry callback with memory updates disabled."""
        config = mock_config_with_retry
        config.memory_update_on_retry = False

        service = CounterfactualsService(
            config=config,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        retry_callback = None

        async def capture_callback(*args, **kwargs):
            nonlocal retry_callback
            retry_callback = kwargs.get('participant_retry_callback')
            return Mock()

        utility_agent.parse_principle_ranking_enhanced_with_feedback.side_effect = capture_callback

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "Retry response"
            mock_runner.run = AsyncMock(return_value=mock_result)

            await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

            # Test callback execution without memory updates
            with patch.object(service, '_update_memory_with_retry_experience', new_callable=AsyncMock) as mock_memory_update:
                callback_result = await retry_callback("Feedback message")

                assert callback_result == "Retry response"
                mock_memory_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_callback_failure_handling(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test retry callback failure handling returns empty string."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        retry_callback = None

        async def capture_callback(*args, **kwargs):
            nonlocal retry_callback
            retry_callback = kwargs.get('participant_retry_callback')
            return Mock()

        utility_agent.parse_principle_ranking_enhanced_with_feedback.side_effect = capture_callback

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            # First call to capture the callback (successful)
            mock_result = Mock()
            mock_result.final_output = "Initial response"
            mock_runner.run = AsyncMock(return_value=mock_result)

            await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

            # Now test callback failure
            assert retry_callback is not None
            mock_runner.run = AsyncMock(side_effect=Exception("Runner failed"))

            callback_result = await retry_callback("Feedback message")
            assert callback_result == ""

    @pytest.mark.asyncio
    async def test_retry_callback_with_different_feedback_detail_levels(self, mock_service_dependencies, mock_config_with_retry):
        """Test retry callback with different feedback detail levels."""
        # Test detailed feedback
        config_detailed = mock_config_with_retry
        config_detailed.retry_feedback_detail = "detailed"

        service_detailed = CounterfactualsService(
            config=config_detailed,
            **mock_service_dependencies
        )

        # Test concise feedback
        config_concise = Mock(spec=ExperimentConfiguration)
        config_concise.enable_intelligent_retries = True
        config_concise.max_participant_retries = 2
        config_concise.memory_update_on_retry = True
        config_concise.retry_feedback_detail = "concise"
        config_concise.memory_guidance_style = "narrative"

        service_concise = CounterfactualsService(
            config=config_concise,
            **mock_service_dependencies
        )

        # Test prompt building with different detail levels
        original_prompt = "Please rank the principles"
        feedback = "Format was incorrect"

        detailed_prompt = service_detailed._build_retry_prompt(original_prompt, feedback, "detailed")
        concise_prompt = service_concise._build_retry_prompt(original_prompt, feedback, "concise")

        # Detailed should be longer and contain more structure
        assert len(detailed_prompt) > len(concise_prompt)
        assert feedback in detailed_prompt
        assert feedback in concise_prompt
        assert original_prompt in detailed_prompt
        assert original_prompt in concise_prompt


class TestMemoryIntegration:
    """Test memory service integration and fallback behavior."""

    @pytest.mark.asyncio
    async def test_memory_update_via_memory_service(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context):
        """Test memory updates via MemoryService with SIMPLE_STATUS_UPDATE."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        feedback = "Your ranking format was unclear"
        retry_response = "1. Floor 2. Average 3. Floor Constraint 4. Range Constraint"

        # Mock MemoryService update
        mock_memory_service = mock_service_dependencies["memory_service"]
        mock_memory_service.update_memory_selective = AsyncMock(return_value="Updated memory")

        await service._update_memory_with_retry_experience(
            participant=participant,
            context=context,
            feedback=feedback,
            retry_response=retry_response
        )

        # Verify MemoryService was called with correct parameters
        mock_memory_service.update_memory_selective.assert_called_once()
        call_args = mock_memory_service.update_memory_selective.call_args

        assert call_args[1]['agent'] == participant
        assert call_args[1]['context'] == context
        assert call_args[1]['event_type'] == MemoryEventType.SIMPLE_STATUS_UPDATE
        assert feedback in call_args[1]['content']
        assert retry_response in call_args[1]['content']
        assert call_args[1]['config'] == mock_config_with_retry

        # Verify context memory was updated
        assert context.memory == "Updated memory"

    @pytest.mark.asyncio
    async def test_memory_update_fallback_to_memory_manager(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context):
        """Test fallback to MemoryManager when MemoryService fails."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        feedback = "Format error"
        retry_response = "Fixed response"

        # Mock MemoryService to fail
        mock_memory_service = mock_service_dependencies["memory_service"]
        mock_memory_service.update_memory_selective = AsyncMock(side_effect=Exception("MemoryService failed"))

        with patch.object(service, '_fallback_memory_update', new_callable=AsyncMock) as mock_fallback:
            await service._update_memory_with_retry_experience(
                participant=participant,
                context=context,
                feedback=feedback,
                retry_response=retry_response
            )

            # Verify fallback was called
            mock_fallback.assert_called_once()
            call_args = mock_fallback.call_args[0]
            assert call_args[0] == participant
            assert call_args[1] == context
            assert feedback in call_args[2]  # Check content contains feedback
            assert retry_response in call_args[2]  # Check content contains response

    @pytest.mark.asyncio
    async def test_memory_update_without_memory_service(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context):
        """Test memory update when MemoryService is not available."""
        # Remove memory service
        mock_service_dependencies["memory_service"] = None

        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context

        with patch.object(service, '_fallback_memory_update', new_callable=AsyncMock) as mock_fallback:
            await service._update_memory_with_retry_experience(
                participant=participant,
                context=context,
                feedback="Test feedback",
                retry_response="Test response"
            )

            # Verify fallback was called directly
            mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_memory_update(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context):
        """Test MemoryManager fallback functionality."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        retry_memory_content = "Retry experience content"

        with patch('core.services.counterfactuals_service.MemoryManager') as mock_memory_manager:
            mock_memory_manager.prompt_agent_for_memory_update = AsyncMock(return_value="Fallback updated memory")

            await service._fallback_memory_update(
                participant=participant,
                context=context,
                retry_memory_content=retry_memory_content
            )

            # Verify MemoryManager was called with correct parameters
            mock_memory_manager.prompt_agent_for_memory_update.assert_called_once_with(
                participant, context, retry_memory_content,
                memory_guidance_style="narrative",
                language_manager=service.language_manager,
                error_handler=None,
                utility_agent=None,
                round_number=getattr(context, 'round_number', None),
                phase=getattr(context, 'phase', None) or "phase_2"
            )

            # Verify context memory was updated
            assert context.memory == "Fallback updated memory"


class TestUtilityAgentIntegration:
    """Test integration with UtilityAgent parsing methods."""

    @pytest.mark.asyncio
    async def test_enhanced_parsing_with_feedback_called_when_retry_enabled(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test that enhanced parsing with feedback is called when retry enabled."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        expected_ranking = Mock()
        utility_agent.parse_principle_ranking_enhanced_with_feedback.return_value = expected_ranking

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "Test response"
            mock_runner.run = AsyncMock(return_value=mock_result)

            result = await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

        # Verify enhanced parsing with feedback was called
        utility_agent.parse_principle_ranking_enhanced_with_feedback.assert_called_once()
        utility_agent.parse_principle_ranking_enhanced.assert_not_called()
        assert result == expected_ranking

    @pytest.mark.asyncio
    async def test_enhanced_parsing_fallback_when_retry_disabled(self, mock_service_dependencies, mock_config_without_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test fallback to enhanced parsing when retry disabled."""
        service = CounterfactualsService(
            config=mock_config_without_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        expected_ranking = Mock()
        utility_agent.parse_principle_ranking_enhanced.return_value = expected_ranking

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "Test response"
            mock_runner.run = AsyncMock(return_value=mock_result)

            result = await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

        # Verify standard enhanced parsing was called
        utility_agent.parse_principle_ranking_enhanced.assert_called_once()
        utility_agent.parse_principle_ranking_enhanced_with_feedback.assert_not_called()
        assert result == expected_ranking

    @pytest.mark.asyncio
    async def test_parsing_error_classification_integration(self, mock_service_dependencies, mock_config_without_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test integration with create_parsing_error for error classification."""
        service = CounterfactualsService(
            config=mock_config_without_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        # Mock parsing failure
        parsing_exception = Exception("Invalid ranking structure")
        utility_agent.parse_principle_ranking_enhanced.side_effect = parsing_exception

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "Invalid response"
            mock_runner.run = AsyncMock(return_value=mock_result)

            with patch('core.services.counterfactuals_service.create_parsing_error') as mock_create_error:
                mock_parsing_error = Exception("Classified parsing error")
                mock_create_error.return_value = mock_parsing_error

                # Should return default ranking due to outer exception handling
                result = await service._get_final_ranking_task_with_retry(
                    participant=participant,
                    context=context,
                    utility_agent=utility_agent
                )

                # Verify default ranking was returned (graceful degradation)
                assert isinstance(result, PrincipleRanking)
                assert result.certainty == CertaintyLevel.NO_OPINION

                # Verify create_parsing_error was called with correct parameters
                mock_create_error.assert_called_once()
                call_args = mock_create_error.call_args[1]
                assert call_args['response'] == "Invalid response"
                assert call_args['parsing_operation'] == "phase2_final_ranking"
                assert call_args['expected_format'] == "ranking"
                assert call_args['additional_context']['participant_name'] == participant.name
                assert call_args['additional_context']['retry_enabled'] is False
                assert call_args['cause'] == parsing_exception


class TestErrorHandling:
    """Test error handling and default ranking generation."""

    @pytest.mark.asyncio
    async def test_default_ranking_generation_on_parsing_failure(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test default ranking generation when parsing fails completely."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        # Mock complete parsing failure
        utility_agent.parse_principle_ranking_enhanced_with_feedback.side_effect = Exception("Parsing failed completely")

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "Unparseable response"
            mock_runner.run = AsyncMock(return_value=mock_result)

            result = await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

        # Verify default ranking was generated
        assert isinstance(result, PrincipleRanking)
        assert len(result.rankings) == 4
        assert result.certainty == CertaintyLevel.NO_OPINION

        # Verify default ranking order (Maximizing Floor first)
        assert result.rankings[0].principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert result.rankings[0].rank == 1
        assert result.rankings[1].principle == JusticePrinciple.MAXIMIZING_AVERAGE
        assert result.rankings[1].rank == 2

    @pytest.mark.asyncio
    async def test_exception_handling_in_retry_callback(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test proper exception handling in retry callback."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        retry_callback = None

        async def capture_callback(*args, **kwargs):
            nonlocal retry_callback
            retry_callback = kwargs.get('participant_retry_callback')
            return Mock()

        utility_agent.parse_principle_ranking_enhanced_with_feedback.side_effect = capture_callback

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            # First call to set up callback
            mock_result = Mock()
            mock_result.final_output = "Initial response"
            mock_runner.run = AsyncMock(return_value=mock_result)

            await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

            # Test callback exception handling
            mock_runner.run = AsyncMock(side_effect=Exception("Callback execution failed"))

            result = await retry_callback("Test feedback")

            # Should return empty string on failure
            assert result == ""

    @pytest.mark.asyncio
    async def test_context_cleanup_in_retry_task(self, mock_service_dependencies, mock_config_with_retry, mock_participant_and_context, mock_utility_agent_with_retry):
        """Test context cleanup in retry task method."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participant, context = mock_participant_and_context
        utility_agent = mock_utility_agent_with_retry

        # Set up context with discussion-mode values
        context.interaction_type = "discussion"
        context.round_number = 5
        context.internal_reasoning = "Previous reasoning"
        context.discussion_history = "Previous discussion history"

        utility_agent.parse_principle_ranking_enhanced_with_feedback.return_value = Mock()

        with patch('core.services.counterfactuals_service.Runner') as mock_runner:
            mock_result = Mock()
            mock_result.final_output = "Test response"
            mock_runner.run = AsyncMock(return_value=mock_result)

            await service._get_final_ranking_task_with_retry(
                participant=participant,
                context=context,
                utility_agent=utility_agent
            )

        # Verify context was cleaned up for final ranking
        assert context.interaction_type is None
        assert context.round_number == 0
        assert context.internal_reasoning == ""
        assert context.discussion_history == ""


class TestMethodIntegration:
    """Test method integration and conditional logic paths."""

    @pytest.mark.asyncio
    async def test_collect_final_rankings_exception_handling(self, mock_service_dependencies, mock_config_with_retry, mock_utility_agent_with_retry):
        """Test exception handling in collect_final_rankings_streamlined."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        participants = [MockParticipantAgent("Alice"), MockParticipantAgent("Bob")]
        contexts = [MockParticipantContext("Alice"), MockParticipantContext("Bob")]
        utility_agent = mock_utility_agent_with_retry

        # Mock first participant to succeed, second to fail
        with patch.object(service, '_get_final_ranking_task_with_retry', new_callable=AsyncMock) as mock_retry:
            success_ranking = Mock()
            failure_exception = Exception("Task failed")

            mock_retry.side_effect = [success_ranking, failure_exception]

            result = await service.collect_final_rankings_streamlined(
                contexts=contexts,
                participants=participants,
                utility_agent=utility_agent
            )

        # Verify both participants handled appropriately
        assert len(result) == 2
        assert result["Alice"] == success_ranking

        # Bob should get default ranking due to exception
        assert isinstance(result["Bob"], PrincipleRanking)
        assert result["Bob"].certainty == CertaintyLevel.NO_OPINION

    def test_build_retry_prompt_with_different_detail_levels(self, mock_service_dependencies, mock_config_with_retry):
        """Test _build_retry_prompt with different detail levels."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        original_prompt = "Please provide your ranking"
        feedback = "The format was incorrect"

        # Test detailed prompt
        detailed_prompt = service._build_retry_prompt(original_prompt, feedback, "detailed")
        assert len(detailed_prompt) > 0
        assert original_prompt in detailed_prompt
        assert feedback in detailed_prompt

        # Test concise prompt
        concise_prompt = service._build_retry_prompt(original_prompt, feedback, "concise")
        assert len(concise_prompt) > 0
        assert original_prompt in concise_prompt
        assert feedback in concise_prompt

        # Detailed should generally be longer due to additional structure
        assert len(detailed_prompt) >= len(concise_prompt)

    @pytest.mark.asyncio
    async def test_multilingual_retry_support(self, mock_service_dependencies, mock_config_with_retry, mock_utility_agent_with_retry):
        """Test retry mechanism works with multilingual setup."""
        # Test with different languages
        for language in [MockLanguage.ENGLISH, MockLanguage.SPANISH, MockLanguage.MANDARIN]:
            mock_deps = mock_service_dependencies.copy()
            mock_deps["language_manager"] = MockLanguageManager(language)

            service = CounterfactualsService(
                config=mock_config_with_retry,
                **mock_deps
            )

            participant = MockParticipantAgent("TestAgent", language=language.value)
            context = MockParticipantContext("TestAgent", language=language.value)
            utility_agent = mock_utility_agent_with_retry

            # Mock successful parsing
            utility_agent.parse_principle_ranking_enhanced_with_feedback.return_value = Mock()

            with patch('core.services.counterfactuals_service.Runner') as mock_runner:
                mock_result = Mock()
                mock_result.final_output = f"Response in {language.value}"
                mock_runner.run = AsyncMock(return_value=mock_result)

                result = await service._get_final_ranking_task_with_retry(
                    participant=participant,
                    context=context,
                    utility_agent=utility_agent
                )

            # Verify parsing was attempted for each language
            utility_agent.parse_principle_ranking_enhanced_with_feedback.assert_called()

    @pytest.mark.asyncio
    async def test_async_task_concurrency(self, mock_service_dependencies, mock_config_with_retry, mock_utility_agent_with_retry):
        """Test async task creation and concurrent execution."""
        service = CounterfactualsService(
            config=mock_config_with_retry,
            **mock_service_dependencies
        )

        # Create multiple participants
        participants = [
            MockParticipantAgent("Alice"),
            MockParticipantAgent("Bob"),
            MockParticipantAgent("Carol")
        ]
        contexts = [
            MockParticipantContext("Alice"),
            MockParticipantContext("Bob"),
            MockParticipantContext("Carol")
        ]
        utility_agent = mock_utility_agent_with_retry

        # Track task creation timing
        task_creation_times = []

        async def mock_retry_task(*args):
            task_creation_times.append(len(task_creation_times))
            await asyncio.sleep(0.01)  # Simulate work
            return Mock()

        with patch.object(service, '_get_final_ranking_task_with_retry', side_effect=mock_retry_task):
            result = await service.collect_final_rankings_streamlined(
                contexts=contexts,
                participants=participants,
                utility_agent=utility_agent
            )

        # Verify all tasks were created (tasks should be created before execution)
        assert len(result) == 3
        assert len(task_creation_times) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])