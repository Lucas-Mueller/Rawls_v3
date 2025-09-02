"""
Unit tests for MemoryService.

Tests the unified memory management service for consistent memory updates,
content truncation, event routing, and integration with SelectiveMemoryManager.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from core.services.memory_service import MemoryService, MemoryEventType
from config.phase2_settings import Phase2Settings
from models.experiment_types import ParticipantContext, ExperimentPhase
from experiment_agents.participant_agent import ParticipantAgent


class TestMemoryServiceInitialization:
    """Test MemoryService initialization and configuration."""
    
    def test_memory_service_init_with_required_dependencies(self):
        """Test MemoryService initializes with required dependencies."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        
        service = MemoryService(language_manager, utility_agent, settings)
        
        assert service.language_manager == language_manager
        assert service.utility_agent == utility_agent
        assert service.settings == settings
        assert service.statement_max_chars == 300
        assert service.reasoning_max_chars == 200
        assert service.memory_guidance_style == 'narrative'  # Default
    
    def test_memory_service_init_with_custom_guidance_style(self):
        """Test MemoryService uses custom memory guidance style from config."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        config = Mock()
        config.memory_guidance_style = 'structured'
        
        service = MemoryService(language_manager, utility_agent, settings, config=config)
        
        assert service.memory_guidance_style == 'structured'
    
    def test_memory_service_init_with_optional_logger(self):
        """Test MemoryService accepts optional logger."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        custom_logger = Mock()
        
        service = MemoryService(language_manager, utility_agent, settings, custom_logger)
        
        assert service.logger == custom_logger


