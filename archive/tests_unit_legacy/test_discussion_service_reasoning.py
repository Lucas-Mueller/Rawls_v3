"""
Unit tests for DiscussionService reasoning functionality.

Tests the two-step reasoning flow, reasoning configuration handling,
error scenarios, and integration with existing statement validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Any

from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings
from models import GroupDiscussionState


class MockRunner:
    """Mock Runner class for testing."""
    
    class Result:
        def __init__(self, final_output: str):
            self.final_output = final_output
    
    @staticmethod
    async def run(agent: Any, prompt: str, context: Any = None) -> 'MockRunner.Result':
        """Mock run method that returns configurable results."""
        # This will be mocked in tests to return specific values
        pass


class TestDiscussionServiceReasoningConfiguration:
    """Test reasoning configuration and should_use_reasoning method."""
    
    def test_should_use_reasoning_enabled_by_default(self):
        """Test that reasoning is enabled by default."""
        language_manager = Mock()
        service = DiscussionService(language_manager)
        
        assert service.should_use_reasoning() is True
    
    def test_should_use_reasoning_with_custom_settings_enabled(self):
        """Test reasoning enabled with custom settings."""
        language_manager = Mock()
        settings = Phase2Settings(reasoning_enabled=True)
        service = DiscussionService(language_manager, settings)
        
        assert service.should_use_reasoning() is True
    
    def test_should_use_reasoning_with_custom_settings_disabled(self):
        """Test reasoning disabled with custom settings."""
        language_manager = Mock()
        settings = Phase2Settings(reasoning_enabled=False)
        service = DiscussionService(language_manager, settings)
        
        assert service.should_use_reasoning() is False
    
    def test_should_use_reasoning_reflects_settings_changes(self):
        """Test should_use_reasoning reflects settings state."""
        language_manager = Mock()
        
        # Test with enabled
        settings_enabled = Phase2Settings(reasoning_enabled=True)
        service_enabled = DiscussionService(language_manager, settings_enabled)
        assert service_enabled.should_use_reasoning() is True
        
        # Test with disabled
        settings_disabled = Phase2Settings(reasoning_enabled=False)
        service_disabled = DiscussionService(language_manager, settings_disabled)
        assert service_disabled.should_use_reasoning() is False


class TestDiscussionServiceReasoningFlow:
    """Test the two-step reasoning flow in get_participant_statement_with_retry."""
    
    @pytest.fixture
    def language_manager(self):
        """Mock language manager."""
        manager = Mock()
        manager.get.return_value = "Mock prompt"
        return manager
    
    @pytest.fixture
    def settings_reasoning_enabled(self):
        """Settings with reasoning enabled."""
        return Phase2Settings(
            reasoning_enabled=True,
            reasoning_timeout_seconds=120,
            reasoning_max_retries=2,
            max_statement_retries=3
        )
    
    @pytest.fixture
    def settings_reasoning_disabled(self):
        """Settings with reasoning disabled."""
        return Phase2Settings(reasoning_enabled=False)
    
    @pytest.fixture
    def mock_participant(self):
        """Mock participant agent."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        return participant
    
    @pytest.fixture
    def mock_context(self):
        """Mock participant context."""
        context = Mock()
        context.round_number = 2
        context.interaction_type = None
        return context
    
    @pytest.fixture
    def mock_discussion_state(self):
        """Mock discussion state."""
        state = Mock()
        state.public_history = "Previous discussion content"
        return state
    
    @pytest.fixture
    def mock_agent_config(self):
        """Mock agent configuration."""
        config = Mock()
        config.language = 'english'
        return config
    
    @pytest.mark.asyncio
    async def test_two_step_reasoning_enabled_success(
        self, language_manager, settings_reasoning_enabled, mock_participant,
        mock_context, mock_discussion_state, mock_agent_config
    ):
        """Test successful two-step reasoning flow when enabled."""
        service = DiscussionService(language_manager, settings_reasoning_enabled)
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock successful reasoning call
            reasoning_result = Mock()
            reasoning_result.final_output = "This is my internal reasoning"
            
            # Mock successful statement call
            statement_result = Mock()
            statement_result.final_output = "This is my public statement"
            
            # Configure Runner.run to return different results based on call order
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            # Mock build methods
            with patch.object(service, 'build_internal_reasoning_prompt', return_value="Reasoning prompt"):
                with patch.object(service, 'build_discussion_prompt', return_value="Discussion prompt"):
                    with patch.object(service, 'validate_statement', return_value=True):
                        
                        result = await service.get_participant_statement_with_retry(
                            participant=mock_participant,
                            context=mock_context,
                            discussion_state=mock_discussion_state,
                            agent_config=mock_agent_config,
                            participant_names=["TestAgent", "OtherAgent"],
                            max_rounds=5
                        )
                        
                        statement, internal_reasoning = result
                        assert statement == "This is my public statement"
                        assert internal_reasoning == "This is my internal reasoning"
                        
                        # Verify Runner.run was called twice
                        assert mock_runner_class.run.call_count == 2
                        
                        # Verify context.interaction_type was set correctly
                        assert mock_context.interaction_type == "statement"  # Final value
    
    @pytest.mark.asyncio
    async def test_single_step_reasoning_disabled(
        self, language_manager, settings_reasoning_disabled, mock_participant,
        mock_context, mock_discussion_state, mock_agent_config
    ):
        """Test single-step flow when reasoning is disabled."""
        service = DiscussionService(language_manager, settings_reasoning_disabled)
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock successful statement call
            statement_result = Mock()
            statement_result.final_output = "This is my public statement"
            
            mock_runner_class.run = AsyncMock(return_value=statement_result)
            
            # Mock build methods
            with patch.object(service, 'build_internal_reasoning_prompt') as mock_reasoning_prompt:
                with patch.object(service, 'build_discussion_prompt', return_value="Discussion prompt"):
                    with patch.object(service, 'validate_statement', return_value=True):
                        
                        result = await service.get_participant_statement_with_retry(
                            participant=mock_participant,
                            context=mock_context,
                            discussion_state=mock_discussion_state,
                            agent_config=mock_agent_config,
                            participant_names=["TestAgent"],
                            max_rounds=3
                        )
                        
                        statement, internal_reasoning = result
                        assert statement == "This is my public statement"
                        assert internal_reasoning == ""  # Empty when disabled
                        
                        # Verify Runner.run was called only once (for statement)
                        assert mock_runner_class.run.call_count == 1
                        
                        # Verify reasoning prompt was not built
                        mock_reasoning_prompt.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_reasoning_timeout_fallback_to_empty(
        self, language_manager, settings_reasoning_enabled, mock_participant,
        mock_context, mock_discussion_state, mock_agent_config
    ):
        """Test reasoning timeout handling with fallback to empty reasoning."""
        service = DiscussionService(language_manager, settings_reasoning_enabled)
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock statement call success
            statement_result = Mock()
            statement_result.final_output = "This is my public statement"
            
            # Configure Runner.run: first call times out, second succeeds
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                asyncio.TimeoutError("Reasoning timed out"),  # First call (reasoning)
                statement_result  # Second call (statement)
            ]
            
            with patch.object(service, 'build_internal_reasoning_prompt', return_value="Reasoning prompt"):
                with patch.object(service, 'build_discussion_prompt', return_value="Discussion prompt"):
                    with patch.object(service, 'validate_statement', return_value=True):
                        
                        result = await service.get_participant_statement_with_retry(
                            participant=mock_participant,
                            context=mock_context,
                            discussion_state=mock_discussion_state,
                            agent_config=mock_agent_config,
                            participant_names=["TestAgent"],
                            max_rounds=3
                        )
                        
                        statement, internal_reasoning = result
                        assert statement == "This is my public statement"
                        assert internal_reasoning == ""  # Empty due to timeout fallback
                        
                        # Verify both calls were attempted
                        assert mock_runner_class.run.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reasoning_exception_fallback_to_empty(
        self, language_manager, settings_reasoning_enabled, mock_participant,
        mock_context, mock_discussion_state, mock_agent_config
    ):
        """Test reasoning exception handling with fallback to empty reasoning."""
        service = DiscussionService(language_manager, settings_reasoning_enabled)
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock statement call success
            statement_result = Mock()
            statement_result.final_output = "This is my public statement"
            
            # Configure Runner.run: first call raises exception, second succeeds
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                Exception("Reasoning failed"),  # First call (reasoning)
                statement_result  # Second call (statement)
            ]
            
            with patch.object(service, 'build_internal_reasoning_prompt', return_value="Reasoning prompt"):
                with patch.object(service, 'build_discussion_prompt', return_value="Discussion prompt"):
                    with patch.object(service, 'validate_statement', return_value=True):
                        
                        result = await service.get_participant_statement_with_retry(
                            participant=mock_participant,
                            context=mock_context,
                            discussion_state=mock_discussion_state,
                            agent_config=mock_agent_config,
                            participant_names=["TestAgent"],
                            max_rounds=3
                        )
                        
                        statement, internal_reasoning = result
                        assert statement == "This is my public statement"
                        assert internal_reasoning == ""  # Empty due to exception fallback
                        
                        # Verify both calls were attempted
                        assert mock_runner_class.run.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reasoning_empty_result_handling(
        self, language_manager, settings_reasoning_enabled, mock_participant,
        mock_context, mock_discussion_state, mock_agent_config
    ):
        """Test handling of empty reasoning results."""
        service = DiscussionService(language_manager, settings_reasoning_enabled)
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock reasoning with empty result
            reasoning_result = Mock()
            reasoning_result.final_output = None  # Empty result
            
            # Mock successful statement call
            statement_result = Mock()
            statement_result.final_output = "This is my public statement"
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            with patch.object(service, 'build_internal_reasoning_prompt', return_value="Reasoning prompt"):
                with patch.object(service, 'build_discussion_prompt', return_value="Discussion prompt"):
                    with patch.object(service, 'validate_statement', return_value=True):
                        
                        result = await service.get_participant_statement_with_retry(
                            participant=mock_participant,
                            context=mock_context,
                            discussion_state=mock_discussion_state,
                            agent_config=mock_agent_config,
                            participant_names=["TestAgent"],
                            max_rounds=3
                        )
                        
                        statement, internal_reasoning = result
                        assert statement == "This is my public statement"
                        assert internal_reasoning == ""  # Empty due to None result


