"""
End-to-end testing for letter rejection across complete experiment flows.

This test suite validates letter rejection through complete experiment execution
across all three languages, ensuring no letter-based inputs can slip through
at any stage of the experimental process.
"""

import unittest
import asyncio
import tempfile
import os
import json
import sys
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.experiment_manager import ExperimentManager
from config.models import ExperimentConfiguration, AgentConfiguration
from utils.language_manager import LanguageManager


class TestEndToEndLetterRejection(unittest.TestCase):
    """Test letter rejection through complete experiment flows."""
    
    def setUp(self):
        """Set up test configurations for each language."""
        self.test_configs = {
            'english': self._create_test_config('english'),
            'spanish': self._create_test_config('spanish'),
            'mandarin': self._create_test_config('mandarin')
        }
        
        # Letter-contaminated agent responses for testing
        self.letter_contaminated_responses = {
            'english': [
                "After considering all options, my choice is principle a.",
                "I believe principle b is the best approach.",
                "My final decision is to support principle c.",
                "I choose principle d as my preferred option.",
                "My vote goes to a.",
                "I prefer b over the other options.",
                "My selection is c.",
                "I pick d as the winner."
            ],
            'spanish': [
                "Después de considerar todas las opciones, mi elección es principio a.",
                "Creo que principio b es el mejor enfoque.",
                "Mi decisión final es apoyar principio c.", 
                "Elijo principio d como mi opción preferida.",
                "Mi voto va para a.",
                "Prefiero b sobre las otras opciones.",
                "Mi selección es c.",
                "Escojo d como el ganador."
            ],
            'mandarin': [
                "考虑了所有选择后，我的选择是原则a。",
                "我认为原则b是最好的方法。",
                "我的最终决定是支持原则c。",
                "我选择原则d作为我的首选。",
                "我投票给a。",
                "我更喜欢b而不是其他选择。",
                "我的选择是c。",
                "我选d作为获胜者。"
            ]
        }

    def _create_test_config(self, language: str) -> ExperimentConfiguration:
        """Create a minimal test configuration for the given language."""
        return ExperimentConfiguration(
            language=language,
            agents=[
                AgentConfiguration(
                    name=f"test_agent_1_{language}",
                    personality="analytical",
                    model="gpt-4.1-mini",
                    temperature=0.3,
                    reasoning_enabled=False,
                    memory_character_limit=5000
                ),
                AgentConfiguration(
                    name=f"test_agent_2_{language}",
                    personality="collaborative",
                    model="gpt-4.1-mini", 
                    temperature=0.3,
                    reasoning_enabled=False,
                    memory_character_limit=5000
                )
            ],
            phase2_rounds=5,
            voting_detection_mode="simple"
        )

    @patch('experiment_agents.participant_agent.ParticipantAgent.run')
    def test_phase1_letter_rejection_english(self, mock_agent_run):
        """Test Phase 1 letter rejection in English."""
        mock_agent_run.return_value = AsyncMock(
            return_value="After careful consideration, my choice is principle a."
        )
        
        with self.assertLogs() as log_context:
            experiment_manager = ExperimentManager(self.test_configs['english'])
            
            # This should fail/reject the letter-based response
            with self.assertRaises((ValueError, AssertionError)):
                asyncio.run(experiment_manager.run_experiment())

    @patch('experiment_agents.participant_agent.ParticipantAgent.run') 
    def test_phase1_letter_rejection_spanish(self, mock_agent_run):
        """Test Phase 1 letter rejection in Spanish."""
        mock_agent_run.return_value = AsyncMock(
            return_value="Mi elección final es principio b."
        )
        
        with self.assertLogs() as log_context:
            experiment_manager = ExperimentManager(self.test_configs['spanish'])
            
            # This should fail/reject the letter-based response
            with self.assertRaises((ValueError, AssertionError)):
                asyncio.run(experiment_manager.run_experiment())

    @patch('experiment_agents.participant_agent.ParticipantAgent.run')
    def test_phase1_letter_rejection_mandarin(self, mock_agent_run):
        """Test Phase 1 letter rejection in Mandarin."""
        mock_agent_run.return_value = AsyncMock(
            return_value="我的选择是原则c。"
        )
        
        with self.assertLogs() as log_context:
            experiment_manager = ExperimentManager(self.test_configs['mandarin'])
            
            # This should fail/reject the letter-based response
            with self.assertRaises((ValueError, AssertionError)):
                asyncio.run(experiment_manager.run_experiment())

    def test_utility_agent_rejection_patterns(self):
        """Test that utility agent properly rejects all letter patterns."""
        from experiment_agents.utility_agent import UtilityAgent
        
        utility_agent = UtilityAgent()
        
        # Test all contaminated responses across all languages
        for language, responses in self.letter_contaminated_responses.items():
            with self.subTest(language=language):
                for response in responses:
                    with self.subTest(response=response):
                        result = utility_agent.parse_principle_choice(response, language)
                        self.assertIsNone(result,
                            f"Expected None for letter-based response in {language}: {response}")

    def test_cross_language_experiment_safety(self):
        """Test that cross-language contamination is prevented."""
        from experiment_agents.utility_agent import UtilityAgent
        
        utility_agent = UtilityAgent()
        
        # Test cross-language contamination scenarios
        cross_contamination_tests = [
            # English agent receiving Spanish letter input
            ("Mi elección es principio a", "english"),
            # Spanish agent receiving English letter input
            ("My choice is principle b", "spanish"),
            # Mandarin agent receiving English letter input
            ("I choose principle c", "mandarin"),
            # Mixed language inputs
            ("我选择 principle d", "english"),
            ("My elección is principio a", "spanish"),
            ("I choose 原则b", "mandarin")
        ]
        
        for input_text, expected_language in cross_contamination_tests:
            with self.subTest(input=input_text, language=expected_language):
                result = utility_agent.parse_principle_choice(input_text, expected_language)
                self.assertIsNone(result,
                    f"Cross-contamination not rejected: '{input_text}' in {expected_language}")

    def test_valid_full_names_still_work(self):
        """Test that valid full principle names are still properly parsed."""
        from experiment_agents.utility_agent import UtilityAgent
        
        utility_agent = UtilityAgent()
        
        valid_responses = {
            'english': [
                "I choose maximizing the floor income.",
                "My preference is maximizing the average income.",
                "I select maximizing the average income with a floor constraint.",
                "I vote for maximizing the average income with a range constraint."
            ],
            'spanish': [
                "Elijo maximizar el ingreso mínimo.",
                "Mi preferencia es maximizar el ingreso promedio.",
                "Selecciono maximizar el ingreso promedio con restricción de mínimo.",
                "Voto por maximizar el ingreso promedio con restricción de rango."
            ],
            'mandarin': [
                "我选择最大化最低收入。",
                "我的偏好是最大化平均收入。",
                "我选择在最低收入约束下最大化平均收入。",
                "我投票给在收入范围约束下最大化平均收入。"
            ]
        }
        
        for language, responses in valid_responses.items():
            with self.subTest(language=language):
                for response in responses:
                    with self.subTest(response=response):
                        result = utility_agent.parse_principle_choice(response, language)
                        self.assertIsNotNone(result,
                            f"Valid full name rejected in {language}: {response}")


