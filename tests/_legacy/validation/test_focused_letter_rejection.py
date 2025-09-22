"""
Focused test for cross-language letter rejection validation.
Simplified version for Phase 3 implementation.
"""

import asyncio
import unittest
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from experiment_agents.utility_agent import UtilityAgent


class TestFocusedLetterRejection(unittest.TestCase):
    """Focused test for letter rejection across all languages."""
    
    def setUp(self):
        """Set up test environment."""
        self.utility_agent = UtilityAgent()

    def test_cross_language_contamination_sync(self):
        """Test cross-language contamination using sync approach."""
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
        
        async def run_test():
            for input_text, language in cross_contamination_inputs:
                with self.subTest(input=input_text, language=language):
                    result = await self.utility_agent.parse_principle_choice_llm(input_text)
                    self.assertIsNone(result,
                        f"Expected None for cross-contamination '{input_text}' in {language}, got {result}")
        
        # Run the async test
        asyncio.run(run_test())

    def test_english_letter_patterns_sync(self):
        """Test English letter patterns using sync approach."""
        english_patterns = [
            "My choice is a",
            "I prefer b",
            "My choice is principle c", 
            "I support principle d",
            "My answer is A",
            "I pick B"
        ]
        
        async def run_test():
            for input_text in english_patterns:
                with self.subTest(input=input_text):
                    result = await self.utility_agent.parse_principle_choice_llm(input_text)
                    self.assertIsNone(result,
                        f"Expected None for '{input_text}', got {result}")
        
        asyncio.run(run_test())

    def test_spanish_letter_patterns_sync(self):
        """Test Spanish letter patterns using sync approach."""
        spanish_patterns = [
            "Mi elección es a",
            "Prefiero b", 
            "Mi elección es principio c",
            "Apoyo principio d",
            "Mi opción es a",
            "Escojo b"
        ]
        
        async def run_test():
            for input_text in spanish_patterns:
                with self.subTest(input=input_text):
                    result = await self.utility_agent.parse_principle_choice_llm(input_text)
                    self.assertIsNone(result,
                        f"Expected None for '{input_text}', got {result}")
        
        asyncio.run(run_test())

    def test_mandarin_letter_patterns_sync(self):
        """Test Mandarin letter patterns using sync approach."""
        mandarin_patterns = [
            "我选择a",
            "我更喜欢b",
            "我选择原则c", 
            "我支持原则d",
            "我选择甲",
            "我更喜欢乙"
        ]
        
        async def run_test():
            for input_text in mandarin_patterns:
                with self.subTest(input=input_text):
                    result = await self.utility_agent.parse_principle_choice_llm(input_text)
                    self.assertIsNone(result,
                        f"Expected None for '{input_text}', got {result}")
        
        asyncio.run(run_test())

    def test_valid_full_names_still_work_sync(self):
        """Test that valid full principle names are still properly parsed."""
        valid_responses = {
            'english': [
                "I choose maximizing the floor income",
                "My preference is maximizing the average income"
            ],
            'spanish': [
                "Elijo maximizar el ingreso mínimo",
                "Mi preferencia es maximizar el ingreso promedio"
            ],
            'mandarin': [
                "我选择最大化最低收入",
                "我的偏好是最大化平均收入"
            ]
        }
        
        async def run_test():
            for language, responses in valid_responses.items():
                for response in responses:
                    with self.subTest(response=response, language=language):
                        result = await self.utility_agent.parse_principle_choice_llm(response)
                        self.assertIsNotNone(result,
                            f"Valid full name rejected in {language}: {response}")
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main(verbosity=2)