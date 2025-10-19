"""
Golden tests for MemoryService consistency.

These tests create snapshots of memory formatting and content across different 
scenarios to detect unintentional changes during refactoring. They help ensure 
that MemoryService produces identical memory updates to the original 
SelectiveMemoryManager calls in Phase2Manager.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from core.services.memory_service import MemoryService, MemoryEventType
from config.phase2_settings import Phase2Settings
from models.experiment_types import ParticipantContext, ExperimentPhase
from experiment_agents.participant_agent import ParticipantAgent
from utils.language_manager import SupportedLanguage, create_language_manager


class TestMemoryServiceFormatConsistency:
    """Golden tests for memory format consistency across languages and scenarios."""
    
    def setup_method(self):
        """Set up test fixtures with real language managers."""
        self.english_language_manager = create_language_manager(SupportedLanguage.ENGLISH)
        self.spanish_language_manager = create_language_manager(SupportedLanguage.SPANISH)
        self.chinese_language_manager = create_language_manager(SupportedLanguage.MANDARIN)
    
    def create_memory_service(self, language_manager):
        """Create a MemoryService with given language manager."""
        utility_agent = Mock()
        settings = Phase2Settings()
        return MemoryService(language_manager, utility_agent, settings)
    
    def create_test_context(self, name: str = "TestAgent", memory: str = "Initial memory") -> ParticipantContext:
        """Create a test participant context."""
        return ParticipantContext(
            name=name,
            role_description="Test participant for golden tests",
            bank_balance=1000.0,
            memory=memory,
            round_number=1,
            phase=ExperimentPhase.PHASE_2,
            memory_character_limit=50000
        )
    
    def create_test_agent(self, name: str = "TestAgent") -> Mock:
        """Create a mock test agent."""
        agent = Mock(spec=ParticipantAgent)
        agent.name = name
        return agent
    
    def test_english_discussion_memory_format_golden(self):
        """Golden test for English discussion memory formatting."""
        service = self.create_memory_service(self.english_language_manager)
        
        # Test truncation behavior for long statements
        long_statement = "I believe we should adopt the principle of maximizing floor income because it provides the greatest protection for the most vulnerable members of our society. This approach ensures that everyone has a basic standard of living that allows them to participate meaningfully in economic and social life."
        
        truncated_result = service.apply_content_truncation(
            f"Round 3: Your statement: {long_statement}\nInternal reasoning: This seems most equitable given our group composition.",
            MemoryEventType.DISCUSSION_STATEMENT
        )
        
        # Verify statement truncation
        lines = truncated_result.split('\n')
        statement_line = next(line for line in lines if 'Your statement:' in line)
        statement_part = statement_line.split('statement:', 1)[1].strip()
        
        # The statement is exactly 299 characters, so it should not be truncated
        expected_statement = "I believe we should adopt the principle of maximizing floor income because it provides the greatest protection for the most vulnerable members of our society. This approach ensures that everyone has a basic standard of living that allows them to participate meaningfully in economic and social life."
        
        assert statement_part == expected_statement
        assert len(statement_part) == 299  # Verify exact length
        assert not statement_part.endswith('...')  # No truncation
        assert "Internal reasoning: This seems most equitable given our group composition." in truncated_result
    
    def test_spanish_discussion_memory_format_golden(self):
        """Golden test for Spanish discussion memory formatting.""" 
        service = self.create_memory_service(self.spanish_language_manager)
        
        # Test with Spanish content
        spanish_statement = "Creo que deberíamos adoptar el principio de maximizar los ingresos mínimos porque proporciona la mayor protección para los miembros más vulnerables de nuestra sociedad. Este enfoque asegura que todos tengan un nivel básico de vida que les permita participar significativamente en la vida económica y social."
        
        truncated_result = service.apply_content_truncation(
            f"Round 2: Your statement: {spanish_statement}\nInternal reasoning: Esto parece más equitativo.",
            MemoryEventType.DISCUSSION_STATEMENT
        )
        
        lines = truncated_result.split('\n')
        statement_line = next(line for line in lines if 'Your statement:' in line)
        statement_part = statement_line.split('statement:', 1)[1].strip()
        
        # Spanish text should remain intact
        assert statement_part == spanish_statement
        assert not statement_part.endswith('...')
        assert "Internal reasoning: Esto parece más equitativo." in truncated_result
    
    def test_chinese_discussion_memory_format_golden(self):
        """Golden test for Chinese discussion memory formatting."""
        service = self.create_memory_service(self.chinese_language_manager)
        
        # Test with Chinese content
        chinese_statement = "我认为我们应该采用最大化最低收入的原则，因为它为我们社会中最脆弱的成员提供了最大的保护。这种方法确保每个人都有基本的生活标准，使他们能够有意义地参与经济和社会生活。我相信这是最公正的选择，特别是考虑到我们群体的组成。"
        
        truncated_result = service.apply_content_truncation(
            f"Round 1: Your statement: {chinese_statement}\nInternal reasoning: 这似乎最公平。",
            MemoryEventType.DISCUSSION_STATEMENT
        )
        
        lines = truncated_result.split('\n')
        statement_line = next(line for line in lines if 'Your statement:' in line)
        statement_part = statement_line.split('statement:', 1)[1].strip()
        
        # Chinese text should remain intact
        assert statement_part == chinese_statement
        assert not statement_part.endswith('...')
        assert "Internal reasoning: 这似乎最公平。" in truncated_result
    
    @pytest.mark.asyncio
    async def test_english_voting_phase_memory_format_golden(self):
        """Golden test for English voting phase memory formatting."""
        service = self.create_memory_service(self.english_language_manager)
        agent = self.create_test_agent("Alice")
        context = self.create_test_context("Alice")
        
        with patch.object(service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated memory"
            
            # Test voting initiation without initiator
            await service.update_voting_phase_memory(
                agent=agent,
                context=context, 
                phase_name="initiation"
            )
            
            call_args = mock_update.call_args
            expected_content = self.english_language_manager.get("voting_phases.initiation")
            
            assert call_args[1]['content'] == expected_content
            assert call_args[1]['event_type'] == MemoryEventType.PHASE_TRANSITION
            
            metadata = call_args[1]['event_metadata']
            assert metadata['phase_name'] == 'initiation'
            assert metadata['initiator_name'] is None
    
    @pytest.mark.asyncio
    async def test_spanish_voting_phase_with_initiator_golden(self):
        """Golden test for Spanish voting phase with initiator."""
        service = self.create_memory_service(self.spanish_language_manager)
        agent = self.create_test_agent("Carlos")
        context = self.create_test_context("Carlos")

        with patch.object(service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Memoria actualizada"
            
            # Test voting confirmation with initiator
            await service.update_voting_phase_memory(
                agent=agent,
                context=context,
                phase_name="confirmation",
                initiator_name="María"
            )
            
            call_args = mock_update.call_args
            expected_content = self.spanish_language_manager.get("voting_phases.confirmation")
            
            assert call_args[1]['content'] == expected_content
            
            metadata = call_args[1]['event_metadata']
            assert metadata['phase_name'] == 'confirmation'
            assert metadata['initiator_name'] == 'María'
    
    @pytest.mark.asyncio
    async def test_chinese_voting_phase_with_additional_info_golden(self):
        """Golden test for Chinese voting phase with additional information."""
        service = self.create_memory_service(self.chinese_language_manager)
        agent = self.create_test_agent("张伟")
        context = self.create_test_context("张伟")

        with patch.object(service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "更新的记忆"
            
            # Test secret ballot with additional info
            additional_info = "所有参与者都已确认参与。"
            await service.update_voting_phase_memory(
                agent=agent,
                context=context,
                phase_name="secret_ballot",
                additional_info=additional_info
            )
            
            call_args = mock_update.call_args
            expected_content = (
                f"{self.chinese_language_manager.get('voting_phases.secret_ballot')} {additional_info}"
            )
            
            assert call_args[1]['content'] == expected_content
    
    @pytest.mark.asyncio
    async def test_final_results_memory_format_golden(self):
        """Golden test for final results memory formatting."""
        service = self.create_memory_service(self.english_language_manager)
        agent = self.create_test_agent("Bob")
        context = self.create_test_context("Bob")

        with patch.object(service, 'update_memory_selective', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = "Updated with final results"
            
            # Test final results formatting
            await service.update_final_results_memory(
                agent=agent,
                context=context,
                result_content="Consensus reached on Maximizing Floor Income. Your final earnings: $15,500. You were assigned to Middle income class.",
                final_earnings=15500.0,
                consensus_reached=True
            )
            
            call_args = mock_update.call_args
            expected_content = self.english_language_manager.get(
                "memory.final_results_format",
                result_content="Consensus reached on Maximizing Floor Income. Your final earnings: $15,500. You were assigned to Middle income class.",
            )
            
            assert call_args[1]['content'] == expected_content
            assert call_args[1]['event_type'] == MemoryEventType.FINAL_RESULTS
            
            metadata = call_args[1]['event_metadata']
            assert metadata['final_earnings'] == 15500.0
            assert metadata['consensus_reached'] is True
    
    def test_truncation_boundary_conditions_golden(self):
        """Ensure memory truncation helper preserves content boundaries."""
        service = self.create_memory_service(self.english_language_manager)
        
        # Test exact 300-character statement (should not be truncated)
        exact_300_char_statement = "A" * 300
        content_300 = f"Round 1: Your statement: {exact_300_char_statement}\nInternal reasoning: Short"
        
        result_300 = service.apply_content_truncation(content_300, MemoryEventType.DISCUSSION_STATEMENT)
        statement_line = next(line for line in result_300.split('\n') if 'Your statement:' in line)
        statement_part = statement_line.split('statement:', 1)[1].strip()
        
        assert len(statement_part) == 300  # Exact match, no truncation
        assert not statement_part.endswith('...')
        
        # Test 301-character statement (should remain intact)
        over_300_char_statement = "A" * 301
        content_301 = f"Round 1: Your statement: {over_300_char_statement}\nInternal reasoning: Short"
        
        result_301 = service.apply_content_truncation(content_301, MemoryEventType.DISCUSSION_STATEMENT)
        statement_line = next(line for line in result_301.split('\n') if 'Your statement:' in line)
        statement_part = statement_line.split('statement:', 1)[1].strip()
        
        assert statement_part == over_300_char_statement
        assert not statement_part.endswith('...')
        
        # Test exact 200-character reasoning (should not be truncated)  
        exact_200_char_reasoning = "B" * 200
        content_reasoning_200 = f"Round 1: Your statement: Short\nInternal reasoning: {exact_200_char_reasoning}"
        
        result_reasoning_200 = service.apply_content_truncation(content_reasoning_200, MemoryEventType.DISCUSSION_STATEMENT)
        reasoning_line = next(line for line in result_reasoning_200.split('\n') if 'Internal reasoning:' in line)
        reasoning_part = reasoning_line.split(':', 1)[1].strip()
        
        assert len(reasoning_part) == 200  # Exact match, no truncation
        assert not reasoning_part.endswith('...')
        
        # Test 201-character reasoning (should remain intact)
        over_200_char_reasoning = "B" * 201  
        content_reasoning_201 = f"Round 1: Your statement: Short\nInternal reasoning: {over_200_char_reasoning}"
        
        result_reasoning_201 = service.apply_content_truncation(content_reasoning_201, MemoryEventType.DISCUSSION_STATEMENT)
        reasoning_line = next(line for line in result_reasoning_201.split('\n') if 'Internal reasoning:' in line)
        reasoning_part = reasoning_line.split(':', 1)[1].strip()
        
        assert reasoning_part == over_200_char_reasoning
        assert not reasoning_part.endswith('...')
    
    def test_memory_content_preservation_across_languages_golden(self):
        """Golden test for memory content preservation across different languages."""
        # Test that memory structure is preserved regardless of language
        
        test_scenarios = [
            (self.english_language_manager, "English discussion content", "English reasoning"),
            (self.spanish_language_manager, "Contenido de discusión en español", "Razonamiento en español"),
            (self.chinese_language_manager, "中文讨论内容", "中文推理")
        ]
        
        for language_manager, statement, reasoning in test_scenarios:
            service = self.create_memory_service(language_manager)
            
            content = f"Round 2: Your statement: {statement}\nInternal reasoning: {reasoning}"
            result = service.apply_content_truncation(content, MemoryEventType.DISCUSSION_STATEMENT)
            
            # Verify structure is preserved
            lines = result.split('\n')
            assert len(lines) == 2
            assert lines[0].startswith('Round 2: Your statement:')
            assert lines[1].startswith('Internal reasoning:')
            
            # Verify content is preserved (no truncation for short content)
            assert statement in lines[0]
            assert reasoning in lines[1]
    
    def test_non_discussion_content_preservation_golden(self):
        """Golden test for non-discussion content preservation."""
        service = self.create_memory_service(self.english_language_manager)
        
        # Test various event types that should not be truncated
        test_cases = [
            (MemoryEventType.FINAL_RESULTS, "Very long final results content " * 50),
            (MemoryEventType.PHASE_TRANSITION, "Very long phase transition content " * 50), 
            (MemoryEventType.VOTE_INITIATION_RESPONSE, "Very long vote response " * 50),
            (MemoryEventType.VOTING_CONFIRMATION, "Very long confirmation content " * 50),
            (None, "Very long unknown content type " * 50)  # No event type
        ]
        
        for event_type, long_content in test_cases:
            result = service.apply_content_truncation(long_content, event_type)
            assert result == long_content  # Should be unchanged
            assert len(result) > 300  # Verify it's actually long content


class TestMemoryServiceContractConsistency:
    """Test contract consistency with original SelectiveMemoryManager behavior."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = create_language_manager(SupportedLanguage.ENGLISH)
        self.utility_agent = Mock()
        self.settings = Phase2Settings()
        self.service = MemoryService(self.language_manager, self.utility_agent, self.settings)
    
    def create_test_agent(self, name: str = "TestAgent") -> Mock:
        """Create a mock test agent."""
        agent = Mock(spec=ParticipantAgent)
        agent.name = name
        return agent
    
    def create_test_context(self, name: str = "TestAgent") -> ParticipantContext:
        """Create a test participant context."""
        return ParticipantContext(
            name=name,
            role_description="Test participant",
            bank_balance=1000.0,
            memory="Initial memory",
            round_number=1,
            phase=ExperimentPhase.PHASE_2
        )
    
    @pytest.mark.asyncio
    @patch('core.services.memory_service.SelectiveMemoryManager.update_memory_selective', new_callable=AsyncMock)
    async def test_selective_update_parameter_contract(self, mock_selective_update):
        """Test that selective update calls maintain parameter contract."""
        mock_selective_update.return_value = "Updated memory"
        
        agent = self.create_test_agent()
        context = self.create_test_context()
        
        # Call with all parameters
        await self.service.update_memory_selective(
            agent=agent,
            context=context,
            content="Test content",
            event_type=MemoryEventType.DISCUSSION_STATEMENT,
            event_metadata={'test': 'metadata'},
            config=Mock(),
            error_handler=Mock(),
            custom_kwarg="custom_value"
        )
        
        # Verify all parameters were passed through correctly
        mock_selective_update.assert_called_once()
        call_kwargs = mock_selective_update.call_args[1]
        
        assert call_kwargs['agent'] == agent
        assert call_kwargs['context'] == context
        assert call_kwargs['event_type'] == MemoryEventType.DISCUSSION_STATEMENT
        assert call_kwargs['event_metadata'] == {'test': 'metadata'}
        assert call_kwargs['language_manager'] == self.language_manager
        assert call_kwargs['utility_agent'] == self.utility_agent
        assert call_kwargs['memory_guidance_style'] == 'structured'
        assert call_kwargs['custom_kwarg'] == 'custom_value'
    
    @pytest.mark.asyncio
    @patch('core.services.memory_service.SelectiveMemoryManager.update_memory_selective', new_callable=AsyncMock)
    async def test_discussion_memory_update_contract(self, mock_selective_update):
        """Test discussion memory update maintains expected contract."""
        mock_selective_update.return_value = "Updated discussion memory"
        
        agent = self.create_test_agent("Alice")
        context = self.create_test_context("Alice")
        
        result = await self.service.update_discussion_memory(
            agent=agent,
            context=context,
            statement="I prefer principle A",
            internal_reasoning="It seems fair",
            round_num=3,
            include_internal_reasoning=True
        )
        
        assert result.startswith("Updated discussion memory")
        assert result.strip().endswith(self.language_manager.get("memory.memory_end_marker"))
        
        call_kwargs = mock_selective_update.call_args[1]
        assert call_kwargs['event_type'] == MemoryEventType.DISCUSSION_STATEMENT
        
        # Verify content format
        content = call_kwargs['content']
        assert "Round 3: Your statement: I prefer principle A" in content
        assert "Internal reasoning: It seems fair" in content
        
        # Verify metadata
        metadata = call_kwargs['event_metadata']
        assert metadata['round_number'] == 3
        assert metadata['participant_name'] == 'Alice'
        assert metadata['has_internal_reasoning'] is True


if __name__ == '__main__':
    pytest.main([__file__])