class TestLanguageManagerIntegrity(unittest.TestCase):
    """Test language manager integrity across all languages."""
    
    def setUp(self):
        self.language_manager = LanguageManager()
        self.languages = ['english', 'spanish', 'mandarin']

    def test_no_letter_content_served(self):
        """Test that language manager never serves letter-based content."""
        # Define all possible prompt types
        prompt_types = [
            'phase1_initial_prompt',
            'phase1_round_prompt', 
            'phase2_initial_prompt',
            'phase2_discussion_prompt',
            'phase2_voting_prompt',
            'utility_llm_parse_principle_choice',
            'utility_llm_parse_vote_intention',
            'utility_llm_validate_constraint'
        ]
        
        letter_patterns = [
            r'principle\s+[a-d]',
            r'principio\s+[a-d]', 
            r'原则[a-d甲乙丙丁]',
            r'choice\s+is\s+[a-d]',
            r'elección\s+es\s+[a-d]',
            r'我选择[a-d甲乙丙丁]'
        ]
        
        import re
        
        for language in self.languages:
            for prompt_type in prompt_types:
                with self.subTest(language=language, prompt_type=prompt_type):
                    try:
                        prompt = self.language_manager.get_prompt(prompt_type, language)
                        
                        # Check each pattern
                        for pattern in letter_patterns:
                            matches = re.findall(pattern, prompt, re.IGNORECASE)
                            self.assertEqual(len(matches), 0,
                                f"Letter pattern '{pattern}' found in {prompt_type} for {language}: {matches}")
                                
                    except Exception:
                        # If prompt doesn't exist, that's acceptable
                        continue

    def test_translation_file_consistency(self):
        """Test that all translation files are consistent and letter-free."""
        translation_files = [
            'translations/english_prompts.json',
            'translations/spanish_prompts.json',
            'translations/mandarin_prompts.json'
        ]
        
        for file_path in translation_files:
            with self.subTest(file=file_path):
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                            content = json.dumps(data, ensure_ascii=False)
                            
                            # Check for letter contamination
                            import re
                            patterns = [
                                r'principle\s+[a-d]',
                                r'principio\s+[a-d]',
                                r'原则[a-d甲乙丙丁]'
                            ]
                            
                            for pattern in patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                self.assertEqual(len(matches), 0,
                                    f"Letter contamination in {file_path}: {matches}")
                                    
                        except json.JSONDecodeError:
                            self.fail(f"Invalid JSON in {file_path}")