class TestMemoryServiceTruncation:
    """Test content truncation functionality."""
    
    @pytest.fixture
    def memory_service(self):
        """Create MemoryService for testing."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        return MemoryService(language_manager, utility_agent, settings)
    
    def test_discussion_statement_truncation_long_statement(self, memory_service):
        """Test truncation of long discussion statements."""
        long_statement = "This is a very long statement that exceeds the 300 character limit. " * 10
        content = f"Round 1: Your statement: {long_statement}\nInternal reasoning: Some reasoning"
        
        truncated = memory_service.apply_content_truncation(content, MemoryEventType.DISCUSSION_STATEMENT)
        
        # Extract statement part to verify truncation
        statement_line = [line for line in truncated.split('\n') if 'Your statement:' in line][0]
        statement_part = statement_line.split('statement:', 1)[1].strip()
        
        assert len(statement_part) <= 303  # 300 + '...'
        assert statement_part.endswith('...')
        assert 'Internal reasoning:' in truncated  # Reasoning line preserved
    
    def test_discussion_reasoning_truncation_long_reasoning(self, memory_service):
        """Test truncation of long internal reasoning."""
        long_reasoning = "This is very detailed internal reasoning that goes on and on. " * 10
        content = f"Round 1: Your statement: Brief statement\nInternal reasoning: {long_reasoning}"
        
        truncated = memory_service.apply_content_truncation(content, MemoryEventType.DISCUSSION_STATEMENT)
        
        # Extract reasoning part to verify truncation
        reasoning_line = [line for line in truncated.split('\n') if 'Internal reasoning:' in line][0]
        reasoning_part = reasoning_line.split(':', 1)[1].strip()
        
        assert len(reasoning_part) <= 203  # 200 + '...'
        assert reasoning_part.endswith('...')
        assert 'Your statement: Brief statement' in truncated  # Statement preserved
    
    def test_non_discussion_content_no_truncation(self, memory_service):
        """Test that non-discussion content is not truncated."""
        long_content = "This is some very long content that would normally be truncated. " * 20
        
        result = memory_service.apply_content_truncation(long_content, MemoryEventType.FINAL_RESULTS)
        
        assert result == long_content  # No truncation applied
    
    def test_empty_content_truncation(self, memory_service):
        """Test truncation handles empty content gracefully."""
        result = memory_service.apply_content_truncation("", MemoryEventType.DISCUSSION_STATEMENT)
        
        assert result == ""
    
    def test_content_within_limits_no_truncation(self, memory_service):
        """Test that content within limits is not truncated."""
        short_content = "Round 1: Your statement: Short statement\nInternal reasoning: Brief reasoning"
        
        result = memory_service.apply_content_truncation(short_content, MemoryEventType.DISCUSSION_STATEMENT)
        
        assert result == short_content  # No changes


class TestMemoryServiceSelectiveUpdate:
    """Test the main selective memory update functionality."""
    
    @pytest.fixture
    def memory_service(self):
        """Create MemoryService with mocked dependencies."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        logger = Mock()
        return MemoryService(language_manager, utility_agent, settings, logger)
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock participant agent."""
        agent = Mock(spec=ParticipantAgent)
        agent.name = "TestAgent"
        return agent
    
    @pytest.fixture
    def mock_context(self):
        """Create mock participant context."""
        context = ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=1000.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )
        return context
    
    @pytest.mark.asyncio
    async def test_selective_update_calls_selective_memory_manager(self, memory_service, mock_agent, mock_context):
        """Test that update_memory_selective calls SelectiveMemoryManager correctly."""
        with patch('core.services.memory_service.SelectiveMemoryManager.update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            result = await memory_service.update_memory_selective(
                agent=mock_agent,
                context=mock_context,
                content="Test content",
                event_type=MemoryEventType.DISCUSSION_STATEMENT
            )
            
            assert result == "Updated memory"
            mock_update.assert_called_once()
            
            # Verify call arguments
            call_args = mock_update.call_args
            assert call_args[1]['agent'] == mock_agent
            assert call_args[1]['context'] == mock_context
            assert call_args[1]['event_type'] == MemoryEventType.DISCUSSION_STATEMENT
            assert call_args[1]['language_manager'] == memory_service.language_manager
            assert call_args[1]['utility_agent'] == memory_service.utility_agent
            assert call_args[1]['memory_guidance_style'] == 'narrative'
    
    @pytest.mark.asyncio
    async def test_selective_update_applies_truncation(self, memory_service, mock_agent, mock_context):
        """Test that selective update applies content truncation."""
        long_content = "Round 1: Your statement: " + "Long statement " * 50 + "\nInternal reasoning: " + "Long reasoning " * 30
        
        with patch('core.services.memory_service.SelectiveMemoryManager.update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            await memory_service.update_memory_selective(
                agent=mock_agent,
                context=mock_context,
                content=long_content,
                event_type=MemoryEventType.DISCUSSION_STATEMENT
            )
            
            # Verify truncated content was passed
            call_args = mock_update.call_args
            passed_content = call_args[1]['content']
            
            # Statement should be truncated
            statement_line = [line for line in passed_content.split('\n') if 'Your statement:' in line][0]
            statement_part = statement_line.split('statement:', 1)[1].strip()
            assert len(statement_part) <= 303
            
            # Reasoning should be truncated
            reasoning_line = [line for line in passed_content.split('\n') if 'Internal reasoning:' in line][0]
            reasoning_part = reasoning_line.split(':', 1)[1].strip()
            assert len(reasoning_part) <= 203
    
    @pytest.mark.asyncio
    async def test_selective_update_error_handling(self, memory_service, mock_agent, mock_context):
        """Test error handling in selective update."""
        with patch('core.services.memory_service.SelectiveMemoryManager.update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.side_effect = Exception("Memory update failed")
            
            with pytest.raises(Exception, match="Memory update failed"):
                await memory_service.update_memory_selective(
                    agent=mock_agent,
                    context=mock_context,
                    content="Test content"
                )
            
            # Verify warning was logged
            memory_service.logger.warning.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_selective_update_with_custom_config(self, memory_service, mock_agent, mock_context):
        """Test selective update with custom configuration."""
        custom_config = Mock()
        custom_config.memory_guidance_style = 'structured'
        
        with patch('core.services.memory_service.SelectiveMemoryManager.update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            await memory_service.update_memory_selective(
                agent=mock_agent,
                context=mock_context,
                content="Test content",
                config=custom_config
            )
            
            # Verify custom config was passed
            call_args = mock_update.call_args
            assert call_args[1]['config'] == custom_config


class TestMemoryServiceDiscussionUpdates:
    """Test discussion-specific memory update methods."""
    
    @pytest.fixture
    def memory_service(self):
        """Create MemoryService for testing."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        return MemoryService(language_manager, utility_agent, settings)
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock participant agent."""
        agent = Mock(spec=ParticipantAgent)
        agent.name = "TestAgent"
        return agent
    
    @pytest.fixture
    def mock_context(self):
        """Create mock participant context."""
        return ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=1000.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )
    
    @pytest.mark.asyncio
    async def test_update_discussion_memory_with_reasoning(self, memory_service, mock_agent, mock_context):
        """Test discussion memory update with internal reasoning."""
        with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            result = await memory_service.update_discussion_memory(
                agent=mock_agent,
                context=mock_context,
                statement="I prefer principle A",
                internal_reasoning="It seems most fair",
                round_num=2,
                include_internal_reasoning=True
            )
            
            assert result == "Updated memory"
            mock_update.assert_called_once()
            
            # Verify call arguments
            call_args = mock_update.call_args
            assert call_args[1]['agent'] == mock_agent
            assert call_args[1]['context'] == mock_context
            assert call_args[1]['event_type'] == MemoryEventType.DISCUSSION_STATEMENT
            
            # Check content formatting
            content = call_args[1]['content']
            assert "Round 2: Your statement: I prefer principle A" in content
            assert "Internal reasoning: It seems most fair" in content
            
            # Check metadata
            metadata = call_args[1]['event_metadata']
            assert metadata['round_number'] == 2
            assert metadata['participant_name'] == 'TestAgent'
            assert metadata['has_internal_reasoning'] is True
    
    @pytest.mark.asyncio
    async def test_update_discussion_memory_without_reasoning(self, memory_service, mock_agent, mock_context):
        """Test discussion memory update without internal reasoning."""
        with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            await memory_service.update_discussion_memory(
                agent=mock_agent,
                context=mock_context,
                statement="I prefer principle B",
                round_num=1,
                include_internal_reasoning=False
            )
            
            call_args = mock_update.call_args
            content = call_args[1]['content']
            
            assert "Round 1: Your statement: I prefer principle B" in content
            assert "Internal reasoning:" not in content
            
            metadata = call_args[1]['event_metadata']
            assert metadata['has_internal_reasoning'] is False


class TestMemoryServiceVotingUpdates:
    """Test voting-specific memory update methods."""
    
    @pytest.fixture
    def memory_service(self):
        """Create MemoryService with mocked language manager."""
        language_manager = Mock()
        language_manager.get.return_value = "Voting phase message"
        utility_agent = Mock()
        settings = Phase2Settings()
        logger = Mock()
        return MemoryService(language_manager, utility_agent, settings, logger=logger)
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock participant agent."""
        agent = Mock(spec=ParticipantAgent)
        agent.name = "TestAgent"
        return agent
    
    @pytest.fixture
    def mock_context(self):
        """Create mock participant context."""
        return ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=1000.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )
    
    @pytest.mark.asyncio
    async def test_update_voting_phase_memory_basic(self, memory_service, mock_agent, mock_context):
        """Test basic voting phase memory update."""
        with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            result = await memory_service.update_voting_phase_memory(
                agent=mock_agent,
                context=mock_context,
                phase_name="initiation"
            )
            
            assert result == "Updated memory"
            
            # Verify language manager call
            memory_service.language_manager.get.assert_called_with("voting_phases.initiation")
            
            # Verify selective update call
            call_args = mock_update.call_args
            assert call_args[1]['content'] == "Voting phase message"
            assert call_args[1]['event_type'] == MemoryEventType.PHASE_TRANSITION
            
            metadata = call_args[1]['event_metadata']
            assert metadata['phase_name'] == 'initiation'
            assert metadata['initiator_name'] is None
    
    @pytest.mark.asyncio
    async def test_update_voting_phase_memory_with_initiator(self, memory_service, mock_agent, mock_context):
        """Test voting phase memory update with initiator."""
        memory_service.language_manager.get.return_value = "Alice initiated voting"
        
        with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            await memory_service.update_voting_phase_memory(
                agent=mock_agent,
                context=mock_context,
                phase_name="initiation",
                initiator_name="Alice"
            )
            
            # Verify language manager called with initiator
            memory_service.language_manager.get.assert_called_with(
                "voting_phases.initiation_with_initiator", 
                initiator_name="Alice"
            )
            
            call_args = mock_update.call_args
            metadata = call_args[1]['event_metadata']
            assert metadata['initiator_name'] == 'Alice'
    
    @pytest.mark.asyncio
    async def test_update_voting_phase_memory_with_additional_info(self, memory_service, mock_agent, mock_context):
        """Test voting phase memory update with additional information."""
        with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            await memory_service.update_voting_phase_memory(
                agent=mock_agent,
                context=mock_context,
                phase_name="confirmation",
                additional_info="All participants agreed"
            )
            
            call_args = mock_update.call_args
            content = call_args[1]['content']
            assert content == "Voting phase message All participants agreed"
    
    @pytest.mark.asyncio
    async def test_update_all_memories_for_voting_phase(self, memory_service):
        """Test updating all participant memories for voting phase."""
        # Create mock participants and contexts
        participants = [Mock(name=f"Agent{i}") for i in range(3)]
        for i, p in enumerate(participants):
            p.name = f"Agent{i}"
        
        contexts = [
            ParticipantContext(
                name=f"Agent{i}",
                role_description="Test participant",
                bank_balance=1000.0,
                memory="Initial memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2
            )
            for i in range(3)
        ]
        
        with patch.object(memory_service, 'update_voting_phase_memory', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            await memory_service.update_all_memories_for_voting_phase(
                participants=participants,
                contexts=contexts,
                phase_name="confirmation",
                additional_info="Test info",
                initiator_name="Agent0"
            )
            
            # Verify called for each participant
            assert mock_update.call_count == 3
            
            # Verify all contexts were updated
            for context in contexts:
                assert context.memory == "Updated memory"
    
    @pytest.mark.asyncio 
    async def test_update_all_memories_handles_individual_failures(self, memory_service):
        """Test that update_all_memories continues even if individual updates fail."""
        participants = [Mock(name=f"Agent{i}") for i in range(3)]
        for i, p in enumerate(participants):
            p.name = f"Agent{i}"
        
        contexts = [
            ParticipantContext(
                name=f"Agent{i}",
                role_description="Test participant",
                bank_balance=1000.0,
                memory="Initial memory",
                round_number=1,
                phase=ExperimentPhase.PHASE_2
            )
            for i in range(3)
        ]
        
        with patch.object(memory_service, 'update_voting_phase_memory', new_callable=AsyncMock) as mock_update:
            # First call succeeds, second fails, third succeeds
            mock_update.side_effect = ["Success 1", Exception("Update failed"), "Success 3"]
            
            await memory_service.update_all_memories_for_voting_phase(
                participants=participants,
                contexts=contexts,
                phase_name="confirmation"
            )
            
            # Verify all calls were attempted
            assert mock_update.call_count == 3
            
            # Verify successful updates were applied
            assert contexts[0].memory == "Success 1"
            assert contexts[1].memory == "Initial memory"  # Failed, unchanged
            assert contexts[2].memory == "Success 3"
            
            # Verify warning was logged for failure
            assert memory_service.logger.warning.called


class TestMemoryServiceFinalResults:
    """Test final results memory update methods."""
    
    @pytest.fixture
    def memory_service(self):
        """Create MemoryService for testing."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        return MemoryService(language_manager, utility_agent, settings)
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock participant agent."""
        agent = Mock(spec=ParticipantAgent)
        agent.name = "TestAgent"
        return agent
    
    @pytest.fixture
    def mock_context(self):
        """Create mock participant context."""
        return ParticipantContext(
            name="TestAgent",
            role_description="Test participant",
            bank_balance=1000.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )
    
    @pytest.mark.asyncio
    async def test_update_final_results_memory(self, memory_service, mock_agent, mock_context):
        """Test final results memory update."""
        with patch.object(memory_service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory with results"
            
            result = await memory_service.update_final_results_memory(
                agent=mock_agent,
                context=mock_context,
                result_content="Consensus reached on principle A. Your earnings: $15,000",
                final_earnings=15000.0,
                consensus_reached=True
            )
            
            assert result == "Updated memory with results"
            
            call_args = mock_update.call_args
            assert call_args[1]['agent'] == mock_agent
            assert call_args[1]['context'] == mock_context
            assert call_args[1]['event_type'] == MemoryEventType.FINAL_RESULTS
            
            # Check content formatting
            content = call_args[1]['content']
            assert content == "Final Phase 2 Results: Consensus reached on principle A. Your earnings: $15,000"
            
            # Check metadata
            metadata = call_args[1]['event_metadata']
            assert metadata['final_earnings'] == 15000.0
            assert metadata['consensus_reached'] is True


class TestMemoryServiceConfigFallback:
    """Test configuration fallback functionality."""
    
    def test_create_config_fallback_with_settings(self):
        """Test creation of config fallback from settings."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        mock_config = Mock()
        mock_config.memory_guidance_style = 'structured'
        
        service = MemoryService(language_manager, utility_agent, settings, config=mock_config)
        config = service._create_config_fallback()
        
        # The fallback uses settings, not the original config
        assert config.memory_guidance_style == 'narrative'  # Default from settings
        assert config.selective_memory_updates is True      # Default
    
    def test_create_config_fallback_with_defaults(self):
        """Test creation of config fallback with default values."""
        language_manager = Mock()
        utility_agent = Mock()
        settings = Phase2Settings()
        
        service = MemoryService(language_manager, utility_agent, settings)
        config = service._create_config_fallback()
        
        assert config.memory_guidance_style == 'narrative'  # Default
        assert config.selective_memory_updates is True      # Default


if __name__ == '__main__':
    pytest.main([__file__])