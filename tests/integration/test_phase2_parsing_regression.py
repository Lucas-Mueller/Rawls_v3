"""
Phase 2 Parsing Regression Tests

Focused regression tests for the parser agent disambiguation issue.
These tests ensure that responses containing voting context still parse
correctly as principle choices/rankings instead of being misinterpreted
as vote proposals.

Critical for preventing regression of our parser agent fix.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, CertaintyLevel
from utils.language_manager import create_language_manager, SupportedLanguage


class TestParserDisambiguationRegression:
    """Regression tests for parser agent disambiguation."""
    
    @pytest.fixture(params=["english", "spanish", "mandarin"])
    def language_agent_pair(self, request):
        """Create utility agent for each language."""
        language = request.param
        lang_manager = create_language_manager(SupportedLanguage(language.title()))
        agent = UtilityAgent(
            utility_model="gpt-4o-mini",
            temperature=0.0,
            experiment_language=language,
            language_manager=lang_manager
        )
        return language, agent

    @pytest.mark.asyncio
    async def test_principle_choice_with_voting_context_all_languages(self, language_agent_pair):
        """Test principle choice parsing with voting context across all languages."""
        language, agent = language_agent_pair
        
        # Language-specific test responses with voting context
        test_responses = {
            "english": """
            After our discussion, I choose maximizing floor income. I'm very sure about this choice.
            The reasoning is that it provides the best protection for vulnerable populations.
            I think we should proceed with a formal vote now.
            """,
            "spanish": """
            Después de nuestra discusión, elijo maximizar los ingresos mínimos. Estoy muy seguro de esta elección.
            La razón es que proporciona la mejor protección para las poblaciones vulnerables.
            Creo que deberíamos proceder con una votación formal ahora.
            """,
            "mandarin": """
            经过我们的讨论，我选择最大化最低收入。我对这个选择很确定。
            理由是这为弱势群体提供了最好的保护。
            我认为我们现在应该进行正式投票。
            """
        }
        
        # Expected parsing results
        expected_results = {
            "english": {
                "principle": "maximizing_floor",
                "constraint_amount": None,
                "certainty": "very_sure",
                "reasoning": "Best protection for vulnerable populations"
            },
            "spanish": {
                "principle": "maximizing_floor", 
                "constraint_amount": None,
                "certainty": "very_sure",
                "reasoning": "Best protection for vulnerable populations"
            },
            "mandarin": {
                "principle": "maximizing_floor",
                "constraint_amount": None,
                "certainty": "sure", 
                "reasoning": "Best protection for vulnerable populations"
            }
        }
        
        response = test_responses[language]
        expected = expected_results[language]
        
        # Mock LLM response
        mock_result = MagicMock()
        mock_result.final_output = f"""
        {{
            "principle": "{expected['principle']}",
            "constraint_amount": {expected['constraint_amount']},
            "certainty": "{expected['certainty']}", 
            "reasoning": "{expected['reasoning']}"
        }}
        """
        
        with patch('experiment_agents.utility_agent.run_without_tracing', return_value=mock_result):
            await agent.async_init()
            choice = await agent.parse_principle_choice_enhanced(response)
            
            # Verify correct parsing despite voting context
            assert choice.principle == JusticePrinciple.MAXIMIZING_FLOOR
            assert choice.certainty in [CertaintyLevel.SURE, CertaintyLevel.VERY_SURE]
            assert choice.constraint_amount is None

    @pytest.mark.asyncio
    async def test_principle_ranking_with_voting_context_all_languages(self, language_agent_pair):
        """Test principle ranking parsing with voting context across all languages."""
        language, agent = language_agent_pair
        
        # Language-specific ranking responses with voting context
        test_responses = {
            "english": """
            After extensive discussion, here's my final ranking:
            1. Maximizing floor income
            2. Maximizing average with floor constraint  
            3. Maximizing average income
            4. Maximizing average with range constraint
            
            Overall certainty: very sure
            
            I believe we're ready to vote on this now.
            """,
            "spanish": """
            Después de una discusión extensa, aquí está mi ranking final:
            1. Maximizar los ingresos mínimos
            2. Maximizar los ingresos promedio con restricción de ingreso mínimo
            3. Maximizar los ingresos promedio
            4. Maximizar los ingresos promedio con restricción de rango
            
            Certeza general: muy seguro
            
            Creo que estamos listos para votar sobre esto ahora.
            """,
            "mandarin": """
            经过广泛讨论，这是我的最终排序：
            1. 最大化最低收入
            2. 在最低收入约束条件下最大化平均收入
            3. 最大化平均收入
            4. 在范围约束条件下最大化平均收入
            
            总体确定性：很确定
            
            我认为我们现在准备投票了。
            """
        }
        
        response = test_responses[language]
        
        # Mock LLM response with proper ranking JSON
        mock_result = MagicMock()
        mock_result.final_output = """
        {
            "rankings": [
                {"principle": "maximizing_floor", "rank": 1},
                {"principle": "maximizing_average_floor_constraint", "rank": 2},
                {"principle": "maximizing_average", "rank": 3},
                {"principle": "maximizing_average_range_constraint", "rank": 4}
            ],
            "certainty": "very_sure"
        }
        """
        
        with patch('experiment_agents.utility_agent.run_without_tracing', return_value=mock_result):
            await agent.async_init()
            ranking = await agent.parse_principle_ranking_enhanced(response)
            
            # Verify correct ranking parsing despite voting context
            assert len(ranking.rankings) == 4
            assert ranking.rankings[0].principle == JusticePrinciple.MAXIMIZING_FLOOR
            assert ranking.rankings[0].rank == 1
            assert ranking.certainty == CertaintyLevel.VERY_SURE

    @pytest.mark.asyncio
    async def test_constraint_principle_with_voting_context(self, language_agent_pair):
        """Test constraint principle parsing with voting context."""
        language, agent = language_agent_pair
        
        # Test responses with constraint principles and voting context
        test_responses = {
            "english": """
            I choose maximizing average with floor constraint at $15,000. Very sure about this.
            This balances efficiency with fairness effectively.
            Let's proceed with voting on this principle.
            """,
            "spanish": """
            Elijo maximizar los ingresos promedio con restricción de ingreso mínimo de $15,000. Muy seguro de esto.
            Esto equilibra la eficiencia con la equidad de manera efectiva.
            Procedamos con la votación sobre este principio.
            """,
            "mandarin": """
            我选择在最低收入约束条件下最大化平均收入，约束为15000美元。对此很确定。
            这有效地平衡了效率和公平。
            让我们就这个原则进行投票。
            """
        }
        
        response = test_responses[language]
        
        # Mock LLM response with constraint principle
        mock_result = MagicMock()
        mock_result.final_output = """
        {
            "principle": "maximizing_average_floor_constraint",
            "constraint_amount": 15000,
            "certainty": "very_sure",
            "reasoning": "Balances efficiency with fairness"
        }
        """
        
        with patch('experiment_agents.utility_agent.run_without_tracing', return_value=mock_result):
            await agent.async_init()
            choice = await agent.parse_principle_choice_enhanced(response)
            
            # Verify constraint principle parsing despite voting context
            assert choice.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            assert choice.constraint_amount == 15000
            assert choice.certainty == CertaintyLevel.VERY_SURE

    @pytest.mark.asyncio
    async def test_no_false_vote_proposal_responses(self, language_agent_pair):
        """Test that parser doesn't return VOTE_PROPOSAL when parsing principles."""
        language, agent = language_agent_pair
        
        # Response that might confuse old parser due to heavy voting context
        response_heavy_voting_context = {
            "english": """
            Before we vote, let me state my choice clearly. I vote for maximizing floor income.
            I think voting is the right approach here. Let's vote on this principle.
            My vote is for the floor principle. Time to vote!
            """,
            "spanish": """
            Antes de votar, permíteme declarar mi elección claramente. Voto por maximizar los ingresos mínimos.
            Creo que votar es el enfoque correcto aquí. Votemos por este principio.
            Mi voto es por el principio de piso. ¡Es hora de votar!
            """,
            "mandarin": """
            在我们投票之前，让我清楚地说明我的选择。我投票选择最大化最低收入。
            我认为投票是正确的方法。让我们就这个原则投票。
            我的投票是支持底线原则。是时候投票了！
            """
        }
        
        response = response_heavy_voting_context[language]
        
        # Mock proper principle choice response (not VOTE_PROPOSAL)
        mock_result = MagicMock()
        mock_result.final_output = """
        {
            "principle": "maximizing_floor",
            "constraint_amount": null,
            "certainty": "sure",
            "reasoning": "Clear choice for floor principle"
        }
        """
        
        with patch('experiment_agents.utility_agent.run_without_tracing', return_value=mock_result):
            await agent.async_init()
            
            # This should NOT raise an exception about VOTE_PROPOSAL format
            choice = await agent.parse_principle_choice_enhanced(response)
            
            # Should successfully parse as principle choice
            assert choice.principle == JusticePrinciple.MAXIMIZING_FLOOR
            assert choice.certainty == CertaintyLevel.SURE

    @pytest.mark.asyncio
    async def test_legacy_vote_proposal_format_still_handled(self):
        """Test that legacy VOTE_PROPOSAL format is still handled in fallback."""
        # This test ensures our fix doesn't break any existing functionality
        # that might still rely on VOTE_PROPOSAL format detection
        
        agent = UtilityAgent(
            utility_model="gpt-4o-mini", 
            temperature=0.0,
            experiment_language="mandarin",
            language_manager=create_language_manager(SupportedLanguage.MANDARIN)
        )
        
        # Legacy format that might still appear in some contexts
        legacy_response = "VOTE_PROPOSAL:[在最低收入约束条件下最大化平均收入, 平均收入最大化, 在范围约束条件下最大化平均收入, 最大化最低收入]"
        
        # Should be handled by fallback extraction
        await agent.async_init()
        
        # This should use our fallback extraction logic for VOTE_PROPOSAL format
        result = agent._fallback_extract_ranking(legacy_response)
        
        # Should successfully extract from legacy format
        assert result is not None
        assert len(result['rankings']) == 4
        assert result['rankings'][0]['principle'] == 'maximizing_average_floor_constraint'
        assert result['rankings'][1]['principle'] == 'maximizing_average' 
        assert result['rankings'][2]['principle'] == 'maximizing_average_range_constraint'
        assert result['rankings'][3]['principle'] == 'maximizing_floor'


if __name__ == '__main__':
    pytest.main([__file__])