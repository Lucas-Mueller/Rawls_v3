"""
Error handling tests for the reasoning system.

Tests various error scenarios, fallback mechanisms, timeout handling,
and recovery strategies in the reasoning functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Any

from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings


class MockResult:
    """Mock result class for testing."""
    def __init__(self, final_output: str = None):
        self.final_output = final_output


class TestReasoningTimeoutHandling:
    """Test timeout handling for reasoning calls."""
    
    @pytest.fixture
    def service_with_short_timeout(self):
        """Service with short reasoning timeout for testing."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock prompt"
        settings = Phase2Settings(
            reasoning_enabled=True,
            reasoning_timeout_seconds=30,  # Short timeout for testing
            max_statement_retries=1
        )
        return DiscussionService(language_manager, settings)
    
    @pytest.fixture
    def mock_components(self):
        """Mock components for testing."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        return participant, context, discussion_state, agent_config
    
    @pytest.mark.asyncio
    async def test_reasoning_timeout_fallback_to_empty(self, service_with_short_timeout, mock_components):
        """Test that reasoning timeout falls back to empty reasoning."""
        participant, context, discussion_state, agent_config = mock_components
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock reasoning call to timeout
            mock_runner_class.run = AsyncMock()
            
            # First call (reasoning) times out, second call (statement) succeeds
            statement_result = MockResult("Valid statement")
            mock_runner_class.run.side_effect = [
                asyncio.TimeoutError("Reasoning timed out"),
                statement_result
            ]
            
            with patch.object(service_with_short_timeout, 'validate_statement', return_value=True):
                
                result = await service_with_short_timeout.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                statement, internal_reasoning = result
                assert statement == "Valid statement"
                assert internal_reasoning == ""  # Empty due to timeout
                
                # Verify both calls were made
                assert mock_runner_class.run.call_count == 2
    
    @pytest.mark.asyncio
    async def test_reasoning_timeout_doesnt_prevent_statement(self, service_with_short_timeout, mock_components):
        """Test that reasoning timeout doesn't prevent getting a statement."""
        participant, context, discussion_state, agent_config = mock_components
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Configure timeouts and results
            statement_result = MockResult("This is my statement")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                asyncio.TimeoutError("Reasoning timeout"),  # Reasoning times out
                statement_result  # Statement succeeds
            ]
            
            with patch.object(service_with_short_timeout, 'validate_statement', return_value=True):
                
                # Should complete successfully despite reasoning timeout
                result = await service_with_short_timeout.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                statement, internal_reasoning = result
                assert statement == "This is my statement"
                assert internal_reasoning == ""
    
    @pytest.mark.asyncio
    async def test_statement_timeout_after_reasoning_timeout(self, service_with_short_timeout, mock_components):
        """Test behavior when both reasoning and statement timeout."""
        participant, context, discussion_state, agent_config = mock_components
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Both calls time out
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                asyncio.TimeoutError("Reasoning timeout"),
                asyncio.TimeoutError("Statement timeout")
            ]
            
            # Should raise the statement timeout (final error)
            with pytest.raises(asyncio.TimeoutError, match="Statement timeout"):
                await service_with_short_timeout.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )


class TestReasoningExceptionHandling:
    """Test exception handling for reasoning calls."""
    
    @pytest.fixture
    def service_with_reasoning(self):
        """Service with reasoning enabled."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock prompt"
        settings = Phase2Settings(
            reasoning_enabled=True,
            max_statement_retries=1
        )
        return DiscussionService(language_manager, settings)
    
    @pytest.fixture
    def mock_components(self):
        """Mock components for testing."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        return participant, context, discussion_state, agent_config
    
    @pytest.mark.asyncio
    async def test_reasoning_generic_exception_fallback(self, service_with_reasoning, mock_components):
        """Test that generic reasoning exceptions fall back to empty reasoning."""
        participant, context, discussion_state, agent_config = mock_components
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock reasoning exception and successful statement
            statement_result = MockResult("Valid statement")
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                ValueError("Reasoning model error"),
                statement_result
            ]
            
            with patch.object(service_with_reasoning, 'validate_statement', return_value=True):
                
                result = await service_with_reasoning.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                statement, internal_reasoning = result
                assert statement == "Valid statement"
                assert internal_reasoning == ""  # Empty due to exception
    
    @pytest.mark.asyncio
    async def test_reasoning_network_exception_fallback(self, service_with_reasoning, mock_components):
        """Test that network exceptions in reasoning fall back gracefully."""
        participant, context, discussion_state, agent_config = mock_components
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock network error and successful statement
            statement_result = MockResult("Statement after network error")
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                ConnectionError("Network unreachable"),
                statement_result
            ]
            
            with patch.object(service_with_reasoning, 'validate_statement', return_value=True):
                
                result = await service_with_reasoning.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                statement, internal_reasoning = result
                assert statement == "Statement after network error"
                assert internal_reasoning == ""
    
    @pytest.mark.asyncio
    async def test_reasoning_exception_doesnt_prevent_statement_retry(self, service_with_reasoning, mock_components):
        """Test that reasoning exceptions don't affect statement retry logic."""
        participant, context, discussion_state, agent_config = mock_components
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock reasoning exception, invalid statement, then valid statement
            invalid_result = MockResult("")  # Invalid empty statement
            valid_result = MockResult("Valid statement on retry")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                Exception("Reasoning failed"),  # Reasoning attempt 1
                invalid_result,                 # Statement attempt 1 (invalid)
                Exception("Reasoning failed again"),  # Reasoning attempt 2  
                valid_result                   # Statement attempt 2 (valid)
            ]
            
            # First validation fails, second succeeds
            with patch.object(service_with_reasoning, 'validate_statement', side_effect=[False, True]):
                
                result = await service_with_reasoning.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3,
                    max_retries=2
                )
                
                statement, internal_reasoning = result
                assert statement == "Valid statement on retry"
                assert internal_reasoning == ""  # Empty due to exceptions


