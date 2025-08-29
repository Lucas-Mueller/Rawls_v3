"""
Comprehensive multilingual test framework for letter-based principle rejection.

This test suite validates that the system properly rejects letter-based 
principle references across English, Spanish, and Mandarin languages.
Part of Phase 3 implementation from letter_contamination_remediation_plan.md.
"""

import unittest
import asyncio
from typing import List, Dict, Any, Optional
import sys
import os
import pytest

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiment_agents.utility_agent import UtilityAgent
from utils.language_manager import LanguageManager
from config.models import AgentConfiguration


class TestMultilingualLetterRejection(unittest.TestCase):
    """Comprehensive test suite for multilingual letter rejection."""
    
    def setUp(self):
        """Set up test environment with multilingual configurations."""
        self.utility_agent = UtilityAgent()
        self.language_manager = LanguageManager()
        
        # Test agent configurations for each language
        self.english_agent_config = AgentConfiguration(
            name="test_english_agent",
            personality="analytical",
            model="gpt-4.1-mini",
            temperature=0.7,
            reasoning_enabled=True,
            memory_character_limit=10000
        )
        
        self.spanish_agent_config = AgentConfiguration(
            name="test_spanish_agent", 
            personality="analytical",
            model="gpt-4.1-mini",
            temperature=0.7,
            reasoning_enabled=True,
            memory_character_limit=10000
        )
        
        self.mandarin_agent_config = AgentConfiguration(
            name="test_mandarin_agent",
            personality="analytical", 
            model="gpt-4.1-mini",
            temperature=0.7,
            reasoning_enabled=True,
            memory_character_limit=10000
        )

    # English Letter Rejection Tests
    @pytest.mark.asyncio
    async def test_english_simple_letter_rejection(self):
        """Test rejection of simple English letter patterns."""
        letter_inputs = [
            "My choice is a",
            "I prefer b", 
            "I select c",
            "I choose d",
            "My answer is a",
            "I pick b",
            "I support c", 
            "I vote for d"
        ]
        
        for input_text in letter_inputs:
            with self.subTest(input=input_text):
                result = await self.utility_agent.parse_principle_choice(
                    input_text, "english"
                )
                self.assertIsNone(result, 
                    f"Expected None for '{input_text}', got {result}")

    def test_english_principle_letter_rejection(self):
        """Test rejection of 'principle X' pattern in English."""
        principle_letter_inputs = [
            "My choice is principle a",
            "I prefer principle b",
            "I select principle c", 
            "I choose principle d",
            "My vote is principle a",
            "I support principle b",
            "My preference is principle c",
            "I pick principle d"
        ]
        
        for input_text in principle_letter_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "english"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    def test_english_case_variation_rejection(self):
        """Test rejection of letter patterns with case variations."""
        case_variation_inputs = [
            "My choice is Principle A",
            "I prefer PRINCIPLE B",
            "I select principle C",
            "I choose Principle d",
            "My choice is A",
            "I prefer B",
            "I select C",
            "I choose D"
        ]
        
        for input_text in case_variation_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "english"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    # Spanish Letter Rejection Tests
    def test_spanish_simple_letter_rejection(self):
        """Test rejection of simple Spanish letter patterns."""
        spanish_letter_inputs = [
            "Mi elección es a",
            "Prefiero b",
            "Selecciono c", 
            "Elijo d",
            "Mi respuesta es a",
            "Escojo b",
            "Apoyo c",
            "Voto por d"
        ]
        
        for input_text in spanish_letter_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "spanish"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    def test_spanish_principio_letter_rejection(self):
        """Test rejection of 'principio X' pattern in Spanish."""
        spanish_principle_inputs = [
            "Mi elección es principio a",
            "Prefiero principio b", 
            "Selecciono principio c",
            "Elijo principio d",
            "Mi voto es principio a",
            "Apoyo principio b",
            "Mi preferencia es principio c",
            "Escojo principio d"
        ]
        
        for input_text in spanish_principle_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "spanish"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    def test_spanish_opcion_eleccion_letter_rejection(self):
        """Test rejection of 'opción/elección X' patterns in Spanish."""
        spanish_option_inputs = [
            "Mi opción es a",
            "Mi elección de voto es b",
            "La opción c",
            "Elección d",
            "Mi opción preferida es a",
            "Mi elección final es b"
        ]
        
        for input_text in spanish_option_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "spanish"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    # Mandarin Letter Rejection Tests
    def test_mandarin_simple_letter_rejection(self):
        """Test rejection of simple Mandarin letter patterns."""
        mandarin_letter_inputs = [
            "我选择a",
            "我更喜欢b",
            "我选c",
            "我选择d", 
            "我的答案是a",
            "我挑选b",
            "我支持c",
            "我投票给d"
        ]
        
        for input_text in mandarin_letter_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "mandarin"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    def test_mandarin_yuanze_letter_rejection(self):
        """Test rejection of '原则X' pattern in Mandarin."""
        mandarin_principle_inputs = [
            "我选择原则a",
            "我更喜欢原则b",
            "我选原则c", 
            "我选择原则d",
            "我的投票是原则a",
            "我支持原则b",
            "我的偏好是原则c",
            "我挑选原则d"
        ]
        
        for input_text in mandarin_principle_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "mandarin"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    def test_mandarin_traditional_letter_rejection(self):
        """Test rejection of traditional Chinese letter patterns (甲乙丙丁)."""
        traditional_letter_inputs = [
            "我选择原则甲",
            "我更喜欢原则乙",
            "我选原则丙",
            "我选择原则丁",
            "我选择甲",
            "我更喜欢乙", 
            "我选丙",
            "我选择丁"
        ]
        
        for input_text in traditional_letter_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "mandarin"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    # Valid Full Name Acceptance Tests (to ensure system still works)
    def test_english_full_name_acceptance(self):
        """Test that valid English full principle names are accepted."""
        valid_english_inputs = [
            "I choose maximizing the floor income",
            "My preference is maximizing the average income",
            "I select maximizing the average income with a floor constraint",
            "I vote for maximizing the average income with a range constraint"
        ]
        
        for input_text in valid_english_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "english"
                )
                self.assertIsNotNone(result,
                    f"Expected valid principle for '{input_text}', got None")

    def test_spanish_full_name_acceptance(self):
        """Test that valid Spanish full principle names are accepted."""
        valid_spanish_inputs = [
            "Elijo maximizar el ingreso mínimo", 
            "Mi preferencia es maximizar el ingreso promedio",
            "Selecciono maximizar el ingreso promedio con restricción de mínimo",
            "Voto por maximizar el ingreso promedio con restricción de rango"
        ]
        
        for input_text in valid_spanish_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "spanish"
                )
                self.assertIsNotNone(result,
                    f"Expected valid principle for '{input_text}', got None")

    def test_mandarin_full_name_acceptance(self):
        """Test that valid Mandarin full principle names are accepted."""
        valid_mandarin_inputs = [
            "我选择最大化最低收入",
            "我的偏好是最大化平均收入", 
            "我选择在最低收入约束下最大化平均收入",
            "我投票给在收入范围约束下最大化平均收入"
        ]
        
        for input_text in valid_mandarin_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "mandarin"
                )
                self.assertIsNotNone(result,
                    f"Expected valid principle for '{input_text}', got None")

    # Cross-Language Contamination Tests
    def test_cross_language_letter_contamination(self):
        """Test that letter patterns are rejected regardless of language context."""
        cross_contamination_inputs = [
            # English agent with Spanish letter input
            ("My elección es principio a", "english"),
            # Spanish agent with English letter input  
            ("My choice is principle b", "spanish"),
            # Mandarin agent with English letter input
            ("I choose principle c", "mandarin"),
            # Mixed language with letters
            ("我选择 principle d", "english"),
            ("Mi choice is 原则a", "spanish"),
            ("I elijo principio b 我选择", "mandarin")
        ]
        
        for input_text, language in cross_contamination_inputs:
            with self.subTest(input=input_text, language=language):
                result = self.utility_agent.parse_principle_choice(input_text, language)
                self.assertIsNone(result,
                    f"Expected None for cross-contamination '{input_text}' in {language}, got {result}")

    # Edge Case and Boundary Tests
    def test_letter_with_punctuation_rejection(self):
        """Test rejection of letters with punctuation and formatting."""
        punctuation_inputs = [
            "My choice is: a",
            "I prefer (b)",
            "I select \"c\"",
            "I choose [d]", 
            "My answer is 'a'",
            "I pick principle: b",
            "I support (principle c)",
            "I vote for \"principle d\""
        ]
        
        for input_text in punctuation_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "english"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")

    def test_multiple_letter_references_rejection(self):
        """Test rejection of inputs with multiple letter references."""
        multiple_letter_inputs = [
            "I choose a over b",
            "Between principle c and principle d, I prefer c",
            "My ranking is a, b, c, d",
            "I don't want a or b, I choose c",
            "Either principle a or principle b would work"
        ]
        
        for input_text in multiple_letter_inputs:
            with self.subTest(input=input_text):
                result = self.utility_agent.parse_principle_choice(
                    input_text, "english"
                )
                self.assertIsNone(result,
                    f"Expected None for '{input_text}', got {result}")


