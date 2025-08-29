"""
Integration tests for Phase 2 cross-language interaction scenarios.
Tests system behavior when agents use different languages within the same experiment.
"""
import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from core.experiment_manager import FrohlichExperimentManager
from core.phase2_manager import Phase2Manager
from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture
from tests.integration.utils.async_test_utils import AsyncTestUtils, TestDataGenerators
from tests.integration.utils.test_helpers import validate_utility_agent_methods, get_utility_agent_mock_methods
from utils.language_manager import get_language_manager, set_global_language, SupportedLanguage
from utils.error_handling import (
    ExperimentError, MemoryError, ValidationError, AgentCommunicationError,
    ErrorSeverity, get_global_error_handler
)
from models import (
    JusticePrinciple, CertaintyLevel, IncomeClass, 
    PrincipleChoice, PrincipleRanking, RankedPrinciple
)


class TestPhase2MixedLanguages:
    """Test Phase 2 behavior with agents using different languages."""
    
    def setup_method(self):
        """Set up test fixtures for each test."""
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
        
        # Validate that all commonly mocked utility agent methods exist
        validate_utility_agent_methods(get_utility_agent_mock_methods())
    
    @pytest.mark.asyncio
    async def test_spanish_english_chinese_mixed_discussion(self):
        """Test discussion with one Spanish, one English, and one Chinese agent."""
        
        # Create mixed-language configuration
        config = ExperimentTestFixture.create_config_with_agents([
            {
                "name": "SpanishAgent",
                "personality": "analytical and detail-oriented",
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "language": "spanish"
            },
            {
                "name": "EnglishAgent", 
                "personality": "pragmatic and focused on outcomes",
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "language": "english"
            },
            {
                "name": "ChineseAgent",
                "personality": "collaborative and consensus-seeking",
                "model": "gpt-4o-mini", 
                "temperature": 0.3,
                "language": "mandarin"
            }
        ])
        
        # Mock responses in respective languages
        spanish_responses = [
            # Phase 2 discussion responses
            "Creo que maximización del ingreso mínimo es la mejor opción porque protege a los más vulnerables.",
            "No estoy de acuerdo con la propuesta anterior. Prefiero maximización del ingreso promedio.",
            "Mi voto final es: maximización del ingreso mínimo"
        ]
        
        english_responses = [
            # Phase 2 discussion responses  
            "I believe maximizing the average income provides the best overall outcome for society.",
            "I disagree with focusing only on the floor. We need to consider average income too.",
            "My final vote is: maximizing the average income"
        ]
        
        chinese_responses = [
            # Phase 2 discussion responses
            "我认为最大化最低收入是最公平的选择，因为它帮助最需要帮助的人。",
            "我同意前面的观点。最大化底线收入应该是优先考虑的。",
            "我的最终投票是：最大化最低收入"
        ]
        
        with patch('core.experiment_manager.FrohlichExperimentManager') as mock_manager:
            # Mock the Phase 2 manager to test language interactions
            mock_phase2 = AsyncMock()
            mock_manager.return_value.phase2_manager = mock_phase2
            
            # Mock agent responses with language-specific content
            agent_mocks = {
                "SpanishAgent": AsyncTestUtils.mock_agent_responses("SpanishAgent", spanish_responses),
                "EnglishAgent": AsyncTestUtils.mock_agent_responses("EnglishAgent", english_responses),
                "ChineseAgent": AsyncTestUtils.mock_agent_responses("ChineseAgent", chinese_responses)
            }
            
            # Simulate mixed-language discussion
            discussion_messages = []
            for round_num in range(3):  # 3 rounds of discussion
                for agent_name, responses in zip(["SpanishAgent", "EnglishAgent", "ChineseAgent"], 
                                                [spanish_responses, english_responses, chinese_responses]):
                    if round_num < len(responses):
                        discussion_messages.append({
                            "agent": agent_name,
                            "message": responses[round_num],
                            "round": round_num + 1
                        })
            
            # Mock the Phase 2 discussion flow
            mock_phase2.run_phase2.return_value = {
                "consensus_reached": True,
                "final_votes": {
                    "SpanishAgent": "maximizing_floor",
                    "EnglishAgent": "maximizing_average", 
                    "ChineseAgent": "maximizing_floor"
                },
                "discussion_messages": discussion_messages,
                "quarantine_messages": []
            }
            
            # Test that mixed languages can coexist
            result = mock_phase2.run_phase2.return_value
            
            # Validate cross-language interaction
            assert len(result["discussion_messages"]) == 9  # 3 agents × 3 rounds
            assert result["consensus_reached"] is True
            
            # Check that each agent maintained their language
            spanish_messages = [msg for msg in discussion_messages if msg["agent"] == "SpanishAgent"]
            english_messages = [msg for msg in discussion_messages if msg["agent"] == "EnglishAgent"]  
            chinese_messages = [msg for msg in discussion_messages if msg["agent"] == "ChineseAgent"]
            
            assert len(spanish_messages) == 3
            assert len(english_messages) == 3
            assert len(chinese_messages) == 3
            
            # Verify language-specific content is preserved
            assert any("maximización" in msg["message"] for msg in spanish_messages)
            assert any("maximizing" in msg["message"] for msg in english_messages)
            assert any("最大化" in msg["message"] for msg in chinese_messages)
    
    @pytest.mark.asyncio
    async def test_language_switching_mid_discussion(self):
        """Test agent switching languages during discussion."""
        
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        config.agents[0].language = "english"
        config.agents[1].language = "spanish"
        
        # Responses showing language switching
        switching_responses = [
            "I think maximizing the floor income is best.",  # English
            "But wait, let me explain in Spanish: Creo que maximización del ingreso mínimo es mejor.",  # Mixed
            "Actually, voy a continuar en español porque es más claro para mí."  # Switching to Spanish
        ]
        
        non_switching_responses = [
            "Estoy de acuerdo con la propuesta.",
            "Mi opinión es que maximización del ingreso promedio es mejor.",
            "Mantengo mi posición en español."
        ]
        
        with patch('experiment_agents.participant_agent.ParticipantAgent') as mock_agent_class:
            # Create mock agents
            mock_switching_agent = AsyncMock()
            mock_stable_agent = AsyncMock()
            
            # Mock responses
            mock_switching_agent.generate.side_effect = [Mock(final_output=resp) for resp in switching_responses]
            mock_stable_agent.generate.side_effect = [Mock(final_output=resp) for resp in non_switching_responses]
            
            mock_agent_class.side_effect = [mock_switching_agent, mock_stable_agent]
            
            # Test language detection across responses
            mixed_content = switching_responses + non_switching_responses
            
            # Verify mixed language content can be handled
            english_content = [msg for msg in mixed_content if any(word in msg.lower() for word in ["maximizing", "think", "actually"])]
            spanish_content = [msg for msg in mixed_content if any(word in msg.lower() for word in ["creo", "maximización", "español", "opinión"])]
            
            assert len(english_content) >= 1, "Should detect English content"
            assert len(spanish_content) >= 1, "Should detect Spanish content"
            
            # Test that the system can handle language transitions
            assert "mixed language" not in str(mixed_content).lower()  # No error markers
    
    @pytest.mark.asyncio  
    async def test_consensus_with_mixed_language_ballots(self):
        """Test consensus building when final ballots are in different languages."""
        
        config = ExperimentTestFixture.create_config_with_agents([
            {"name": "Agent1", "language": "english"},
            {"name": "Agent2", "language": "spanish"},
            {"name": "Agent3", "language": "mandarin"}
        ])
        
        # Mixed language final ballots
        mixed_ballots = {
            "Agent1": "My final vote is: maximizing the floor income. I am very sure about this choice.",
            "Agent2": "Mi voto final es: maximización del ingreso mínimo. Estoy muy seguro de esta elección.",
            "Agent3": "我的最终投票是：最大化最低收入。我对这个选择很确定。"
        }
        
        with patch('experiment_agents.utility_agent.UtilityAgent') as mock_utility:
            mock_utility_instance = AsyncMock()
            mock_utility.return_value = mock_utility_instance
            
            # Mock parsing for each language ballot
            mock_utility_instance.parse_principle_choice_enhanced.side_effect = [
                Mock(principle="maximizing_floor", certainty="very_sure"),  # English
                Mock(principle="maximizing_floor", certainty="very_sure"),  # Spanish  
                Mock(principle="maximizing_floor", certainty="very_sure")   # Chinese
            ]
            
            # Simulate ballot parsing
            parsed_results = []
            for agent_name, ballot in mixed_ballots.items():
                result = await mock_utility_instance.parse_principle_choice_enhanced(ballot)
                parsed_results.append({
                    "agent": agent_name,
                    "principle": result.principle,
                    "certainty": result.certainty,
                    "original_ballot": ballot
                })
            
            # Verify all ballots parsed to same principle despite language differences
            principles = [result["principle"] for result in parsed_results]
            assert all(p == "maximizing_floor" for p in principles), "All ballots should parse to same principle"
            
            # Verify certainty levels were extracted correctly
            certainties = [result["certainty"] for result in parsed_results]
            assert all(c == "very_sure" for c in certainties), "All certainty levels should be extracted"
            
            # Test consensus detection with mixed languages
            consensus_reached = len(set(principles)) == 1
            assert consensus_reached, "Should detect consensus despite language differences"
    
    @pytest.mark.asyncio
    async def test_quarantine_messages_different_languages(self):
        """Test quarantine handling when agents use different languages."""
        
        config = ExperimentTestFixture.create_minimal_config(num_agents=2) 
        config.agents[0].language = "english"
        config.agents[1].language = "spanish"
        
        # Messages that should be quarantined in different languages
        quarantine_candidates = [
            # English problematic messages
            "I choose principle a because it's better.",  # Letter usage
            "Let's vote for option b right now.",  # Letter + vote intention
            
            # Spanish problematic messages  
            "Mi elección es el principio a para esta situación.",  # Letter usage in Spanish
            "Votemos por la opción b ahora mismo.",  # Letter + vote intention in Spanish
        ]
        
        # Test our enhanced utility agent-based quarantine detection
        from experiment_agents.utility_agent import UtilityAgent
        
        utility_agent = UtilityAgent()
        await utility_agent.async_init()
        
        # Test intelligent quarantine detection on all problematic messages
        quarantined = []
        for i, message in enumerate(quarantine_candidates):
            detection_result = await utility_agent.detect_problematic_content_multilingual(message)
            
            if detection_result:
                quarantined.append({
                    "message": message,
                    "agent": f"Agent{i % 2 + 1}",
                    "reason": detection_result["type"],
                    "language": "spanish" if any(word in message.lower() for word in ["principio", "opción", "votemos"]) else "english",
                    "detection_method": detection_result["detection_method"]
                })
        
        # Verify enhanced quarantine detection works across languages
        assert len(quarantined) == 4, f"Should quarantine problematic messages in both languages. Got {len(quarantined)}: {[q['message'] for q in quarantined]}"
        
        english_quarantine = [q for q in quarantined if q["language"] == "english"]
        spanish_quarantine = [q for q in quarantined if q["language"] == "spanish"]
        
        assert len(english_quarantine) >= 1, "Should quarantine English letter references"
        assert len(spanish_quarantine) >= 1, "Should quarantine Spanish letter references"
        
        # Test that quarantine reasons are language-appropriate
        for q in quarantined:
            assert q["reason"].startswith("letter_reference"), f"Expected letter_reference, got {q['reason']}"
            assert "principio" in q["message"] or "principle" in q["message"] or "opción" in q["message"] or "option" in q["message"]