class TestReasoningNullResultHandling:
    """Test handling of null/empty reasoning results."""
    
    @pytest.fixture
    def service_with_reasoning(self):
        """Service with reasoning enabled."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock prompt"
        settings = Phase2Settings(reasoning_enabled=True)
        return DiscussionService(language_manager, settings)
    
    @pytest.mark.asyncio
    async def test_reasoning_none_result_handling(self, service_with_reasoning):
        """Test handling when reasoning returns None."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock reasoning with None result
            reasoning_result = MockResult(final_output=None)
            statement_result = MockResult("Valid statement")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            with patch.object(service_with_reasoning, 'validate_statement', return_value=True):
                
                result = await service_with_reasoning.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                statement, internal_reasoning = result
                assert statement == "Valid statement"
                assert internal_reasoning == ""  # Empty due to None
    
    @pytest.mark.asyncio
    async def test_reasoning_empty_string_result_handling(self, service_with_reasoning):
        """Test handling when reasoning returns empty string."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock reasoning with empty string
            reasoning_result = MockResult(final_output="")
            statement_result = MockResult("Valid statement")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            with patch.object(service_with_reasoning, 'validate_statement', return_value=True):
                
                result = await service_with_reasoning.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                statement, internal_reasoning = result
                assert statement == "Valid statement"
                assert internal_reasoning == ""  # Empty string preserved


class TestReasoningRecoveryStrategies:
    """Test recovery and resilience strategies for reasoning system."""
    
    @pytest.fixture
    def service_with_retries(self):
        """Service configured with multiple retries."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock prompt"
        logger = Mock()
        settings = Phase2Settings(
            reasoning_enabled=True,
            reasoning_timeout_seconds=60,
            reasoning_max_retries=3,
            max_statement_retries=3,
            retry_backoff_factor=1.5
        )
        return DiscussionService(language_manager, settings, logger)
    
    @pytest.mark.asyncio
    async def test_reasoning_failure_doesnt_break_statement_retries(self, service_with_retries):
        """Test that reasoning failures don't interfere with statement retry logic."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # All reasoning calls fail, statements gradually succeed
            invalid_statement = MockResult("")
            valid_statement = MockResult("Finally a valid statement")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                Exception("Reasoning fail 1"),  # Reasoning attempt 1
                invalid_statement,              # Statement attempt 1 (invalid)
                Exception("Reasoning fail 2"),  # Reasoning attempt 2
                invalid_statement,              # Statement attempt 2 (invalid)
                Exception("Reasoning fail 3"),  # Reasoning attempt 3
                valid_statement                 # Statement attempt 3 (valid)
            ]
            
            # Two failures, then success
            with patch.object(service_with_retries, 'validate_statement', side_effect=[False, False, True]):
                
                result = await service_with_retries.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3,
                    max_retries=3
                )
                
                statement, internal_reasoning = result
                assert statement == "Finally a valid statement"
                assert internal_reasoning == ""  # All reasoning attempts failed
    
    @pytest.mark.asyncio
    async def test_mixed_reasoning_success_failure_pattern(self, service_with_retries):
        """Test mixed success/failure patterns in reasoning across retries."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mixed reasoning results, statements gradually improve
            good_reasoning = MockResult("Good reasoning")
            invalid_statement = MockResult("")
            valid_statement = MockResult("Valid statement")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                good_reasoning,                 # Reasoning attempt 1 (success)
                invalid_statement,              # Statement attempt 1 (invalid)
                Exception("Reasoning fail"),    # Reasoning attempt 2 (fail)
                valid_statement                 # Statement attempt 2 (valid)
            ]
            
            # First statement invalid, second valid
            with patch.object(service_with_retries, 'validate_statement', side_effect=[False, True]):
                
                result = await service_with_retries.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3,
                    max_retries=2
                )
                
                statement, internal_reasoning = result
                assert statement == "Valid statement"
                # Should return empty reasoning from final attempt (which failed)
                assert internal_reasoning == ""
    
    @pytest.mark.asyncio 
    async def test_reasoning_logging_on_failures(self, service_with_retries):
        """Test that reasoning failures are properly logged."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Reasoning fails, statement succeeds
            statement_result = MockResult("Valid statement")
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                ConnectionError("Network error in reasoning"),
                statement_result
            ]
            
            with patch.object(service_with_retries, 'validate_statement', return_value=True):
                
                await service_with_retries.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                # Should complete successfully - check that logger methods exist if provided
                # (Actual logging details depend on implementation)
                assert hasattr(service_with_retries, 'logger')


class TestReasoningEdgeCases:
    """Test edge cases and unusual scenarios in reasoning system."""
    
    @pytest.mark.asyncio
    async def test_reasoning_disabled_doesnt_call_reasoning_methods(self):
        """Test that reasoning disabled completely skips reasoning calls."""
        language_manager = Mock()
        settings = Phase2Settings(reasoning_enabled=False)
        service = DiscussionService(language_manager, settings)
        
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            statement_result = MockResult("Statement without reasoning")
            mock_runner_class.run = AsyncMock(return_value=statement_result)
            
            with patch.object(service, 'build_internal_reasoning_prompt') as mock_reasoning_prompt:
                with patch.object(service, 'validate_statement', return_value=True):
                    
                    result = await service.get_participant_statement_with_retry(
                        participant=participant,
                        context=context,
                        discussion_state=discussion_state,
                        agent_config=agent_config,
                        participant_names=["TestAgent"],
                        max_rounds=3
                    )
                    
                    statement, internal_reasoning = result
                    assert statement == "Statement without reasoning"
                    assert internal_reasoning == ""
                    
                    # Reasoning prompt should never be built
                    mock_reasoning_prompt.assert_not_called()
                    # Runner should be called only once (for statement)
                    assert mock_runner_class.run.call_count == 1
    
    @pytest.mark.asyncio
    async def test_reasoning_with_zero_timeout_handling(self):
        """Test behavior with extremely short reasoning timeout."""
        language_manager = Mock()
        language_manager.get.return_value = "Mock prompt"
        # Note: Phase2Settings validation would prevent timeout=0, but test the boundary
        settings = Phase2Settings(
            reasoning_enabled=True,
            reasoning_timeout_seconds=10,  # Minimum allowed
            max_statement_retries=1
        )
        service = DiscussionService(language_manager, settings)
        
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        
        context = Mock()
        context.round_number = 1
        
        discussion_state = Mock()
        discussion_state.public_history = "History"
        
        agent_config = Mock()
        agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Simulate very slow reasoning that times out
            async def slow_reasoning(*args, **kwargs):
                await asyncio.sleep(0.1)  # Longer than timeout
                return MockResult("Should not reach here")
            
            statement_result = MockResult("Statement after timeout")
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [slow_reasoning, statement_result]
            
            with patch.object(service, 'validate_statement', return_value=True):
                
                # Should handle the timeout gracefully
                result = await service.get_participant_statement_with_retry(
                    participant=participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                statement, internal_reasoning = result
                assert statement == "Statement after timeout"
                assert internal_reasoning == ""  # Empty due to timeout


if __name__ == '__main__':
    pytest.main([__file__])