class TestDiscussionServiceReasoningIntegration:
    """Test reasoning integration with existing functionality."""
    
    @pytest.fixture
    def service_with_reasoning(self):
        """Service with reasoning enabled."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock message"
        settings = Phase2Settings(reasoning_enabled=True)
        return DiscussionService(language_manager, settings)
    
    def test_build_discussion_prompt_includes_reasoning(self, service_with_reasoning):
        """Test that build_discussion_prompt properly includes internal reasoning."""
        discussion_state = Mock()
        discussion_state.public_history = "Previous discussion"
        
        # Mock the format_group_composition method
        with patch.object(service_with_reasoning, 'format_group_composition', return_value="Group: Alice, Bob"):
            
            result = service_with_reasoning.build_discussion_prompt(
                discussion_state=discussion_state,
                round_num=2,
                max_rounds=5,
                participant_names=["Alice", "Bob"],
                internal_reasoning="My internal thoughts about this decision"
            )
            
            # Should include both the base prompt and reasoning
            assert "Mock message" in result
            assert "My internal thoughts about this decision" in result
            
            # Should include reasoning section markers
            service_with_reasoning.language_manager.get.assert_called()
    
    def test_build_discussion_prompt_without_reasoning(self, service_with_reasoning):
        """Test that build_discussion_prompt works without internal reasoning."""
        discussion_state = Mock()
        discussion_state.public_history = "Previous discussion"
        
        with patch.object(service_with_reasoning, 'format_group_composition', return_value="Group: Alice"):
            
            result = service_with_reasoning.build_discussion_prompt(
                discussion_state=discussion_state,
                round_num=1,
                max_rounds=3,
                participant_names=["Alice"],
                internal_reasoning=""  # Empty reasoning
            )
            
            # Should only include base prompt
            assert "Mock message" in result
            # Should not include reasoning section
            assert "My internal thoughts" not in result
    
    def test_build_internal_reasoning_prompt_exists(self, service_with_reasoning):
        """Test that build_internal_reasoning_prompt method exists and works."""
        discussion_state = Mock()
        discussion_state.public_history = "Previous discussion"
        
        result = service_with_reasoning.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=10
        )
        
        # Should call language manager with correct key
        service_with_reasoning.language_manager.get.assert_called_with(
            "prompts.phase2_internal_reasoning",
            round_number=3,
            max_rounds=10,
            discussion_history="Previous discussion"
        )
        
        assert result == "Mock message"
    
    @pytest.mark.asyncio
    async def test_return_value_format_consistency(self, service_with_reasoning):
        """Test that return value is always (statement, internal_reasoning) tuple."""
        mock_participant = Mock()
        mock_participant.name = "TestAgent"
        mock_participant.agent = Mock()
        
        mock_context = Mock()
        mock_context.round_number = 1
        
        mock_discussion_state = Mock()
        mock_discussion_state.public_history = "History"
        
        mock_agent_config = Mock()
        mock_agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Test with reasoning enabled
            reasoning_result = Mock()
            reasoning_result.final_output = "Internal reasoning"
            statement_result = Mock()
            statement_result.final_output = "Public statement"
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            with patch.object(service_with_reasoning, 'validate_statement', return_value=True):
                
                result = await service_with_reasoning.get_participant_statement_with_retry(
                    participant=mock_participant,
                    context=mock_context,
                    discussion_state=mock_discussion_state,
                    agent_config=mock_agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                # Should always return tuple
                assert isinstance(result, tuple)
                assert len(result) == 2
                statement, internal_reasoning = result
                assert isinstance(statement, str)
                assert isinstance(internal_reasoning, str)
    
    @pytest.mark.asyncio
    async def test_existing_statement_validation_still_works(self, service_with_reasoning):
        """Test that existing statement validation continues to work with reasoning."""
        mock_participant = Mock()
        mock_participant.name = "TestAgent"
        mock_participant.agent = Mock()
        
        mock_context = Mock()
        mock_context.round_number = 1
        
        mock_discussion_state = Mock()
        mock_discussion_state.public_history = "History"
        
        mock_agent_config = Mock()
        mock_agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            reasoning_result = Mock()
            reasoning_result.final_output = "Reasoning"
            statement_result = Mock()
            statement_result.final_output = ""  # Invalid empty statement
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            with patch.object(service_with_reasoning, 'validate_statement', return_value=False):
                
                # Should raise exception due to validation failure
                with pytest.raises((ValueError, Exception)):
                    await service_with_reasoning.get_participant_statement_with_retry(
                        participant=mock_participant,
                        context=mock_context,
                        discussion_state=mock_discussion_state,
                        agent_config=mock_agent_config,
                        participant_names=["TestAgent"],
                        max_rounds=3,
                        max_retries=1  # Limit retries for faster test
                    )


class TestDiscussionServiceReasoningSettings:
    """Test interaction with reasoning settings from Phase2Settings."""
    
    @pytest.mark.asyncio
    async def test_reasoning_timeout_from_settings(self):
        """Test that reasoning timeout comes from Phase2Settings."""
        language_manager = Mock()
        custom_timeout = 90
        settings = Phase2Settings(
            reasoning_enabled=True,
            reasoning_timeout_seconds=custom_timeout
        )
        service = DiscussionService(language_manager, settings)
        
        mock_participant = Mock()
        mock_participant.name = "TestAgent"
        mock_participant.agent = Mock()
        
        mock_context = Mock()
        mock_context.round_number = 1
        
        mock_discussion_state = Mock()
        mock_discussion_state.public_history = "History"
        
        mock_agent_config = Mock()
        mock_agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            with patch('core.services.discussion_service.asyncio.wait_for') as mock_wait_for:
                # Setup successful calls
                reasoning_result = Mock()
                reasoning_result.final_output = "Reasoning"
                statement_result = Mock()
                statement_result.final_output = "Statement"
                
                mock_runner_class.run = AsyncMock()
                mock_runner_class.run.side_effect = [reasoning_result, statement_result]
                mock_wait_for.side_effect = [reasoning_result, statement_result]
                
                with patch.object(service, 'validate_statement', return_value=True):
                    
                    await service.get_participant_statement_with_retry(
                        participant=mock_participant,
                        context=mock_context,
                        discussion_state=mock_discussion_state,
                        agent_config=mock_agent_config,
                        participant_names=["TestAgent"],
                        max_rounds=3
                    )
                    
                    # Verify wait_for was called with custom timeout for reasoning
                    assert mock_wait_for.call_count == 2
                    reasoning_call = mock_wait_for.call_args_list[0]
                    assert reasoning_call[1]['timeout'] == custom_timeout
    
    def test_reasoning_settings_access(self):
        """Test that DiscussionService properly accesses reasoning settings."""
        language_manager = Mock()
        custom_settings = Phase2Settings(
            reasoning_enabled=False,
            reasoning_timeout_seconds=45,
            reasoning_max_retries=1
        )
        service = DiscussionService(language_manager, custom_settings)
        
        # Service should use the provided settings
        assert service.settings.reasoning_enabled is False
        assert service.settings.reasoning_timeout_seconds == 45
        assert service.settings.reasoning_max_retries == 1
        
        # should_use_reasoning should reflect the settings
        assert service.should_use_reasoning() is False


if __name__ == '__main__':
    pytest.main([__file__])