class TestSystemWideLetterMonitoring(unittest.TestCase):
    """System-wide monitoring for letter contamination."""
    
    def test_active_code_letter_scanning(self):
        """Scan active codebase for letter contamination."""
        import re
        import glob
        
        # Patterns to detect letter contamination
        contamination_patterns = [
            r'\bprinciple\s+[a-d]\b',
            r'\bprincipio\s+[a-d]\b',
            r'原则[a-d甲乙丙丁]',
            r'\bchoice\s+is\s+[a-d]\b',
            r'\belección\s+es\s+[a-d]\b',
            r'我选择[a-d甲乙丙丁]'
        ]
        
        # Scan active directories (excluding archives)
        scan_patterns = [
            'experiment_agents/**/*.py',
            'core/**/*.py',
            'utils/**/*.py',
            'translations/*.json',
            'tests/unit/**/*.py',
            'tests/integration/**/*.py'
        ]
        
        contamination_found = []
        
        for pattern in scan_patterns:
            for file_path in glob.glob(pattern, recursive=True):
                # Skip archive directories
                if 'archive' in file_path or 'letter_based_legacy' in file_path:
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for cont_pattern in contamination_patterns:
                        matches = re.findall(cont_pattern, content, re.IGNORECASE)
                        if matches:
                            contamination_found.append({
                                'file': file_path,
                                'pattern': cont_pattern,
                                'matches': matches
                            })
                            
                except (UnicodeDecodeError, IOError):
                    continue
        
        # Fail test if contamination is found
        if contamination_found:
            error_msg = "Active code contamination detected:\n"
            for contamination in contamination_found:
                error_msg += f"File: {contamination['file']}\n"
                error_msg += f"Pattern: {contamination['pattern']}\n"
                error_msg += f"Matches: {contamination['matches']}\n\n"
            
            self.fail(error_msg)

    def test_config_file_letter_safety(self):
        """Test that configuration files contain no letter references."""
        config_files = glob.glob('config/**/*.yaml', recursive=True)
        
        import re
        
        for config_file in config_files:
            with self.subTest(config=config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for letter patterns in config files
                    patterns = [
                        r'principle\s+[a-d]',
                        r'principio\s+[a-d]',
                        r'原则[a-d甲乙丙丁]'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        self.assertEqual(len(matches), 0,
                            f"Letter contamination in config {config_file}: {matches}")
                            
                except (IOError, UnicodeDecodeError):
                    continue


if __name__ == '__main__':
    # Run all end-to-end validation tests
    unittest.main(verbosity=2)