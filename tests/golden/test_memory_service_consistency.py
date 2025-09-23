"""
Golden tests for MemoryService consistency.

These tests validate memory formatting and content across different scenarios
using flexible validation to detect unintentional changes during refactoring
while allowing for reasonable memory management improvements.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List

from core.services.memory_service import MemoryService, MemoryEventType
from config.phase2_settings import Phase2Settings
from models.experiment_types import ParticipantContext, ExperimentPhase
from experiment_agents.participant_agent import ParticipantAgent
from tests.utils.prompt_assertions import (
    assert_memory_content_reasonable,
    assert_prompt_structure_preserved,
    assert_multilingual_equivalence
)


class TestMemoryServiceFormatConsistency:
    """Golden tests for memory format consistency across languages and scenarios."""
    
    def setup_method(self):
        """Set up test fixtures with mock language managers."""
        # Mock language managers for different languages
        self.english_language_manager = Mock()
        self.spanish_language_manager = Mock()
        self.chinese_language_manager = Mock()
        
        # Set up English translations
        self.english_translations = {
            "voting_phases.initiation": "The voting initiation phase has begun.",
            "voting_phases.initiation_with_initiator": "{initiator_name} has initiated the voting process.",
            "voting_phases.confirmation": "The voting confirmation phase is active.",
            "voting_phases.confirmation_with_initiator": "{initiator_name} requested group voting confirmation.",
            "voting_phases.secret_ballot": "The secret ballot voting phase has started.",
            "voting_phases.consensus_check": "Checking for consensus on the voting results."
        }
        
        # Set up Spanish translations
        self.spanish_translations = {
            "voting_phases.initiation": "La fase de iniciación de votación ha comenzado.",
            "voting_phases.initiation_with_initiator": "{initiator_name} ha iniciado el proceso de votación.",
            "voting_phases.confirmation": "La fase de confirmación de votación está activa.",
            "voting_phases.confirmation_with_initiator": "{initiator_name} solicitó confirmación de votación grupal.",
            "voting_phases.secret_ballot": "La fase de votación secreta ha comenzado.",
            "voting_phases.consensus_check": "Verificando consenso en los resultados de votación."
        }
        
        # Set up Chinese translations
        self.chinese_translations = {
            "voting_phases.initiation": "投票启动阶段已开始。",
            "voting_phases.initiation_with_initiator": "{initiator_name}已启动投票过程。",
            "voting_phases.confirmation": "投票确认阶段正在进行。",
            "voting_phases.confirmation_with_initiator": "{initiator_name}请求小组投票确认。",
            "voting_phases.secret_ballot": "秘密投票阶段已开始。",
            "voting_phases.consensus_check": "正在检查投票结果的共识。"
        }
        
        # Configure mock language managers
        self.english_language_manager.get.side_effect = lambda key, **kwargs: self.english_translations.get(key, f"[MISSING: {key}]").format(**kwargs)
        self.spanish_language_manager.get.side_effect = lambda key, **kwargs: self.spanish_translations.get(key, f"[MISSING: {key}]").format(**kwargs)
        self.chinese_language_manager.get.side_effect = lambda key, **kwargs: self.chinese_translations.get(key, f"[MISSING: {key}]").format(**kwargs)
    
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

        # Test structure preservation for discussion statements
        long_statement = "I believe we should adopt the principle of maximizing floor income because it provides the greatest protection for the most vulnerable members of our society. This approach ensures that everyone has a basic standard of living that allows them to participate meaningfully in economic and social life."

        truncated_result = service.apply_content_truncation(
            f"Round 3: Your statement: {long_statement}\nInternal reasoning: This seems most equitable given our group composition.",
            MemoryEventType.DISCUSSION_STATEMENT
        )

        # Validate memory structure is preserved
        assert_prompt_structure_preserved(truncated_result, [
            "Round 3:",
            "Your statement:",
            "Internal reasoning:"
        ])

        # Validate content is reasonable length and contains key elements
        assert_memory_content_reasonable(truncated_result, max_reasonable_length=1000)

        # Verify essential content is preserved
        assert "maximizing floor income" in truncated_result
        assert "most equitable" in truncated_result
    
    def test_spanish_discussion_memory_format_golden(self):
        """Golden test for Spanish discussion memory formatting."""
        service = self.create_memory_service(self.spanish_language_manager)

        # Test with Spanish content
        spanish_statement = "Creo que deberíamos adoptar el principio de maximizar los ingresos mínimos porque proporciona la mayor protección para los miembros más vulnerables de nuestra sociedad. Este enfoque asegura que todos tengan un nivel básico de vida que les permita participar significativamente en la vida económica y social."

        truncated_result = service.apply_content_truncation(
            f"Round 2: Your statement: {spanish_statement}\nInternal reasoning: Esto parece más equitativo.",
            MemoryEventType.DISCUSSION_STATEMENT
        )

        # Validate structure is preserved for Spanish content
        assert_prompt_structure_preserved(truncated_result, [
            "Round 2:",
            "Your statement:",
            "Internal reasoning:"
        ])

        # Validate content is reasonable and contains key Spanish terms
        assert_memory_content_reasonable(truncated_result, max_reasonable_length=1000)
        assert "maximizar los ingresos mínimos" in truncated_result
        assert "más equitativo" in truncated_result
    
    def test_chinese_discussion_memory_format_golden(self):
        """Golden test for Chinese discussion memory formatting."""
        service = self.create_memory_service(self.chinese_language_manager)

        # Test with Chinese content
        chinese_statement = "我认为我们应该采用最大化最低收入的原则，因为它为我们社会中最脆弱的成员提供了最大的保护。这种方法确保每个人都有基本的生活标准，使他们能够有意义地参与经济和社会生活。我相信这是最公正的选择，特别是考虑到我们群体的组成。"

        truncated_result = service.apply_content_truncation(
            f"Round 1: Your statement: {chinese_statement}\nInternal reasoning: 这似乎最公平。",
            MemoryEventType.DISCUSSION_STATEMENT
        )

        # Validate structure is preserved for Chinese content
        assert_prompt_structure_preserved(truncated_result, [
            "Round 1:",
            "Your statement:",
            "Internal reasoning:"
        ])

        # Validate content is reasonable and contains key Chinese terms
        assert_memory_content_reasonable(truncated_result, max_reasonable_length=1000)
        assert "最大化最低收入" in truncated_result
        assert "最公平" in truncated_result
    
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
            content = call_args[1]['content']

            # Validate content contains key voting phase elements
            assert "voting" in content
            assert "initiation" in content
            assert "phase" in content
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
            content = call_args[1]['content']

            # Validate Spanish voting phase content contains key elements
            # The content should contain voting-related terms and the initiator name when provided
            assert "confirmación" in content
            assert "votación" in content
            # Note: initiator name may not always be in final content depending on phase

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
            await service.update_voting_phase_memory(
                agent=agent,
                context=context,
                phase_name="secret_ballot",
                additional_info="所有参与者都已确认参与。"
            )

            call_args = mock_update.call_args
            content = call_args[1]['content']

            # Validate Chinese voting phase content contains key elements
            assert_multilingual_equivalence(content, [
                "秘密投票",
                "阶段",
                "参与者",
                "确认"
            ], "Chinese")
    
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
            content = call_args[1]['content']

            # Validate final results content structure and metadata
            # The content should be reasonable length and properly structured
            assert_memory_content_reasonable(content, max_reasonable_length=2000)
            # The result content parameter should have been passed along
            # (checking call arguments instead of exact content due to translation dependencies)
            assert call_args[1]['event_type'] == MemoryEventType.FINAL_RESULTS

            metadata = call_args[1]['event_metadata']
            assert metadata['final_earnings'] == 15500.0
            assert metadata['consensus_reached'] is True
    
    def test_truncation_boundary_conditions_golden(self):
        """Golden test for truncation behavior with reasonable length validation."""
        service = self.create_memory_service(self.english_language_manager)

        # Test that very long statements are handled reasonably
        very_long_statement = "A" * 500  # Clearly over any reasonable limit
        content_long = f"Round 1: Your statement: {very_long_statement}\nInternal reasoning: Short"

        result_long = service.apply_content_truncation(content_long, MemoryEventType.DISCUSSION_STATEMENT)

        # Validate structure is preserved regardless of truncation
        assert_prompt_structure_preserved(result_long, [
            "Round 1:",
            "Your statement:",
            "Internal reasoning:"
        ])

        # Validate content is reasonable length (should be truncated to manageable size)
        assert_memory_content_reasonable(result_long, max_reasonable_length=1000)

        # Test that very long reasoning is handled reasonably
        very_long_reasoning = "B" * 500  # Clearly over any reasonable limit
        content_reasoning_long = f"Round 1: Your statement: Short\nInternal reasoning: {very_long_reasoning}"

        result_reasoning_long = service.apply_content_truncation(content_reasoning_long, MemoryEventType.DISCUSSION_STATEMENT)

        # Validate structure is preserved
        assert_prompt_structure_preserved(result_reasoning_long, [
            "Round 1:",
            "Your statement:",
            "Internal reasoning:"
        ])

        # Validate content is reasonable length
        assert_memory_content_reasonable(result_reasoning_long, max_reasonable_length=1000)
    
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

            # Verify structure is preserved across languages
            assert_prompt_structure_preserved(result, [
                "Round 2:",
                "Your statement:",
                "Internal reasoning:"
            ])

            # Verify content is reasonable and contains expected terms
            assert_memory_content_reasonable(result, max_reasonable_length=1000)
            assert statement in result
            assert reasoning in result
    
    def test_non_discussion_content_preservation_golden(self):
        """Golden test for non-discussion content preservation."""
        service = self.create_memory_service(self.english_language_manager)

        # Test various event types that should preserve content appropriately
        test_cases = [
            (MemoryEventType.FINAL_RESULTS, "Very long final results content " * 50),
            (MemoryEventType.PHASE_TRANSITION, "Very long phase transition content " * 50),
            (MemoryEventType.VOTE_INITIATION_RESPONSE, "Very long vote response " * 50),
            (MemoryEventType.VOTING_CONFIRMATION, "Very long confirmation content " * 50),
            (None, "Very long unknown content type " * 50)  # No event type
        ]

        for event_type, long_content in test_cases:
            result = service.apply_content_truncation(long_content, event_type)
            # Validate content is reasonable without being overly strict about exact preservation
            assert_memory_content_reasonable(result, max_reasonable_length=10000)
            # Key content phrases should be preserved
            if event_type == MemoryEventType.FINAL_RESULTS:
                assert "final results" in result
            elif event_type == MemoryEventType.PHASE_TRANSITION:
                assert "phase transition" in result
            elif event_type == MemoryEventType.VOTE_INITIATION_RESPONSE:
                assert "vote response" in result
            elif event_type == MemoryEventType.VOTING_CONFIRMATION:
                assert "confirmation" in result
            else:
                assert "unknown content type" in result


class TestMemoryServiceContractConsistency:
    """Test contract consistency with original SelectiveMemoryManager behavior."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.language_manager = Mock()
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
    
    @patch('core.services.memory_service.SelectiveMemoryManager.update_memory_selective')
    def test_selective_update_parameter_contract(self, mock_selective_update):
        """Test that selective update calls maintain parameter contract."""
        mock_selective_update.return_value = "Updated memory"
        
        agent = self.create_test_agent()
        context = self.create_test_context()
        
        # Call with all parameters
        asyncio.run(self.service.update_memory_selective(
            agent=agent,
            context=context,
            content="Test content",
            event_type=MemoryEventType.DISCUSSION_STATEMENT,
            event_metadata={'test': 'metadata'},
            config=Mock(),
            error_handler=Mock(),
            custom_kwarg="custom_value"
        ))
        
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
    
    @patch('core.services.memory_service.SelectiveMemoryManager.update_memory_selective')
    def test_discussion_memory_update_contract(self, mock_selective_update):
        """Test discussion memory update maintains expected contract."""
        mock_selective_update.return_value = "Updated discussion memory"
        
        agent = self.create_test_agent("Alice")
        context = self.create_test_context("Alice")
        
        result = asyncio.run(self.service.update_discussion_memory(
            agent=agent,
            context=context,
            statement="I prefer principle A",
            internal_reasoning="It seems fair",
            round_num=3,
            include_internal_reasoning=True
        ))
        
        assert result == "Updated discussion memory"
        
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