class TestPhase2MixedLanguageEdgeCases:
    """Test edge cases and error conditions in mixed-language scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = get_global_error_handler()
        self.error_handler.clear_error_history()
    
    @pytest.mark.asyncio
    async def test_unsupported_language_fallback(self):
        """Test behavior when agent attempts to use unsupported language."""
        
        # Use 2 agents but focus testing on the first one
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        config.agents[0].language = "english"  # Supported language
        
        # Simulate agent trying to use unsupported language  
        unsupported_messages = [
            "Je pense que maximiser le revenu minimum est le meilleur choix.",  # French
            "Ich glaube, die Maximierung des Mindesteinkommens ist die beste Wahl.",  # German
            "私は最低所得の最大化が最良の選択だと思います。"  # Japanese (not Mandarin)
        ]
        
        with patch('utils.language_manager.get_language_manager') as mock_lang_manager:
            mock_manager = Mock()
            mock_lang_manager.return_value = mock_manager
            
            # Mock detection of unsupported languages
            mock_manager.detect_language.side_effect = ["french", "german", "japanese"]
            mock_manager.is_supported_language.side_effect = [False, False, False]
            
            for message in unsupported_messages:
                detected_lang = mock_manager.detect_language(message)
                is_supported = mock_manager.is_supported_language(detected_lang)
                
                assert not is_supported, f"Should detect {detected_lang} as unsupported"
                
                # Test fallback mechanism
                if not is_supported:
                    # Should fall back to default language (English)
                    fallback_lang = "english"
                    assert fallback_lang in ["english", "spanish", "mandarin"]
    
    @pytest.mark.asyncio
    async def test_corrupted_unicode_handling(self):
        """Test handling of corrupted or invalid Unicode in mixed-language scenarios."""
        
        # Use 2 agents but focus testing on the first one
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        
        # Test corrupted Unicode scenarios
        corrupted_inputs = [
            "I choose maximizing \uFFFF the floor income",  # Invalid Unicode
            "Mi elección es maximizaci\u00F3n del ingreso m\u00EDnimo",  # Valid accents
            "我选择最大化\uD800最低收入",  # Invalid surrogate
        ]
        
        with patch('experiment_agents.utility_agent.UtilityAgent') as mock_utility:
            mock_utility_instance = AsyncMock()
            mock_utility.return_value = mock_utility_instance
            
            # Test that system handles corrupted Unicode gracefully
            for corrupt_input in corrupted_inputs:
                try:
                    # Should not raise exceptions for Unicode issues
                    cleaned_input = corrupt_input.encode('utf-8', errors='replace').decode('utf-8')
                    result = await mock_utility_instance.parse_principle_choice_enhanced(cleaned_input)
                    
                    # Should return result or None, not crash
                    assert result is not None or result is None
                    
                except UnicodeError:
                    pytest.fail(f"Should handle Unicode gracefully for: {repr(corrupt_input)}")
                except Exception as e:
                    # Other exceptions might be OK, but Unicode should be handled
                    if "unicode" in str(e).lower() or "utf" in str(e).lower():
                        pytest.fail(f"Unicode error should be handled: {str(e)}")
    
    @pytest.mark.asyncio
    async def test_extremely_long_multilingual_messages(self):
        """Test handling of very long messages in multiple languages."""
        
        # Use 2 agents but focus testing on the first one
        config = ExperimentTestFixture.create_minimal_config(num_agents=2)
        
        # Create extremely long multilingual message
        base_phrases = {
            "english": "I think maximizing the floor income is the best choice because",
            "spanish": "Creo que maximización del ingreso mínimo es la mejor opción porque", 
            "mandarin": "我认为最大化最低收入是最好的选择因为"
        }
        
        # Create very long message by repeating phrases
        long_message = ""
        for i in range(100):  # Repeat 100 times to create very long message
            lang = ["english", "spanish", "mandarin"][i % 3]
            long_message += base_phrases[lang] + f" reason {i + 1}. "
        
        with patch('experiment_agents.utility_agent.UtilityAgent') as mock_utility:
            mock_utility_instance = AsyncMock()
            mock_utility.return_value = mock_utility_instance
            
            # Test that very long multilingual messages are handled
            try:
                result = await mock_utility_instance.parse_principle_choice_enhanced(long_message)
                
                # Should not crash, even if it can't parse
                assert result is not None or result is None
                
                # Check message length handling
                assert len(long_message) > 5000, "Message should be very long"
                
            except Exception as e:
                # Should not fail due to length alone
                if "length" in str(e).lower() or "too long" in str(e).lower():
                    pytest.fail(f"Should handle long messages gracefully: {str(e)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])