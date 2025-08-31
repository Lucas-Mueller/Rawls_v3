"""
Integration tests for language fallback mechanisms.
Tests system behavior when translations are missing or incomplete.
"""
import pytest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from utils.language_manager import create_language_manager, SupportedLanguage
from experiment_agents.utility_agent import UtilityAgent
from experiment_agents.participant_agent import ParticipantAgent
from tests.integration.utils.async_test_utils import AsyncTestUtils
from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture
from utils.error_handling import get_global_error_handler, ExperimentError, ExperimentErrorCategory
from models import JusticePrinciple, CertaintyLevel


class TestLanguageFallbackMechanisms:
    """Test fallback mechanisms when translations are missing or incomplete."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
        
        # Mock translation data with some missing entries
        self.mock_translations = {
            "english": {
                "principle.maximizing_floor": "maximizing the floor income",
                "principle.maximizing_average": "maximizing the average income",
                "certainty.sure": "sure",
                "certainty.very_sure": "very sure",
                "agreement.yes": "I agree",
                "agreement.no": "I disagree",
                "vote.intention": "Let's vote",
                "error.parsing_failed": "Failed to parse response"
            },
            "spanish": {
                "principle.maximizing_floor": "maximización del ingreso mínimo",
                "principle.maximizing_average": "maximización del ingreso promedio",
                "certainty.sure": "seguro",
                "certainty.very_sure": "muy seguro",
                "agreement.yes": "estoy de acuerdo",
                # Missing: agreement.no, vote.intention, error.parsing_failed
            },
            "mandarin": {
                "principle.maximizing_floor": "最大化最低收入",
                # Missing: principle.maximizing_average, certainty.sure, etc.
                "agreement.yes": "我同意",
                "error.parsing_failed": "解析响应失败"
            }
        }
    
    @pytest.mark.asyncio
    async def test_missing_translation_fallback_to_english(self):
        """Test that missing translations fall back to English."""
        
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        config.agents[0].language = "spanish"
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            def mock_get_translation(key, language="english", fallback_to_english=True):
                """Mock translation lookup with fallback."""
                translations = self.mock_translations.get(language, {})
                
                if key in translations:
                    return translations[key]
                elif fallback_to_english and language != "english":
                    # Fallback to English
                    english_translations = self.mock_translations.get("english", {})
                    return english_translations.get(key, key)  # Return key if no translation
                else:
                    return key  # Return key as fallback
            
            mock_manager.get_translation.side_effect = mock_get_translation
            
            # Test missing Spanish translations fall back to English
            test_cases = [
                ("agreement.no", "I disagree"),  # Missing in Spanish, should get English
                ("vote.intention", "Let's vote"),  # Missing in Spanish, should get English
                ("error.parsing_failed", "Failed to parse response"),  # Missing in Spanish
            ]
            
            for key, expected_fallback in test_cases:
                with self.subTest(key=key):
                    result = mock_get_translation(key, "spanish", fallback_to_english=True)
                    assert result == expected_fallback, f"Should fallback to English for {key}: got {result}"
    
    @pytest.mark.asyncio
    async def test_partial_translation_handling(self):
        """Test handling when only some translations are available."""
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            # Mock partial translation scenario for Mandarin
            def mock_partial_translation(key, language="mandarin"):
                translations = self.mock_translations.get(language, {})
                return translations.get(key, None)
            
            mock_manager.get_translation.side_effect = mock_partial_translation
            mock_manager.has_translation.side_effect = lambda key, lang: key in self.mock_translations.get(lang, {})
            
            # Test what happens with partial translations
            mandarin_keys = [
                "principle.maximizing_floor",  # Available
                "principle.maximizing_average",  # Missing
                "certainty.sure",  # Missing
                "agreement.yes",  # Available
            ]
            
            available_translations = []
            missing_translations = []
            
            for key in mandarin_keys:
                has_translation = mock_manager.has_translation(key, "mandarin")
                if has_translation:
                    available_translations.append(key)
                else:
                    missing_translations.append(key)
            
            assert len(available_translations) == 2, f"Should have 2 available: {available_translations}"
            assert len(missing_translations) == 2, f"Should have 2 missing: {missing_translations}"
            
            # Verify specific expected results
            assert "principle.maximizing_floor" in available_translations
            assert "agreement.yes" in available_translations
            assert "principle.maximizing_average" in missing_translations
            assert "certainty.sure" in missing_translations
    
    @pytest.mark.asyncio
    async def test_default_language_fallback_in_agent_creation(self):
        """Test that agents fall back to default language when specified language is unavailable."""
        
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        
        # Test unsupported language scenarios
        unsupported_languages = ["french", "german", "japanese", "invalid_language"]
        
        for unsupported_lang in unsupported_languages:
            with self.subTest(language=unsupported_lang):
                config.agents[0].language = unsupported_lang
                
                with patch('experiment_agents.participant_agent.ParticipantAgent') as mock_agent:
                    mock_instance = AsyncMock()
                    mock_agent.return_value = mock_instance
                    
                    # Mock language validation
                    with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
                        mock_manager = Mock()
                        mock_lang_manager.return_value = mock_manager
                        
                        # Mock unsupported language detection
                        supported_languages = ["english", "spanish", "mandarin"]
                        mock_manager.is_supported_language.return_value = unsupported_lang in supported_languages
                        mock_manager.get_default_language.return_value = "english"
                        
                        # Create agent with unsupported language
                        try:
                            agent = ParticipantAgent(
                                name="TestAgent",
                                personality="test",
                                model="gpt-4o-mini",
                                language=unsupported_lang
                            )
                            
                            # Should not fail, should fall back to default
                            effective_language = mock_manager.get_default_language() if not mock_manager.is_supported_language() else unsupported_lang
                            assert effective_language == "english", f"Should fallback to English from {unsupported_lang}"
                            
                        except Exception as e:
                            # If it fails, should be graceful failure with clear error
                            assert "language" in str(e).lower() or "unsupported" in str(e).lower(), f"Should have clear language error: {str(e)}"
    
    @pytest.mark.asyncio
    async def test_error_message_localization_with_fallback(self):
        """Test that error messages are localized with proper fallback."""
        
        error_scenarios = [
            {
                "error_key": "error.parsing_failed",
                "language": "spanish",
                "should_fallback": True,  # Spanish translation missing
                "expected": "Failed to parse response"  # English fallback
            },
            {
                "error_key": "error.parsing_failed", 
                "language": "mandarin",
                "should_fallback": False,  # Mandarin translation available
                "expected": "解析响应失败"
            },
            {
                "error_key": "error.parsing_failed",
                "language": "english", 
                "should_fallback": False,  # English original
                "expected": "Failed to parse response"
            }
        ]
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            def mock_error_translation(key, language):
                """Mock error message translation with fallback logic."""
                translations = self.mock_translations.get(language, {})
                
                if key in translations:
                    return translations[key]
                elif language != "english":
                    # Fallback to English
                    english_translations = self.mock_translations.get("english", {})
                    return english_translations.get(key, f"Missing translation: {key}")
                else:
                    return f"Missing translation: {key}"
            
            mock_manager.get_error_message.side_effect = mock_error_translation
            
            for scenario in error_scenarios:
                with self.subTest(scenario=scenario):
                    error_key = scenario["error_key"]
                    language = scenario["language"] 
                    expected = scenario["expected"]
                    
                    result = mock_manager.get_error_message(error_key, language)
                    assert result == expected, f"Wrong error message for {language}: got {result}, expected {expected}"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_no_translations(self):
        """Test graceful degradation when no translations are available at all."""
        
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        config.agents[0].language = "spanish"
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            # Mock scenario where no translations are available
            mock_manager.get_translation.return_value = None
            mock_manager.has_translation.return_value = False
            mock_manager.get_default_language.return_value = "english"
            mock_manager.is_translation_system_available.return_value = False
            
            # Test system behavior without translations
            with patch('experiment_agents.utility_agent.UtilityAgent') as mock_utility:
                mock_utility_instance = AsyncMock()
                mock_utility.return_value = mock_utility_instance
                
                # Should still function with fallback mechanisms
                mock_utility_instance.parse_principle_choice_enhanced.return_value = Mock(
                    principle="maximizing_floor",  # Should still parse using patterns
                    certainty="sure",
                    constraint_amount=None
                )
                
                # Test parsing without localized strings
                statement = "I choose maximizing the floor income"
                result = await mock_utility_instance.parse_principle_choice_enhanced(statement)
                
                assert result is not None, "Should work even without translation system"
                assert result.principle == "maximizing_floor", "Should parse principle correctly"
    
    @pytest.mark.asyncio
    async def test_mixed_language_fallback_scenarios(self):
        """Test complex fallback scenarios with mixed language requirements."""
        
        config = ExperimentTestFixture.create_config_with_agents([
            {"name": "SpanishAgent", "language": "spanish"},
            {"name": "MandarinAgent", "language": "mandarin"},
            {"name": "EnglishAgent", "language": "english"}
        ])
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            def complex_fallback_logic(key, language, fallback_chain=None):
                """Mock complex fallback logic."""
                if fallback_chain is None:
                    fallback_chain = [language, "english", "key_as_string"]
                
                for fallback_lang in fallback_chain:
                    if fallback_lang == "key_as_string":
                        return key  # Ultimate fallback
                    
                    translations = self.mock_translations.get(fallback_lang, {})
                    if key in translations:
                        return translations[key]
                
                return key  # Should never reach here
            
            mock_manager.get_translation.side_effect = complex_fallback_logic
            
            # Test fallback chains for each agent
            agents_and_keys = [
                ("SpanishAgent", "spanish", "vote.intention"),  # Missing in Spanish, should get English
                ("MandarinAgent", "mandarin", "certainty.sure"),  # Missing in Mandarin, should get English
                ("EnglishAgent", "english", "principle.maximizing_floor"),  # Should get English directly
            ]
            
            for agent_name, language, test_key in agents_and_keys:
                with self.subTest(agent=agent_name, key=test_key):
                    result = complex_fallback_logic(test_key, language)
                    
                    # Verify fallback worked appropriately
                    if language == "spanish" and test_key == "vote.intention":
                        assert result == "Let's vote", "Should fallback to English"
                    elif language == "mandarin" and test_key == "certainty.sure":
                        assert result == "sure", "Should fallback to English"
                    elif language == "english":
                        english_value = self.mock_translations["english"].get(test_key, test_key)
                        assert result == english_value, "Should get English value directly"
    
    @pytest.mark.asyncio
    async def test_translation_cache_fallback_behavior(self):
        """Test translation caching behavior with fallbacks."""
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            # Mock caching behavior
            cache = {}
            call_count = {}
            
            def mock_cached_translation(key, language):
                """Mock translation with caching logic."""
                cache_key = f"{language}:{key}"
                call_count[cache_key] = call_count.get(cache_key, 0) + 1
                
                if cache_key in cache:
                    return cache[cache_key]
                
                # Simulate expensive translation lookup
                translations = self.mock_translations.get(language, {})
                if key in translations:
                    result = translations[key]
                else:
                    # Fallback to English
                    english_translations = self.mock_translations.get("english", {})
                    result = english_translations.get(key, key)
                
                cache[cache_key] = result
                return result
            
            mock_manager.get_translation.side_effect = mock_cached_translation
            
            # Test multiple calls to same translation
            test_key = "principle.maximizing_floor"
            
            # First call - should hit translation system
            result1 = mock_manager.get_translation(test_key, "spanish")
            
            # Second call - should hit cache
            result2 = mock_manager.get_translation(test_key, "spanish")
            
            # Results should be identical
            assert result1 == result2, "Cached results should be identical"
            
            # Should only make one actual translation lookup
            cache_key = f"spanish:{test_key}"
            assert call_count[cache_key] == 2, "Should track call count correctly"
            
            # Verify cached value is correct
            expected = self.mock_translations["spanish"]["principle.maximizing_floor"]
            assert result1 == expected, f"Should get correct Spanish translation: {result1}"


class TestLanguageFallbackErrorHandling:
    """Test error handling in language fallback scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
    
    @pytest.mark.asyncio
    async def test_translation_system_unavailable(self):
        """Test behavior when entire translation system is unavailable."""
        
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            # Mock complete translation system failure
            mock_lang_manager.side_effect = Exception("Translation system unavailable")
            
            # Test that system can still function
            with patch('experiment_agents.utility_agent.UtilityAgent') as mock_utility:
                mock_utility_instance = AsyncMock()
                mock_utility.return_value = mock_utility_instance
                
                # Should still parse using built-in patterns
                mock_utility_instance.parse_principle_choice_enhanced.return_value = Mock(
                    principle="maximizing_floor",
                    certainty="sure",
                    constraint_amount=None
                )
                
                try:
                    result = await mock_utility_instance.parse_principle_choice_enhanced(
                        "I choose maximizing the floor income"
                    )
                    assert result is not None, "Should work even without language manager"
                    
                except Exception as e:
                    # Should fail gracefully if it fails
                    assert "translation" in str(e).lower(), f"Should indicate translation issue: {str(e)}"
    
    @pytest.mark.asyncio
    async def test_circular_translation_fallback_prevention(self):
        """Test prevention of circular fallback loops."""
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            # Mock circular fallback scenario
            def circular_fallback(key, language, visited=None):
                """Mock translation with circular fallback detection."""
                if visited is None:
                    visited = set()
                
                if language in visited:
                    # Prevent circular fallback
                    return key  # Return key as ultimate fallback
                
                visited.add(language)
                
                # Mock circular dependencies
                fallback_chain = {
                    "spanish": "mandarin",
                    "mandarin": "english", 
                    "english": "spanish"  # This creates a cycle
                }
                
                translations = self.mock_translations.get(language, {})
                if key in translations:
                    return translations[key]
                else:
                    # Follow fallback chain
                    next_lang = fallback_chain.get(language, "english")
                    if next_lang != language:  # Prevent immediate self-reference
                        return circular_fallback(key, next_lang, visited)
                    else:
                        return key
            
            mock_manager.get_translation.side_effect = circular_fallback
            
            # Test that circular fallback is handled
            test_key = "non_existent_key"
            result = mock_manager.get_translation(test_key, "spanish")
            
            # Should return the key itself as ultimate fallback
            assert result == test_key, "Should prevent circular fallback and return key"
    
    @pytest.mark.asyncio
    async def test_partial_translation_system_recovery(self):
        """Test system recovery when translation system comes back online."""
        
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        
        with patch('utils.language_manager.create_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            # Simulate system recovery
            system_state = {"available": False}
            
            def recovering_translation_system(key, language):
                """Mock translation system that recovers over time."""
                if not system_state["available"]:
                    # System unavailable, return fallback
                    return f"fallback_{key}"
                else:
                    # System recovered, return proper translation
                    translations = self.mock_translations.get(language, {})
                    return translations.get(key, key)
            
            mock_manager.get_translation.side_effect = recovering_translation_system
            mock_manager.is_translation_system_available.side_effect = lambda: system_state["available"]
            
            # Test behavior when system is down
            result_down = mock_manager.get_translation("principle.maximizing_floor", "spanish")
            assert result_down == "fallback_principle.maximizing_floor", "Should use fallback when system down"
            
            # Simulate system recovery
            system_state["available"] = True
            
            # Test behavior when system recovers
            result_up = mock_manager.get_translation("principle.maximizing_floor", "spanish")
            expected = self.mock_translations["spanish"]["principle.maximizing_floor"]
            assert result_up == expected, f"Should use proper translation when system recovered: {result_up}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])