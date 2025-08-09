"""
Integration tests for multilingual logging behavior.

Tests that ensure agents receive prompts in their configured language
while system logs maintain English consistency for developer readability.
"""
import asyncio
import logging
import tempfile
import unittest
from io import StringIO
from unittest.mock import Mock, patch
from pathlib import Path

from utils.language_manager import (
    get_language_manager, set_global_language, SupportedLanguage,
    get_english_principle_name, get_english_certainty_name
)
from models.principle_types import JusticePrinciple, CertaintyLevel, PrincipleChoice
from experiment_agents.utility_agent import UtilityAgent
from config import ExperimentConfiguration, AgentConfiguration


class TestMultilingualLogging(unittest.TestCase):
    """Test multilingual logging behavior integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Store original language to restore later
        self.original_language = get_language_manager().current_language
        
        # Create log capture
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)
        
        # Add handler to utility agent logger
        self.utility_logger = logging.getLogger('experiment_agents.utility_agent')
        self.utility_logger.addHandler(self.handler)
        self.utility_logger.setLevel(logging.INFO)
        
        # Create utility agent for testing
        self.utility_agent = UtilityAgent()

    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original language
        set_global_language(self.original_language)
        
        # Remove test handler
        self.utility_logger.removeHandler(self.handler)
        self.handler.close()

    def test_spanish_agent_english_logs(self):
        """Test that Spanish agents generate English principle names in logs."""
        # Set system to Spanish
        set_global_language(SupportedLanguage.SPANISH)
        lm = get_language_manager()
        
        # Verify language is set correctly
        assert lm.current_language == SupportedLanguage.SPANISH
        
        # Test principle names are different between languages
        principle_key = "maximizing_floor"
        spanish_name = lm.get_justice_principle_name(principle_key)
        english_name = get_english_principle_name(principle_key)
        
        assert spanish_name != english_name
        assert spanish_name == "Aprovechar al máximo el suelo"
        assert english_name == "Maximizing the floor"
        
        # Test certainty levels are different between languages
        certainty_key = "very_sure"
        spanish_certainty = lm.get_certainty_level_name(certainty_key)
        english_certainty = get_english_certainty_name(certainty_key)
        
        assert spanish_certainty != english_certainty
        assert spanish_certainty == "muy seguro"
        assert english_certainty == "very sure"

    def test_mandarin_agent_english_logs(self):
        """Test that Mandarin agents generate English principle names in logs."""
        # Set system to Mandarin
        set_global_language(SupportedLanguage.MANDARIN)
        lm = get_language_manager()
        
        # Verify language is set correctly
        assert lm.current_language == SupportedLanguage.MANDARIN
        
        # Test principle names are different between languages
        principle_key = "maximizing_average"
        mandarin_name = lm.get_justice_principle_name(principle_key)
        english_name = get_english_principle_name(principle_key)
        
        assert mandarin_name != english_name
        assert mandarin_name == "最大化平均值"
        assert english_name == "Maximizing the average"

    def test_utility_agent_logging_consistency(self):
        """Test that utility agent logs always use English regardless of current language."""
        # Set system to Spanish
        set_global_language(SupportedLanguage.SPANISH)
        
        # Create a choice that requires constraint
        choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=15000,
            certainty=CertaintyLevel.SURE,
            reasoning="Test reasoning"
        )
        
        # Clear log stream
        self.log_stream.seek(0)
        self.log_stream.truncate(0)
        
        # Call utility agent method that logs (run async in unittest)
        async def _test_logging():
            await self.utility_agent.re_prompt_for_constraint("TestAgent", choice)
        
        asyncio.run(_test_logging())
        
        # Check log contents
        log_contents = self.log_stream.getvalue()
        
        # Verify English principle name is used in logs
        assert "floor constraint" in log_contents.lower() or "constraint" in log_contents.lower()
        
        # Verify no Spanish text leaked into logs
        spanish_words = ["maximizando", "restricción", "suelo"]
        for word in spanish_words:
            assert word not in log_contents.lower()

    def test_language_isolation_principle_names(self):
        """Test that principle name functions properly isolate languages."""
        original_language = SupportedLanguage.ENGLISH
        
        # Test with Spanish set as global language
        set_global_language(SupportedLanguage.SPANISH)
        
        # Get principle name through global language (should be Spanish)
        lm = get_language_manager()
        spanish_principle = lm.get_justice_principle_name("maximizing_floor")
        
        # Get principle name through English function (should always be English)
        english_principle = get_english_principle_name("maximizing_floor")
        
        # Verify they are different and correct
        assert spanish_principle == "Aprovechar al máximo el suelo"
        assert english_principle == "Maximizing the floor" 
        
        # Verify global language is still Spanish after English function call
        assert lm.current_language == SupportedLanguage.SPANISH

    def test_language_isolation_certainty_levels(self):
        """Test that certainty level functions properly isolate languages."""
        # Test with Mandarin set as global language
        set_global_language(SupportedLanguage.MANDARIN)
        
        # Get certainty level through global language (should be Mandarin)
        lm = get_language_manager()
        mandarin_certainty = lm.get_certainty_level_name("very_sure")
        
        # Get certainty level through English function (should always be English)
        english_certainty = get_english_certainty_name("very_sure")
        
        # Verify they are different and correct
        assert mandarin_certainty == "很确定"
        assert english_certainty == "very sure"
        
        # Verify global language is still Mandarin after English function call
        assert lm.current_language == SupportedLanguage.MANDARIN

    def test_all_languages_have_consistent_keys(self):
        """Test that all supported languages have the same set of principle and certainty keys."""
        principle_keys = ["maximizing_floor", "maximizing_average", 
                         "maximizing_average_floor_constraint", "maximizing_average_range_constraint"]
        certainty_keys = ["very_unsure", "unsure", "no_opinion", "sure", "very_sure"]
        
        for language in SupportedLanguage:
            set_global_language(language)
            lm = get_language_manager()
            
            # Test all principle keys exist
            for key in principle_keys:
                principle_name = lm.get_justice_principle_name(key)
                assert principle_name is not None
                assert len(principle_name.strip()) > 0
            
            # Test all certainty keys exist
            for key in certainty_keys:
                certainty_name = lm.get_certainty_level_name(key)
                assert certainty_name is not None
                assert len(certainty_name.strip()) > 0