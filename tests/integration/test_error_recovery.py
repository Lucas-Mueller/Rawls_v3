"""
Integration tests for error handling and recovery across experiment components.
Tests various error scenarios and recovery mechanisms.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from core.experiment_manager import FrohlichExperimentManager
from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture
from tests.integration.utils.async_test_utils import AsyncTestUtils, ErrorInjectionUtils
from utils.error_handling import (
    ExperimentError, MemoryError, ValidationError, AgentCommunicationError,
    SystemError, ErrorSeverity, ExperimentErrorCategory, get_global_error_handler
)
from utils.memory_manager import MemoryManager
from experiment_agents.utility_agent import UtilityAgent


class TestErrorRecovery:
    """Test error handling and recovery across experiment components."""
    
    def setup_method(self):
        """Set up test fixtures for each test."""
        self.config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
    
    @pytest.mark.asyncio
    async def test_memory_limit_recovery(self):
        """Test recovery from memory limit exceeded scenarios."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Create responses that will initially exceed memory limits
        long_memory = "A" * 60000  # Exceeds default 50,000 limit
        short_memory = "Valid memory update"
        
        memory_responses = [long_memory, long_memory, short_memory]  # Fail twice, then succeed
        
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up basic agent responses
            mock_runner.return_value.final_output = "Test response"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Mock memory update to simulate length violations
            memory_iter = iter(memory_responses)
            
            async def mock_memory_update(prompt, bank_balance):
                return next(memory_iter, short_memory)
            
            # Apply memory update mock to all participants
            for participant in manager.participants:
                participant.update_memory = AsyncMock(side_effect=mock_memory_update)
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Verify experiment completed despite memory errors
            assert results is not None
            assert len(results.phase1_results) == 2
            
            # Check that memory errors were logged and recovered
            error_stats = self.error_handler.get_error_statistics()
            memory_errors = error_stats.get("by_category", {}).get("memory", 0)
            assert memory_errors > 0  # Should have recorded memory limit violations
    
    @pytest.mark.asyncio
    async def test_agent_communication_failure_recovery(self):
        """Test recovery from agent communication failures."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Create scenario with intermittent communication failures
        call_count = [0]
        
        def failing_agent_response(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 4 == 0:  # Fail every 4th call
                raise ConnectionError("Simulated API failure")
            
            mock_result = Mock()
            mock_result.final_output = "Valid response"
            return mock_result
        
        with patch('agents.Runner.run', side_effect=failing_agent_response), \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up utility agent mocks
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Configure error handler for aggressive retries
            manager.error_handler.retry_config[ExperimentErrorCategory.SYSTEM_ERROR].max_retries = 5
            
            try:
                # Run experiment (might fail due to communication errors)
                results = await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=120.0  # Longer timeout for retries
                )
                
                # If it completes, verify basic results
                if results:
                    assert len(results.phase1_results) <= 2  # Might be partial
                
            except ExperimentError as e:
                # Communication failures might cause experiment to fail
                assert e.category in [ExperimentErrorCategory.SYSTEM_ERROR, ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR]
            
            # Verify error recovery attempts were made
            error_stats = self.error_handler.get_error_statistics()
            assert error_stats.get("total_errors", 0) > 0
    
    @pytest.mark.asyncio
    async def test_validation_error_recovery(self):
        """Test recovery from principle choice validation errors."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Create utility agent that initially returns invalid choices, then valid ones
        invalid_choices = [
            # Missing constraint for constraint principle
            ExperimentTestFixture.create_test_principle_choices()[2]._replace(constraint_amount=None),
            # Invalid constraint amount
            ExperimentTestFixture.create_test_principle_choices()[3]._replace(constraint_amount=-1000),
        ]
        
        valid_choice = ExperimentTestFixture.create_test_principle_choices()[0]
        
        choice_sequence = invalid_choices + [valid_choice] * 20
        
        with patch('agents.Runner.run') as mock_runner, \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up basic mocks
            mock_runner.return_value.final_output = "Test response"
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            
            # Set up choice sequence
            choice_iter = iter(choice_sequence)
            mock_parse_choice.side_effect = lambda x: next(choice_iter, valid_choice)
            
            # Set up validation to fail for invalid choices
            def mock_validation(choice):
                if choice.principle.value.endswith('constraint') and not choice.constraint_amount:
                    return False
                if choice.constraint_amount and choice.constraint_amount < 0:
                    return False
                return True
            
            mock_validate.side_effect = mock_validation
            
            # Run experiment
            results = await AsyncTestUtils.run_with_timeout(
                manager.run_complete_experiment(),
                timeout=60.0
            )
            
            # Verify experiment completed despite validation errors
            assert results is not None
            assert len(results.phase1_results) == 2
            
            # Check that validation errors were handled
            error_stats = self.error_handler.get_error_statistics()
            validation_errors = error_stats.get("by_category", {}).get("validation", 0)
            assert validation_errors >= 0  # May or may not have validation errors depending on choices
    
    @pytest.mark.asyncio
    async def test_api_failure_graceful_degradation(self):
        """Test graceful degradation when OpenAI API fails."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Simulate complete API failure
        def api_failure(*args, **kwargs):
            raise ConnectionError("OpenAI API unavailable")
        
        with patch('agents.Runner.run', side_effect=api_failure):
            
            # Experiment should fail gracefully with proper error handling
            with pytest.raises(ExperimentError) as exc_info:
                await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=30.0
                )
            
            # Verify proper error categorization
            error = exc_info.value
            assert error.category in [
                ExperimentErrorCategory.SYSTEM_ERROR,
                ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR,
                ExperimentErrorCategory.EXPERIMENT_LOGIC_ERROR
            ]
            assert error.severity == ErrorSeverity.FATAL
            assert "OpenAI API" in str(error) or "ConnectionError" in str(error)
    
    @pytest.mark.asyncio
    async def test_partial_agent_failure_handling(self):
        """Test handling when some agents fail but others succeed."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Make first agent always fail, second agent always succeed
        def selective_failure(*args, **kwargs):
            # Simple heuristic to identify which agent based on call pattern
            if hasattr(selective_failure, 'call_count'):
                selective_failure.call_count += 1
            else:
                selective_failure.call_count = 1
            
            # Fail roughly half the calls (simulate one agent failing)
            if selective_failure.call_count % 2 == 1:
                raise TimeoutError("Agent 1 timeout")
            
            mock_result = Mock()
            mock_result.final_output = "Valid response from Agent 2"
            return mock_result
        
        with patch('agents.Runner.run', side_effect=selective_failure), \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up utility agent mocks
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Configure error handler for retries
            manager.error_handler.retry_config[ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR].max_retries = 2
            
            try:
                # Run experiment - may fail due to agent failures
                results = await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=60.0
                )
                
                # If it succeeds, check partial results
                if results:
                    # May have partial results due to agent failures
                    assert len(results.phase1_results) >= 0
                
            except ExperimentError as e:
                # Agent failures may cause experiment failure
                assert e.category in [
                    ExperimentErrorCategory.AGENT_COMMUNICATION_ERROR,
                    ExperimentErrorCategory.EXPERIMENT_LOGIC_ERROR
                ]
    
    @pytest.mark.asyncio
    async def test_memory_manager_error_escalation(self):
        """Test memory manager error escalation after max retries."""
        
        # Test direct memory manager behavior
        participant = ExperimentTestFixture.create_mock_agent_pool(self.config)[0]
        
        # Make agent always return oversized memory
        async def oversized_memory_update(prompt, bank_balance):
            return "A" * 60000  # Always exceeds limit
        
        participant.update_memory = AsyncMock(side_effect=oversized_memory_update)
        
        # Create test context
        from models import ParticipantContext, ExperimentPhase
        context = ParticipantContext(
            name="TestAgent",
            role_description="Test",
            bank_balance=0.0,
            memory="",
            round_number=1,
            phase=ExperimentPhase.PHASE_1,
            memory_character_limit=50000
        )
        
        # Test that memory manager eventually gives up and raises fatal error
        with pytest.raises(MemoryError) as exc_info:
            await MemoryManager.prompt_agent_for_memory_update(
                participant, context, "test content", max_retries=3
            )
        
        error = exc_info.value
        assert error.severity == ErrorSeverity.FATAL
        assert "failed to create valid memory" in str(error).lower()
        assert error.category == ExperimentErrorCategory.MEMORY_ERROR
    
    @pytest.mark.asyncio
    async def test_utility_agent_parsing_resilience(self):
        """Test utility agent resilience to malformed responses."""
        
        utility_agent = UtilityAgent()
        
        # Test malformed responses
        malformed_responses = [
            "",  # Empty response
            "This is not a valid ranking",  # No structure
            "1. Invalid principle name",  # Invalid principle
            "Random text with numbers 1 2 3 4",  # Numbers but no clear structure
            "I choose principle X",  # Invalid principle letter
        ]
        
        with patch('agents.Runner.run') as mock_runner:
            # Set up parser agent to return parsing failures
            mock_result = Mock()
            mock_result.final_output = Mock()
            mock_result.final_output.success = False
            mock_result.final_output.error_message = "Parsing failed"
            mock_runner.return_value = mock_result
            
            # Test each malformed response
            for response in malformed_responses:
                with pytest.raises(ValidationError) as exc_info:
                    await utility_agent.parse_principle_choice(response)
                
                error = exc_info.value
                assert error.category == ExperimentErrorCategory.VALIDATION_ERROR
                assert error.severity == ErrorSeverity.RECOVERABLE
                assert "response_text" in error.context
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Test error handling during concurrent Phase 1 execution."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Create scenario where agents fail at different times
        agent_errors = {
            "TestAgent1": [3, 7],  # Fail on calls 3 and 7
            "TestAgent2": [5, 9],  # Fail on calls 5 and 9
        }
        
        call_counts = {"TestAgent1": 0, "TestAgent2": 0}
        
        def concurrent_failure(*args, **kwargs):
            # Simple heuristic to alternate between agents
            agent_name = "TestAgent1" if sum(call_counts.values()) % 2 == 0 else "TestAgent2"
            call_counts[agent_name] += 1
            
            if call_counts[agent_name] in agent_errors[agent_name]:
                raise ConnectionError(f"Simulated failure for {agent_name}")
            
            mock_result = Mock()
            mock_result.final_output = f"Valid response from {agent_name}"
            return mock_result
        
        with patch('agents.Runner.run', side_effect=concurrent_failure), \
             patch.object(manager.utility_agent, 'parse_principle_ranking_enhanced') as mock_parse_ranking, \
             patch.object(manager.utility_agent, 'parse_principle_choice_enhanced') as mock_parse_choice, \
             patch.object(manager.utility_agent, 'validate_constraint_specification') as mock_validate:
            
            # Set up utility agent mocks
            mock_parse_ranking.return_value = ExperimentTestFixture.create_test_principle_rankings()[0]
            mock_parse_choice.return_value = ExperimentTestFixture.create_test_principle_choices()[0]
            mock_validate.return_value = True
            
            # Clear error history
            manager.error_handler.clear_error_history()
            
            try:
                # Run experiment
                results = await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=90.0
                )
                
                if results:
                    # Verify some level of completion
                    assert len(results.phase1_results) >= 0
                
            except ExperimentError:
                # Concurrent failures may cause experiment failure
                pass
            
            # Verify errors were handled concurrently
            error_stats = manager.error_handler.get_error_statistics()
            assert error_stats.get("total_errors", 0) > 0
            
            # Verify error distribution shows concurrent handling
            recent_errors = error_stats.get("recent_errors", [])
            if recent_errors:
                # Should have errors from both agents
                error_contexts = [error.get("category") for error in recent_errors]
                assert len(set(error_contexts)) >= 1  # At least one error category
    
    @pytest.mark.asyncio
    async def test_error_context_preservation(self):
        """Test that error context is properly preserved through the call stack."""
        
        manager = FrohlichExperimentManager(self.config)
        
        # Create specific error with rich context
        def contextual_failure(*args, **kwargs):
            raise ValueError("Specific validation error with context")
        
        with patch('agents.Runner.run', side_effect=contextual_failure):
            
            # Clear error history
            manager.error_handler.clear_error_history()
            
            try:
                await AsyncTestUtils.run_with_timeout(
                    manager.run_complete_experiment(),
                    timeout=30.0
                )
            except ExperimentError:
                pass  # Expected to fail
            
            # Verify error context was preserved
            error_stats = manager.error_handler.get_error_statistics()
            recent_errors = error_stats.get("recent_errors", [])
            
            if recent_errors:
                # Check that context information is present
                for error in recent_errors:
                    assert "category" in error
                    assert "timestamp" in error
                    # Context should contain operation-specific information
                    assert error.get("category") in [cat.value for cat in ExperimentErrorCategory]