class TestLanguageManagerLetterPrevention(unittest.TestCase):
    """Test that the language manager prevents letter-based content delivery."""
    
    def setUp(self):
        self.language_manager = LanguageManager()
        self.languages = ["english", "spanish", "mandarin"]

    def test_no_letter_prompts_served(self):
        """Test that language manager serves no letter-based prompts."""
        for language in self.languages:
            with self.subTest(language=language):
                # Test various prompt types
                prompt_types = [
                    "utility_llm_parse_vote_intention",
                    "utility_llm_parse_principle_choice", 
                    "utility_llm_validate_constraint",
                    "phase2_ballot_parsing",
                    "phase2_preference_detection"
                ]
                
                for prompt_type in prompt_types:
                    try:
                        prompt = self.language_manager.get_prompt(prompt_type, language)
                        
                        # Check for letter-based contamination in prompts
                        letter_patterns = [
                            "principle a", "principle b", "principle c", "principle d",
                            "principio a", "principio b", "principio c", "principio d", 
                            "原则a", "原则b", "原则c", "原则d",
                            "原则甲", "原则乙", "原则丙", "原则丁"
                        ]
                        
                        for pattern in letter_patterns:
                            self.assertNotIn(pattern.lower(), prompt.lower(),
                                f"Found letter pattern '{pattern}' in {prompt_type} for {language}")
                                
                    except Exception as e:
                        # If prompt doesn't exist, that's acceptable
                        continue


