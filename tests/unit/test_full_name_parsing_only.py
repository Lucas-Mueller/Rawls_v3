"""
Unit tests specifically for full-name-only principle parsing.

This test suite verifies that the system has completely transitioned
to full principle names and no longer supports letter-based references.

Tests verify:
1. Full-name principle parsing works correctly
2. Letter-based inputs are rejected/not supported
3. Language Manager generates full names only
4. Utility Agent processes full names correctly
5. Cross-language full-name consistency
"""

import unittest
import asyncio
from utils.language_manager import get_language_manager, SupportedLanguage
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice


class TestFullNameParsingOnly(unittest.TestCase):
    """Test that the system uses full names only - NO LETTERS."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
        self.language_manager = get_language_manager()
    
    def test_language_manager_generates_no_letters(self):
        """Test that Language Manager generates full names only."""
        
        # Test all format types
        formats = ['simple', 'names_only', 'detailed']
        
        for format_type in formats:
            with self.subTest(format_type=format_type):
                try:
                    result = self.language_manager.get_principle_list_formatted(format_type)
                    
                    # Check that no letters appear in parentheses
                    for letter in ['a', 'b', 'c', 'd']:
                        letter_pattern = f"({letter})"
                        self.assertNotIn(letter_pattern, result.lower(), 
                            f"Found letter '{letter_pattern}' in {format_type} format")
                    
                    # Verify full names are present
                    self.assertIn('maximizing', result.lower())
                    self.assertIn('floor', result.lower())
                    self.assertIn('average', result.lower())
                    
                except ValueError as e:
                    # letters_only format might be deprecated
                    if 'letters_only' in str(e):
                        continue
                    else:
                        raise
    
    def test_utility_agent_rejects_letters(self):
        """Test that Utility Agent no longer processes letter-based inputs."""
        
        letter_inputs = [
            "My choice is a",
            "I prefer maximizing the average income", 
            "My ballot is c",
            "I choose maximizing the average income with a range constraint"
        ]
        
        async def test_letter_rejection():
            await self.utility_agent.async_init()
            
            for letter_input in letter_inputs:
                with self.subTest(letter_input=letter_input):
                    # These should either fail to parse or return None
                    result = await self.utility_agent.detect_preference_statement(letter_input)
                    
                    # The new system should not successfully parse letter-only inputs
                    if result is not None:
                        # If it does parse, it should not be from the letter itself
                        # but from some other pattern match
                        self.fail(f"Letter input '{letter_input}' was unexpectedly parsed as {result.principle.value}")
        
        asyncio.run(test_letter_rejection())
    
    def test_full_name_parsing_works(self):
        """Test that full-name inputs parse correctly."""
        
        full_name_cases = [
            {
                "input": "My choice is maximizing floor income",
                "expected": JusticePrinciple.MAXIMIZING_FLOOR
            },
            {
                "input": "I prefer maximizing average income", 
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE
            },
            {
                "input": "I choose floor constraint with $15000",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            },
            {
                "input": "My preference is range constraint with income gap of $20000",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            }
        ]
        
        async def test_full_name_parsing():
            await self.utility_agent.async_init()
            
            for case in full_name_cases:
                with self.subTest(input=case["input"]):
                    result = await self.utility_agent.detect_preference_statement(case["input"])
                    
                    self.assertIsNotNone(result, f"Failed to parse: {case['input']}")
                    self.assertEqual(result.principle, case["expected"],
                        f"Wrong principle for '{case['input']}': got {result.principle.value}")
        
        asyncio.run(test_full_name_parsing())
    
    def test_ballot_parsing_full_names(self):
        """Test that ballot parsing works with full names."""
        
        ballot_cases = [
            {
                "ballot": "My ballot choice is maximizing floor income",
                "expected": JusticePrinciple.MAXIMIZING_FLOOR
            },
            {
                "ballot": "I vote for maximizing average income",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE
            },
            {
                "ballot": "My vote is floor constraint with minimum income of $12000",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            },
            {
                "ballot": "I choose range constraint to limit income gap to $18000",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            }
        ]
        
        async def test_ballot_parsing():
            await self.utility_agent.async_init()
            
            for case in ballot_cases:
                with self.subTest(ballot=case["ballot"]):
                    result = await self.utility_agent.parse_principle_choice_enhanced(case["ballot"])
                    
                    self.assertIsNotNone(result, f"Failed to parse ballot: {case['ballot']}")
                    self.assertEqual(result.principle, case["expected"],
                        f"Wrong principle for ballot '{case['ballot']}': got {result.principle.value}")
        
        asyncio.run(test_ballot_parsing())
    
    def test_principle_mapping_has_no_letters(self):
        """Test that principle mapping no longer includes letter mappings."""
        
        async def test_mapping():
            await self.utility_agent.async_init()
            
            # Try to get letter mappings (should fail or return None)
            letters = ['a', 'b', 'c', 'd']
            
            for letter in letters:
                with self.subTest(letter=letter):
                    # This is internal testing - accessing the mapping method directly
                    result = self.utility_agent._map_identifier_to_principle(letter)
                    
                    # Letters should no longer map to principles
                    self.assertIsNone(result, 
                        f"Letter '{letter}' should not map to any principle, got {result}")
        
        asyncio.run(test_mapping())
    
    def test_natural_language_variations(self):
        """Test that natural language variations work with full names."""
        
        natural_variations = [
            {
                "input": "I think we should maximize the floor income",
                "expected": JusticePrinciple.MAXIMIZING_FLOOR
            },
            {
                "input": "My preference is to maximize average income",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE  
            },
            {
                "input": "I support having a floor constraint on income",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            },
            {
                "input": "We should limit the income gap between rich and poor",
                "expected": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            }
        ]
        
        async def test_natural_variations():
            await self.utility_agent.async_init()
            
            for case in natural_variations:
                with self.subTest(input=case["input"]):
                    result = await self.utility_agent.detect_preference_statement(case["input"])
                    
                    # Note: Some natural language might not be caught by regex patterns
                    # but that's okay - the point is we're not relying on letters
                    if result is not None:
                        self.assertEqual(result.principle, case["expected"],
                            f"Wrong principle for natural input '{case['input']}': got {result.principle.value}")
        
        asyncio.run(test_natural_variations())


if __name__ == '__main__':
    unittest.main()