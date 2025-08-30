"""
Test to reproduce the Gemini model parsing failure observed in stupid_max.yaml config.

This test specifically targets the parse_principle_ranking_enhanced method failure
when using google/gemini-2.5-flash-lite model for the utility agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from experiment_agents.utility_agent import UtilityAgent
from utils.error_handling import ExperimentError, ExperimentErrorCategory, ErrorSeverity
from config.models import ExperimentConfiguration
from utils.language_manager import SupportedLanguage


class TestGeminiParsingFailure:
    """Test cases to reproduce and analyze the Gemini parsing failure."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration similar to stupid_max.yaml."""
        config = Mock(spec=ExperimentConfiguration)
        config.language = "English"
        config.utility_agent_model = "google/gemini-2.5-flash-lite"
        config.utility_agent_temperature = 0.0
        return config
    
    @pytest.fixture
    def utility_agent(self, mock_config):
        """Create utility agent with mocked dependencies."""
        with patch('experiment_agents.utility_agent.get_language_manager') as mock_lm:
            mock_lm.return_value.current_language = SupportedLanguage.ENGLISH
            agent = UtilityAgent(mock_config)
            return agent
    
    @pytest.mark.asyncio
    async def test_parsing_failure_reproduction(self, utility_agent):
        """Test that reproduces the exact parsing failure scenario."""
        
        # Mock problematic response that could come from Gemini model
        problematic_responses = [
            # Empty or malformed response
            "",
            
            # Response with wrong format
            "I think the principles are good but I cannot rank them properly.",
            
            # Response with incomplete ranking
            "1. Maximizing average income\n2. Floor constraint",
            
            # Response with wrong principle names
            "1. Some random principle\n2. Another weird principle\n3. Third one\n4. Fourth one",
            
            # Response in wrong language or mixed languages  
            "1. Principio de maximizar\n2. Floor constraint\n3. Range constraint\n4. Rawls difference",
        ]
        
        for response in problematic_responses:
            with patch.object(utility_agent, '_extract_ranking_direct', return_value=None) as mock_direct:
                with patch.object(utility_agent, '_extract_ranking_llm_fallback', return_value=None) as mock_llm:
                    
                    # This should raise ExperimentError after max retries
                    with pytest.raises(ExperimentError) as exc_info:
                        await utility_agent.parse_principle_ranking_enhanced(response, max_retries=3)
                    
                    # Verify the error details match what we saw in the log
                    error = exc_info.value
                    assert "Failed to parse principle ranking after 3 attempts" in str(error)
                    assert error.category == ExperimentErrorCategory.VALIDATION_ERROR
                    assert error.severity == ErrorSeverity.FATAL
                    assert "experiment must be aborted" in str(error)
    
    @pytest.mark.asyncio
    async def test_direct_parsing_method_failure(self, utility_agent):
        """Test the _extract_ranking_direct method specifically."""
        
        # Test with various malformed responses that Gemini might produce
        malformed_responses = [
            "Here are my thoughts on the principles...",  # No ranking format
            "1. First\n2. Second",  # Incomplete (< 4 items)
            "Principle A\nPrinciple B\nPrinciple C\nPrinciple D",  # No numbers
            "",  # Empty response
        ]
        
        for response in malformed_responses:
            result = await utility_agent._extract_ranking_direct(response)
            assert result is None, f"Expected None for response: {response}"
    
    @pytest.mark.asyncio 
    async def test_llm_fallback_parsing_failure(self, utility_agent):
        """Test the LLM fallback parsing method failure."""
        
        # Mock the LLM call to fail or return malformed data
        with patch.object(utility_agent, '_get_llm_client') as mock_client:
            mock_completion = Mock()
            mock_completion.choices = [Mock()]
            mock_completion.choices[0].message.content = '{"invalid": "json"}'  # Bad JSON
            mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_completion)
            
            result = await utility_agent._extract_ranking_llm_fallback("test response")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_pattern_matching_issues(self, utility_agent):
        """Test potential regex pattern matching issues."""
        
        # Test the language patterns that might fail with Gemini responses
        test_responses = [
            "1) First principle\n2) Second principle\n3) Third principle\n4) Fourth principle",  # Parentheses instead of dots
            "a. First principle\nb. Second principle\nc. Third principle\nd. Fourth principle",  # Letters instead of numbers
            "• First principle\n• Second principle\n• Third principle\n• Fourth principle",  # Bullet points
            "First: First principle\nSecond: Second principle\nThird: Third principle\nFourth: Fourth principle",  # Different format
        ]
        
        for response in test_responses:
            # Check if our regex patterns can handle these formats
            ranking_pattern = utility_agent._language_patterns.get('ranking_line')
            if ranking_pattern:
                matches = ranking_pattern.findall(response)
                # Document what patterns fail
                print(f"Response: {response[:50]}... -> Matches: {len(matches)}")
    
    def test_model_specific_issues(self):
        """Test for known issues with google/gemini-2.5-flash-lite model."""
        
        # Document potential model-specific issues
        model_issues = {
            "google/gemini-2.5-flash-lite": [
                "May produce inconsistent formatting",
                "Temperature 0.0 might still produce non-deterministic outputs", 
                "Could have different tokenization affecting pattern matching",
                "May not follow exact formatting instructions consistently"
            ]
        }
        
        # This test documents the issues for the report
        assert "google/gemini-2.5-flash-lite" in model_issues
        assert len(model_issues["google/gemini-2.5-flash-lite"]) > 0


class TestParsingRobustness:
    """Tests to verify parsing robustness across different scenarios."""
    
    @pytest.fixture
    def utility_agent(self):
        """Create utility agent for robustness testing."""
        config = Mock(spec=ExperimentConfiguration)
        config.language = "English"
        config.utility_agent_model = "gpt-4o-mini"  # Different model for comparison
        config.utility_agent_temperature = 0.0
        
        with patch('experiment_agents.utility_agent.get_language_manager') as mock_lm:
            mock_lm.return_value.current_language = SupportedLanguage.ENGLISH
            agent = UtilityAgent(config)
            return agent
    
    @pytest.mark.asyncio
    async def test_successful_parsing_formats(self, utility_agent):
        """Test various successful ranking formats that should work."""
        
        successful_formats = [
            """1. Maximizing average income
2. Floor constraint principle  
3. Range constraint principle
4. Rawls difference principle""",
            
            """My ranking is:
1. Floor constraint
2. Maximizing average 
3. Range constraint
4. Difference principle""",
        ]
        
        # Mock the LLM to return valid principle identifications
        with patch.object(utility_agent, '_identify_principle_in_text') as mock_identify:
            mock_identify.side_effect = [
                'maximizing_average',
                'floor_constraint', 
                'range_constraint',
                'rawls_difference'
            ] * len(successful_formats)
            
            for format_text in successful_formats:
                result = await utility_agent._extract_ranking_direct(format_text)
                if result:
                    assert len(result['rankings']) == 4
                    assert 'certainty' in result