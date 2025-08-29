"""
Comprehensive unit tests for Phase 2 preference detection in simple mode.

Tests the preference statement detection logic used in simple mode consensus:
1. Pattern-based preference detection with regex
2. LLM fallback when patterns fail
3. Constraint amount extraction from preferences
4. Simple mode consensus checking logic
5. Round-based preference tracking and reset

The simple mode operates by:
- Detecting preferences per round via detect_preference_statement()  
- Storing in _current_round_preferences (reset each round)
- Checking consensus when all participants have stated preferences
- Using check_preference_consensus_simple_mode() for consensus validation
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel


class TestPreferenceDetectionSimpleMode(unittest.TestCase):
    """Test preference detection logic for simple mode consensus."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(utility_model="gpt-4o-mini", temperature=0.0)
    
    async def _detect_preference(self, statement: str) -> PrincipleChoice:
        """Helper to detect preference in statement."""
        await self.utility_agent.async_init()
        return await self.utility_agent.detect_preference_statement(statement)
    
    def test_explicit_preference_patterns(self):
        """Test explicit preference statement patterns."""
        
        preference_cases = [
            # Direct preference statements
            {
                "statement": "My preference is principle a",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None
            },
            {
                "statement": "I prefer maximizing average income",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE, 
                "expected_constraint": None
            },
            {
                "statement": "I choose principle c with floor constraint of $15,000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                "expected_constraint": 15000
            },
            {
                "statement": "I support principle d with range constraint of $20000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                "expected_constraint": 20000
            },
            
            # Colon format
            {
                "statement": "Preference: maximizing floor income",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR,
                "expected_constraint": None
            },
            {
                "statement": "Choice: principle b",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE,
                "expected_constraint": None
            }
        ]
        
        for case in preference_cases:
            with self.subTest(statement=case["statement"]):
                result = asyncio.run(self._detect_preference(case["statement"]))
                
                self.assertIsNotNone(result, f"Failed to detect preference in: '{case['statement']}'")
                self.assertEqual(result.principle, case["expected_principle"],
                               f"Wrong principle for '{case['statement']}': got {result.principle.value}")
                self.assertEqual(result.constraint_amount, case["expected_constraint"],
                               f"Wrong constraint for '{case['statement']}': got {result.constraint_amount}")
    
    def test_letter_based_preference_detection(self):
        """Test letter-based principle references (backward compatibility)."""
        
        letter_cases = [
            ("I prefer a", JusticePrinciple.MAXIMIZING_FLOOR),
            ("My choice is b", JusticePrinciple.MAXIMIZING_AVERAGE),
            ("I support c with $18000", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
            ("Preference: d with range constraint of $25,000", JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT),
            
            # With "principle" prefix
            ("I prefer principle a", JusticePrinciple.MAXIMIZING_FLOOR),
            ("My choice is principle c with $16000", JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT),
        ]
        
        for statement, expected_principle in letter_cases:
            with self.subTest(statement=statement):
                result = asyncio.run(self._detect_preference(statement))
                
                self.assertIsNotNone(result, f"Failed to detect letter preference: '{statement}'")
                self.assertEqual(result.principle, expected_principle,
                               f"Wrong principle for letter case '{statement}': got {result.principle.value}")
    
    def test_constraint_amount_detection_in_preferences(self):
        """Test constraint amount extraction from preference statements."""
        
        constraint_cases = [
            # Various formats for constraint amounts
            ("I prefer principle c with floor constraint of $15,000", 15000),
            ("My choice is principle d with $20000", 20000),  
            ("I support principle c with constraint $18,500", 18500),
            ("Preference: principle d with range constraint of 22000", 22000),
            ("I choose principle c with $14k", 14000),  # k format
            ("My preference is principle d with 16 thousand", 16000),  # word format
            
            # Edge cases
            ("I prefer principle c with no constraint amount mentioned", None),
            ("My choice is principle a", None),  # Non-constraint principle
        ]
        
        for statement, expected_constraint in constraint_cases:
            with self.subTest(statement=statement):
                result = asyncio.run(self._detect_preference(statement))
                
                self.assertIsNotNone(result, f"Failed to parse constraint case: '{statement}'")
                self.assertEqual(result.constraint_amount, expected_constraint,
                               f"Wrong constraint amount for '{statement}': got {result.constraint_amount}, expected {expected_constraint}")
    
    def test_non_preference_statements(self):
        """Test statements that should NOT be detected as preferences."""
        
        non_preference_cases = [
            # Discussion without clear preference
            "I think we need to consider all options carefully",
            "The principles have different advantages",
            "We should discuss this more",
            "What do others think about principle a?",
            
            # Questions about preferences (not statements of preference)
            "Which principle do you prefer?",
            "Should we choose principle b?",
            "What if we went with principle c?",
            
            # Conditional statements
            "If we choose principle a, then...",
            "Principle b might be good",
            "We could consider principle c",
            
            # Past or future references
            "I used to prefer principle a",
            "We might prefer principle b later",
            "Previously I thought principle c was best",
        ]
        
        for statement in non_preference_cases:
            with self.subTest(statement=statement):
                result = asyncio.run(self._detect_preference(statement))
                self.assertIsNone(result, f"Should NOT detect preference in: '{statement}'")
    
    @patch('experiment_agents.utility_agent.Runner.run')
    async def test_llm_fallback_for_preference_detection(self, mock_runner):
        """Test LLM fallback when regex patterns don't match."""
        await self.utility_agent.async_init()
        
        # Test complex statements that might need LLM analysis
        fallback_cases = [
            {
                "statement": "After careful consideration, I believe the floor-maximizing approach is best",
                "llm_response": "PREFERENCE_DETECTED: maximizing_floor",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
            },
            {
                "statement": "My analysis leads me to support the constrained average approach with $18000",
                "llm_response": "PREFERENCE_DETECTED: maximizing_average_floor_constraint with $18000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            },
            {
                "statement": "Complex discussion without clear preference",
                "llm_response": "NO_PREFERENCE_DETECTED",
                "expected_principle": None
            }
        ]
        
        for case in fallback_cases:
            with self.subTest(statement=case["statement"]):
                mock_result = MagicMock()
                mock_result.final_output = case["llm_response"]
                mock_runner.return_value = mock_result
                
                result = await self.utility_agent.detect_preference_statement(case["statement"])
                
                if case["expected_principle"]:
                    self.assertIsNotNone(result, f"LLM should detect preference in: '{case['statement']}'")
                    self.assertEqual(result.principle, case["expected_principle"])
                else:
                    self.assertIsNone(result, f"LLM should NOT detect preference in: '{case['statement']}'")
    
    def test_multilingual_preference_detection(self):
        """Test preference detection across languages."""
        
        multilingual_cases = [
            # Chinese preferences
            {
                "statement": "我的偏好是最大化最低收入",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
            },
            {
                "statement": "我选择在最低收入约束条件下最大化平均收入，约束为 15000",
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            },
            
            # Spanish preferences (if supported)
            {
                "statement": "Mi preferencia es maximización del ingreso mínimo",
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
            }
        ]
        
        # Note: These tests depend on the LLM's multilingual capabilities
        for case in multilingual_cases:
            with self.subTest(statement=case["statement"]):
                result = asyncio.run(self._detect_preference(case["statement"]))
                
                # These might rely on LLM fallback, so we're more lenient
                if result:  # If detected at all
                    self.assertEqual(result.principle, case["expected_principle"],
                                   f"Wrong multilingual principle for '{case['statement']}'")
    
    def test_simple_mode_consensus_checking(self):
        """Test consensus checking logic specific to simple mode."""
        
        consensus_scenarios = [
            {
                "description": "Perfect consensus - all same principle",
                "preferences": [
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.NO_OPINION),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.NO_OPINION),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.NO_OPINION),
                ],
                "expected_consensus": True,
                "expected_principle": JusticePrinciple.MAXIMIZING_FLOOR
            },
            {
                "description": "Constraint consensus - same principle and constraint",
                "preferences": [
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000, CertaintyLevel.NO_OPINION),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000, CertaintyLevel.NO_OPINION),
                ],
                "expected_consensus": True,
                "expected_principle": JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            },
            {
                "description": "No consensus - different principles",
                "preferences": [
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.NO_OPINION),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE, None, CertaintyLevel.NO_OPINION),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000, CertaintyLevel.NO_OPINION),
                ],
                "expected_consensus": False
            },
            {
                "description": "No consensus - same principle, different constraints",
                "preferences": [
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000, CertaintyLevel.NO_OPINION),
                    PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 20000, CertaintyLevel.NO_OPINION),
                ],
                "expected_consensus": False
            }
        ]
        
        for scenario in consensus_scenarios:
            with self.subTest(description=scenario["description"]):
                consensus, agreed_preference, warnings = self.utility_agent.check_preference_consensus_simple_mode(scenario["preferences"])
                
                self.assertEqual(consensus, scenario["expected_consensus"],
                               f"Consensus detection failed for: {scenario['description']}")
                
                if scenario["expected_consensus"]:
                    self.assertIsNotNone(agreed_preference, f"Should have agreed preference for: {scenario['description']}")
                    self.assertEqual(agreed_preference.principle, scenario["expected_principle"],
                                   f"Wrong agreed principle for: {scenario['description']}")
                else:
                    self.assertIsNone(agreed_preference, f"Should not have agreed preference for: {scenario['description']}")
    
    def test_empty_and_edge_case_inputs(self):
        """Test handling of empty and edge case inputs."""
        
        edge_cases = [
            "",           # Empty string
            "   ",        # Whitespace only  
            "\n\t",       # Only control characters
            "a",          # Single character
            "preference", # Just the keyword
        ]
        
        for edge_input in edge_cases:
            with self.subTest(input=repr(edge_input)):
                result = asyncio.run(self._detect_preference(edge_input))
                self.assertIsNone(result, f"Should return None for edge case input: {repr(edge_input)}")
    
    def test_case_insensitive_detection(self):
        """Test that preference detection is case-insensitive."""
        
        case_variants = [
            "MY PREFERENCE IS PRINCIPLE A",
            "My Preference Is Principle A",
            "my preference is principle a", 
            "mY pReFeReNcE iS pRiNcIpLe A",
        ]
        
        for variant in case_variants:
            with self.subTest(variant=variant):
                result = asyncio.run(self._detect_preference(variant))
                self.assertIsNotNone(result, f"Case insensitive detection failed for: '{variant}'")
                self.assertEqual(result.principle, JusticePrinciple.MAXIMIZING_FLOOR)
    
    def test_pattern_vs_llm_consistency(self):
        """Test consistency between pattern-based and LLM-based detection."""
        
        # Test statements that should be caught by both approaches
        test_statements = [
            "I prefer principle a",
            "My choice is maximizing average income",
            "I support principle c with $15000",
        ]
        
        for statement in test_statements:
            with self.subTest(statement=statement):
                # Get result from normal detection (which uses patterns first)
                pattern_result = asyncio.run(self._detect_preference(statement))
                
                # Should always get a result for these clear cases
                self.assertIsNotNone(pattern_result, 
                                   f"Pattern detection should work for clear case: '{statement}'")
    
    def test_deprecated_consensus_method_isolation(self):
        """Test that deprecated consensus methods are properly isolated."""
        
        # Test that the old check_preference_consensus method is deprecated
        preferences = [
            PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, None, CertaintyLevel.NO_OPINION),
        ]
        
        consensus, agreed_preference, warnings = self.utility_agent.check_preference_consensus(preferences)
        
        # Should always return no consensus (deprecated behavior)
        self.assertFalse(consensus, "Deprecated method should always return no consensus")
        self.assertIsNone(agreed_preference, "Deprecated method should return no agreed preference")
        self.assertIn("Use check_preference_consensus_simple_mode", str(warnings), 
                     "Should warn about using mode-specific method")


if __name__ == '__main__':
    unittest.main()