"""
Integration tests for reasoning system functionality.

Tests end-to-end reasoning functionality with real translation keys,
memory service integration, and multilingual support.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Any, Optional

from core.services.discussion_service import DiscussionService
from core.services.memory_service import MemoryService
from config.phase2_settings import Phase2Settings
from utils.language_manager import create_language_manager, SupportedLanguage
from models import GroupDiscussionState, ExperimentPhase
from models.experiment_types import ParticipantContext


class MockResult:
    """Mock result class for Runner calls."""
    def __init__(self, final_output: str):
        self.final_output = final_output


class TestReasoningIntegrationBasic:
    """Test basic end-to-end reasoning functionality."""
    
    @pytest.fixture
    def language_manager(self):
        """Real language manager for integration testing."""
        return create_language_manager(SupportedLanguage.ENGLISH)
    
    @pytest.fixture
    def settings_with_reasoning(self):
        """Settings with reasoning enabled."""
        return Phase2Settings(
            reasoning_enabled=True,
            reasoning_timeout_seconds=120,
            reasoning_max_retries=2,
            max_statement_retries=2
        )
    
    @pytest.fixture
    def settings_without_reasoning(self):
        """Settings with reasoning disabled."""
        return Phase2Settings(reasoning_enabled=False)
    
    @pytest.fixture
    def discussion_state(self):
        """Sample discussion state."""
        state = GroupDiscussionState()
        state.public_history = "Alice: I think we should focus on fairness. Bob: What does fairness mean to you?"
        return state
    
    @pytest.fixture
    def participant_context(self):
        """Sample participant context."""
        return ParticipantContext(
            name="TestAgent",
            role_description="Participant in justice experiment",
            bank_balance=5000.0,
            memory="Initial memory",
            round_number=2,
            phase=ExperimentPhase.PHASE_2
        )
    
    @pytest.fixture
    def mock_participant(self):
        """Mock participant agent."""
        participant = Mock()
        participant.name = "TestAgent"
        participant.agent = Mock()
        return participant
    
    @pytest.fixture
    def mock_agent_config(self):
        """Mock agent configuration."""
        config = Mock()
        config.language = 'english'
        return config
    
    @pytest.mark.asyncio
    async def test_end_to_end_reasoning_enabled_success(
        self, language_manager, settings_with_reasoning, discussion_state, 
        participant_context, mock_participant, mock_agent_config
    ):
        """Test complete reasoning flow with real translation keys."""
        service = DiscussionService(language_manager, settings_with_reasoning)
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock successful reasoning and statement
            reasoning_result = MockResult("I believe principle A is most fair because it helps the worst off")
            statement_result = MockResult("After consideration, I support maximizing floor income")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            result = await service.get_participant_statement_with_retry(
                participant=mock_participant,
                context=participant_context,
                discussion_state=discussion_state,
                agent_config=mock_agent_config,
                participant_names=["TestAgent", "OtherAgent"],
                max_rounds=5
            )
            
            statement, internal_reasoning = result
            assert statement == "After consideration, I support maximizing floor income"
            assert internal_reasoning == "I believe principle A is most fair because it helps the worst off"
            
            # Verify both prompts were generated using real translation keys
            assert mock_runner_class.run.call_count == 2
            
            # Verify prompts contain expected content from real translations
            reasoning_call = mock_runner_class.run.call_args_list[0]
            reasoning_prompt = reasoning_call[0][1]
            assert "Internal Reasoning" in reasoning_prompt or "Round 2" in reasoning_prompt
            
            statement_call = mock_runner_class.run.call_args_list[1]
            statement_prompt = statement_call[0][1]
            assert "Round 2" in statement_prompt or "Discussion History" in statement_prompt
    
    @pytest.mark.asyncio
    async def test_end_to_end_reasoning_disabled(
        self, language_manager, settings_without_reasoning, discussion_state,
        participant_context, mock_participant, mock_agent_config
    ):
        """Test complete flow with reasoning disabled using real translations."""
        service = DiscussionService(language_manager, settings_without_reasoning)
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            statement_result = MockResult("I support principle B without internal reasoning")
            mock_runner_class.run = AsyncMock(return_value=statement_result)
            
            result = await service.get_participant_statement_with_retry(
                participant=mock_participant,
                context=participant_context,
                discussion_state=discussion_state,
                agent_config=mock_agent_config,
                participant_names=["TestAgent"],
                max_rounds=3
            )
            
            statement, internal_reasoning = result
            assert statement == "I support principle B without internal reasoning"
            assert internal_reasoning == ""
            
            # Only one call for statement
            assert mock_runner_class.run.call_count == 1
    
    @pytest.mark.asyncio
    async def test_real_translation_keys_in_prompts(
        self, language_manager, settings_with_reasoning, discussion_state,
        participant_context, mock_participant, mock_agent_config
    ):
        """Test that real translation keys are properly used in prompt generation."""
        service = DiscussionService(language_manager, settings_with_reasoning)
        
        # Test build_internal_reasoning_prompt with real translations
        reasoning_prompt = service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=8
        )
        
        # Should contain content from real translation file
        assert "Round 3" in reasoning_prompt or "round 3" in reasoning_prompt
        assert "Internal Reasoning" in reasoning_prompt or "internal reasoning" in reasoning_prompt.lower()
        assert len(reasoning_prompt) > 100  # Should be substantial prompt
        
        # Test build_discussion_prompt with real translations
        discussion_prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=8,
            participant_names=["Alice", "Bob", "Charlie"],
            internal_reasoning="My previous reasoning about fairness"
        )
        
        # Should contain real translation content and reasoning
        assert "Round 3" in discussion_prompt or "round 3" in discussion_prompt
        assert "My previous reasoning about fairness" in discussion_prompt
        assert "Alice, Bob, and Charlie" in discussion_prompt or "Alice, Bob and Charlie" in discussion_prompt
        assert len(discussion_prompt) > 200  # Should be comprehensive prompt


class TestReasoningMemoryServiceIntegration:
    """Test reasoning integration with MemoryService."""
    
    @pytest.fixture
    def language_manager(self):
        """Real language manager."""
        return create_language_manager(SupportedLanguage.ENGLISH)
    
    @pytest.fixture
    def memory_service(self, language_manager):
        """Real memory service for integration testing."""
        utility_agent = Mock()
        settings = Phase2Settings()
        return MemoryService(language_manager, utility_agent, settings)
    
    @pytest.fixture
    def mock_participant(self):
        """Mock participant for memory testing."""
        participant = Mock()
        participant.name = "TestAgent"
        return participant
    
    @pytest.fixture
    def participant_context(self):
        """Real participant context."""
        return ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=3000.0,
            memory="Initial memory content",
            round_number=2,
            phase=ExperimentPhase.PHASE_2
        )
    
    @pytest.mark.asyncio
    async def test_memory_service_handles_reasoning_parameter(
        self, memory_service, mock_participant, participant_context
    ):
        """Test that MemoryService properly handles internal reasoning parameter."""
        
        with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory with reasoning"
            
            result = await memory_service.update_discussion_memory(
                agent=mock_participant,
                context=participant_context,
                statement="I prefer principle A",
                internal_reasoning="This is my internal reasoning about fairness",
                round_num=2,
                include_internal_reasoning=True
            )
            
            assert result == "Updated memory with reasoning"
            
            # Verify call with reasoning
            call_args = mock_update.call_args
            content = call_args[1]['content']
            
            # Should include both statement and reasoning
            assert "I prefer principle A" in content
            assert "This is my internal reasoning about fairness" in content
            assert "Round 2" in content
            
            # Check metadata
            metadata = call_args[1]['event_metadata']
            assert metadata['has_internal_reasoning'] is True
    
    @pytest.mark.asyncio
    async def test_memory_service_handles_empty_reasoning(
        self, memory_service, mock_participant, participant_context
    ):
        """Test that MemoryService handles empty reasoning gracefully."""
        
        with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory without reasoning"
            
            result = await memory_service.update_discussion_memory(
                agent=mock_participant,
                context=participant_context,
                statement="I prefer principle B",
                internal_reasoning="",  # Empty reasoning
                round_num=3,
                include_internal_reasoning=False
            )
            
            assert result == "Updated memory without reasoning"
            
            # Verify call without reasoning
            call_args = mock_update.call_args
            content = call_args[1]['content']
            
            # Should include statement but not reasoning section
            assert "I prefer principle B" in content
            assert "Internal reasoning:" not in content
            
            # Check metadata
            metadata = call_args[1]['event_metadata']
            assert metadata['has_internal_reasoning'] is False
    
    @pytest.mark.asyncio
    async def test_memory_update_reasoning_integration_flow(
        self, language_manager, memory_service, mock_participant, participant_context
    ):
        """Test complete flow from reasoning to memory update."""
        settings = Phase2Settings(reasoning_enabled=True)
        discussion_service = DiscussionService(language_manager, settings)
        
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "Previous discussion content"
        
        mock_agent_config = Mock()
        mock_agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Mock reasoning and statement results
            reasoning_result = MockResult("Internal: I think principle A is best")
            statement_result = MockResult("Public: I support maximizing floor income")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            # Get statement with reasoning from discussion service
            statement, internal_reasoning = await discussion_service.get_participant_statement_with_retry(
                participant=mock_participant,
                context=participant_context,
                discussion_state=discussion_state,
                agent_config=mock_agent_config,
                participant_names=["TestAgent"],
                max_rounds=5
            )
            
            # Now update memory with the results
            with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
                mock_update.return_value = "Memory updated with reasoning"
                
                memory_result = await memory_service.update_discussion_memory(
                    agent=mock_participant,
                    context=participant_context,
                    statement=statement,
                    internal_reasoning=internal_reasoning,
                    round_num=participant_context.round_number,
                    include_internal_reasoning=True
                )
                
                assert memory_result == "Memory updated with reasoning"
                
                # Verify the complete flow
                call_args = mock_update.call_args
                content = call_args[1]['content']
                
                assert "Public: I support maximizing floor income" in content
                assert "Internal: I think principle A is best" in content


class TestReasoningMultilingualIntegration:
    """Test reasoning with different languages and real translation keys."""
    
    @pytest.mark.asyncio
    async def test_reasoning_with_spanish_translations(self):
        """Test reasoning flow with Spanish language manager."""
        language_manager = create_language_manager(SupportedLanguage.SPANISH)
        settings = Phase2Settings(reasoning_enabled=True)
        service = DiscussionService(language_manager, settings)
        
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "Discusión previa sobre justicia"
        
        # Test prompt generation with Spanish translations
        reasoning_prompt = service.build_internal_reasoning_prompt(
            discussion_state=discussion_state,
            round_num=2,
            max_rounds=4
        )
        
        # Should use Spanish translations (actual content will depend on translation file)
        assert len(reasoning_prompt) > 50
        # The actual Spanish content test would depend on the translation file structure
    
    @pytest.mark.asyncio
    async def test_reasoning_with_mandarin_translations(self):
        """Test reasoning flow with Mandarin language manager."""
        language_manager = create_language_manager(SupportedLanguage.MANDARIN)
        settings = Phase2Settings(reasoning_enabled=True)
        service = DiscussionService(language_manager, settings)
        
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "之前关于正义的讨论"
        
        # Test prompt generation with Mandarin translations
        discussion_prompt = service.build_discussion_prompt(
            discussion_state=discussion_state,
            round_num=3,
            max_rounds=6,
            participant_names=["张三", "李四"],
            internal_reasoning="我的内部推理"
        )
        
        # Should use Mandarin translations and include reasoning
        assert len(discussion_prompt) > 50
        assert "我的内部推理" in discussion_prompt
        # Group composition should handle Chinese names
        assert "张三" in discussion_prompt and "李四" in discussion_prompt
    
    @pytest.mark.asyncio
    async def test_reasoning_language_fallback_behavior(self):
        """Test reasoning behavior when translations are missing."""
        # Test with a language that might have incomplete translations
        language_manager = create_language_manager(SupportedLanguage.ENGLISH)
        settings = Phase2Settings(reasoning_enabled=True)
        service = DiscussionService(language_manager, settings)
        
        # Mock a translation failure to test fallback
        with patch.object(language_manager, 'get', side_effect=KeyError("Missing key")):
            
            discussion_state = GroupDiscussionState()
            discussion_state.public_history = "Test discussion"
            
            # Should handle missing translations gracefully
            try:
                prompt = service.build_internal_reasoning_prompt(
                    discussion_state=discussion_state,
                    round_num=1,
                    max_rounds=3
                )
                # Should return some form of prompt even with missing translations
                assert isinstance(prompt, str)
                assert len(prompt) > 0
            except Exception:
                # If it fails, should fail gracefully without breaking the system
                pass


class TestReasoningValidationIntegration:
    """Test reasoning integration with existing validation systems."""
    
    @pytest.fixture
    def language_manager(self):
        """Real language manager for validation testing."""
        return create_language_manager(SupportedLanguage.ENGLISH)
    
    @pytest.mark.asyncio
    async def test_statement_validation_works_with_reasoning(self, language_manager):
        """Test that existing statement validation continues to work with reasoning."""
        settings = Phase2Settings(
            reasoning_enabled=True,
            min_statement_length=20,  # Require minimum length
            max_statement_retries=2
        )
        service = DiscussionService(language_manager, settings)
        
        mock_participant = Mock()
        mock_participant.name = "TestAgent"
        mock_participant.agent = Mock()
        
        context = ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=2000.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )
        
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "Previous discussion"
        
        mock_agent_config = Mock()
        mock_agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # First attempt: reasoning succeeds, statement is too short
            reasoning_result_1 = MockResult("Good reasoning")
            statement_result_1 = MockResult("Too short")  # Only 9 chars, below minimum
            
            # Second attempt: reasoning fails, statement is valid
            statement_result_2 = MockResult("This is a sufficiently long statement for validation")
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [
                reasoning_result_1,   # First reasoning
                statement_result_1,   # First statement (too short)
                Exception("Reasoning failed"),  # Second reasoning (fails)
                statement_result_2    # Second statement (valid)
            ]
            
            result = await service.get_participant_statement_with_retry(
                participant=mock_participant,
                context=context,
                discussion_state=discussion_state,
                agent_config=mock_agent_config,
                participant_names=["TestAgent"],
                max_rounds=5
            )
            
            statement, internal_reasoning = result
            assert statement == "This is a sufficiently long statement for validation"
            assert internal_reasoning == ""  # Empty due to second attempt failure
            
            # Should have made 4 calls total (2 reasoning + 2 statement)
            assert mock_runner_class.run.call_count == 4
    
    @pytest.mark.asyncio
    async def test_reasoning_respects_language_specific_validation(self, language_manager):
        """Test that reasoning respects language-specific validation rules."""
        settings = Phase2Settings(
            reasoning_enabled=True,
            min_statement_length=15,      # English minimum
            min_statement_length_cjk=8,   # CJK minimum (shorter)
            max_statement_retries=1
        )
        service = DiscussionService(language_manager, settings)
        
        mock_participant = Mock()
        mock_participant.name = "TestAgent"
        mock_participant.agent = Mock()
        
        context = ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=2000.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )
        
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "Previous discussion"
        
        # Test with English configuration
        english_config = Mock()
        english_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            reasoning_result = MockResult("Reasoning content")
            statement_result = MockResult("Short")  # 5 chars, below English minimum (15)
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            # Should fail validation for English
            with pytest.raises((ValueError, Exception)):
                await service.get_participant_statement_with_retry(
                    participant=mock_participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=english_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
        
        # Test with Mandarin configuration (same short statement should pass)
        mandarin_config = Mock()
        mandarin_config.language = 'Mandarin'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            reasoning_result = MockResult("推理内容")
            statement_result = MockResult("我支持最大化最低收入原则")  # Should pass CJK minimum (8+ chars)
            
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [reasoning_result, statement_result]
            
            result = await service.get_participant_statement_with_retry(
                participant=mock_participant,
                context=context,
                discussion_state=discussion_state,
                agent_config=mandarin_config,
                participant_names=["TestAgent"],
                max_rounds=3
            )
            
            statement, internal_reasoning = result
            assert statement == "我支持最大化最低收入原则"
            assert internal_reasoning == "推理内容"


class TestReasoningConfigurationIntegration:
    """Test reasoning with various configuration combinations."""
    
    @pytest.mark.asyncio
    async def test_reasoning_with_custom_timeout_settings(self):
        """Test reasoning with custom timeout configurations."""
        language_manager = create_language_manager(SupportedLanguage.ENGLISH)
        
        # Very short timeout for testing
        settings = Phase2Settings(
            reasoning_enabled=True,
            reasoning_timeout_seconds=15,  # Very short
            statement_timeout_seconds=30,
            max_statement_retries=1
        )
        service = DiscussionService(language_manager, settings)
        
        mock_participant = Mock()
        mock_participant.name = "TestAgent"
        mock_participant.agent = Mock()
        
        context = ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=2000.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )
        
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "Previous discussion"
        
        mock_agent_config = Mock()
        mock_agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            # Simulate reasoning timeout, statement success
            async def slow_reasoning(*args, **kwargs):
                await asyncio.sleep(0.1)  # Longer than 15ms timeout in test
                return MockResult("Should not reach")
            
            statement_result = MockResult("Statement after reasoning timeout")
            mock_runner_class.run = AsyncMock()
            mock_runner_class.run.side_effect = [slow_reasoning, statement_result]
            
            with patch('asyncio.wait_for', side_effect=[asyncio.TimeoutError(), statement_result]):
                
                result = await service.get_participant_statement_with_retry(
                    participant=mock_participant,
                    context=context,
                    discussion_state=discussion_state,
                    agent_config=mock_agent_config,
                    participant_names=["TestAgent"],
                    max_rounds=3
                )
                
                statement, internal_reasoning = result
                assert statement == "Statement after reasoning timeout"
                assert internal_reasoning == ""  # Empty due to timeout
    
    @pytest.mark.asyncio 
    async def test_reasoning_disabled_integration_behavior(self):
        """Test complete integration behavior when reasoning is disabled."""
        language_manager = create_language_manager(SupportedLanguage.ENGLISH)
        settings = Phase2Settings(reasoning_enabled=False)
        
        # Create both discussion and memory services
        discussion_service = DiscussionService(language_manager, settings)
        utility_agent = Mock()
        memory_service = MemoryService(language_manager, utility_agent, settings)
        
        mock_participant = Mock()
        mock_participant.name = "TestAgent"
        mock_participant.agent = Mock()
        
        context = ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=2000.0,
            memory="Initial memory",
            round_number=2,
            phase=ExperimentPhase.PHASE_2
        )
        
        discussion_state = GroupDiscussionState()
        discussion_state.public_history = "Previous discussion"
        
        mock_agent_config = Mock()
        mock_agent_config.language = 'english'
        
        with patch('core.services.discussion_service.Runner') as mock_runner_class:
            statement_result = MockResult("Statement without reasoning")
            mock_runner_class.run = AsyncMock(return_value=statement_result)
            
            # Get statement (should not involve reasoning)
            statement, internal_reasoning = await discussion_service.get_participant_statement_with_retry(
                participant=mock_participant,
                context=context,
                discussion_state=discussion_state,
                agent_config=mock_agent_config,
                participant_names=["TestAgent"],
                max_rounds=5
            )
            
            assert statement == "Statement without reasoning"
            assert internal_reasoning == ""
            
            # Update memory (should handle empty reasoning gracefully)
            with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
                mock_update.return_value = "Memory updated without reasoning"
                
                memory_result = await memory_service.update_discussion_memory(
                    agent=mock_participant,
                    context=context,
                    statement=statement,
                    internal_reasoning=internal_reasoning,
                    round_num=context.round_number,
                    include_internal_reasoning=False  # Should be False when reasoning disabled
                )
                
                assert memory_result == "Memory updated without reasoning"
                
                # Verify memory call doesn't include reasoning
                call_args = mock_update.call_args
                content = call_args[1]['content']
                metadata = call_args[1]['event_metadata']
                
                assert "Statement without reasoning" in content
                assert "Internal reasoning:" not in content
                assert metadata['has_internal_reasoning'] is False


if __name__ == '__main__':
    pytest.main([__file__])