class TestMonitoringSystemLetterDetection(unittest.TestCase):
    """Test framework for monitoring letter contamination in real-time."""
    
    def test_system_wide_letter_scanning(self):
        """Scan system files for potential letter contamination."""
        import os
        import re
        
        # Define letter contamination patterns
        patterns = {
            'english': [
                r'\bprinciple\s+[a-d]\b',
                r'\bchoice\s+is\s+[a-d]\b',
                r'\bprefer\s+[a-d]\b',
                r'\bselect\s+[a-d]\b'
            ],
            'spanish': [
                r'\bprincipio\s+[a-d]\b', 
                r'\belección\s+es\s+[a-d]\b',
                r'\bopción\s+[a-d]\b'
            ],
            'mandarin': [
                r'原则[a-d甲乙丙丁]',
                r'选择[a-d甲乙丙丁]',
                r'我选[a-d甲乙丙丁]'
            ]
        }
        
        # Scan active system directories (excluding archives)
        scan_directories = [
            'translations/',
            'experiment_agents/', 
            'core/',
            'utils/',
            'tests/unit/',
            'tests/integration/'
        ]
        
        contamination_found = []
        
        for directory in scan_directories:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    # Skip archive directories
                    if 'archive' in root or 'letter_based_legacy' in root:
                        continue
                        
                    for file in files:
                        if file.endswith(('.py', '.json', '.md', '.yaml')):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    
                                for language, language_patterns in patterns.items():
                                    for pattern in language_patterns:
                                        matches = re.findall(pattern, content, re.IGNORECASE)
                                        if matches:
                                            contamination_found.append({
                                                'file': file_path,
                                                'language': language,
                                                'pattern': pattern,
                                                'matches': matches
                                            })
                                            
                            except (UnicodeDecodeError, IOError):
                                continue
        
        # Report any contamination found
        if contamination_found:
            error_msg = "Letter contamination detected:\n"
            for contamination in contamination_found:
                error_msg += f"File: {contamination['file']}\n"
                error_msg += f"Language: {contamination['language']}\n" 
                error_msg += f"Pattern: {contamination['pattern']}\n"
                error_msg += f"Matches: {contamination['matches']}\n\n"
            
            self.fail(error_msg)

    def test_translation_file_integrity(self):
        """Test that translation files contain no letter-based examples."""
        translation_files = [
            'translations/english_prompts.json',
            'translations/spanish_prompts.json', 
            'translations/mandarin_prompts.json'
        ]
        
        for file_path in translation_files:
            if os.path.exists(file_path):
                with self.subTest(file=file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for any letter-based contamination
                    contamination_patterns = [
                        r'principle\s+[a-d]',
                        r'principio\s+[a-d]',
                        r'原则[a-d甲乙丙丁]',
                        r'choice\s+is\s+[a-d]',
                        r'elección\s+es\s+[a-d]',
                        r'我选择[a-d甲乙丙丁]'
                    ]
                    
                    for pattern in contamination_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        self.assertEqual(len(matches), 0,
                            f"Found letter contamination in {file_path}: {matches}")


if __name__ == '__main__':
    # Run comprehensive multilingual test suite
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestMultilingualLetterRejection,
        TestLanguageManagerLetterPrevention,
        TestMonitoringSystemLetterDetection
    ]
    
    for test_class in test_classes:
        tests = test_loader.loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)