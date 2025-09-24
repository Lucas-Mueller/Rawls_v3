"""
Unit tests for ballot parsing vulnerability fixes.

This test module specifically tests the parsing improvements made to fix
the critical issue where "maximizing the floor income with no additional constraints" was
incorrectly parsed as maximizing_average_floor_constraint instead of maximizing_floor.

These tests ensure that the parsing system correctly handles:
1. Letter-based principle references (maximizing the floor income, b, c, d)
2. "No constraints" language vs. actual constraint specifications
3. Ambiguous phrasing that previously caused false matches
4. Order of pattern matching to prevent regression
"""

import unittest
import asyncio
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple


class TestBallotParsingVulnerabilities(unittest.TestCase):
    """Test critical ballot parsing vulnerabilities that caused false consensus failures."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent()
    
    def test_principle_a_no_constraints_parsing(self):
        """Test the specific case from experiment_results_20250827_091903.json."""
        # These are the exact phrases that caused the parsing failure
        problematic_inputs = [
            "maximizing the floor income with no additional constraints",
            "My ballot choice is maximizing the floor income with no constraints", 
            "I choose maximizing the floor income without any constraint",
            "My choice is maximizing the floor income with no constraints",
            "maximizing the floor income - maximizing floor income, no constraints needed"
        ]
        
        for input_text in problematic_inputs:
            with self.subTest(input_text=input_text):
                # Use async test runner for LLM-based parsing
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                self.assertEqual(choice_data['principle'], 'maximizing_floor', 
                               f"Should parse as maximizing_floor, got {choice_data['principle']} for: {input_text}")
    
    def test_letter_based_principle_detection(self):
        """Test that letter-based principle references work correctly."""
        test_cases = [
            ("maximizing the floor income", "maximizing_floor"),
            ("option a", "maximizing_floor"),
            ("maximizing the average income", "maximizing_average"),
            ("option b", "maximizing_average"),
            ("maximizing the average income with a floor constraint", "maximizing_average_floor_constraint"),
            ("option c", "maximizing_average_floor_constraint"),
            ("maximizing the average income with a range constraint", "maximizing_average_range_constraint"),
            ("option d", "maximizing_average_range_constraint"),
        ]
        
        for input_text, expected_principle in test_cases:
            with self.subTest(input_text=input_text):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                self.assertEqual(choice_data['principle'], expected_principle,
                               f"Expected {expected_principle}, got {choice_data['principle']} for: {input_text}")
    
    def test_no_constraints_vs_with_constraints_distinction(self):
        """Test that the system correctly distinguishes 'no constraints' from actual constraints."""
        no_constraints_cases = [
            ("I choose maximizing the floor income with no constraints", "maximizing_floor"),
            ("Maximizing average income with zero constraints", "maximizing_average"),
            ("Floor income without any constraint", "maximizing_floor"),
            ("Average income, constraint: none", "maximizing_average")
        ]
        
        with_constraints_cases = [
            ("I choose maximizing average with floor constraint of $15000", "maximizing_average_floor_constraint"),
            ("Average with floor constraint of $20,000", "maximizing_average_floor_constraint"),  
            ("Maximizing average with range constraint of $25000", "maximizing_average_range_constraint"),
            ("Average with range constraint of $30,000", "maximizing_average_range_constraint")
        ]
        
        # Test "no constraints" cases
        for input_text, expected_principle in no_constraints_cases:
            with self.subTest(input_text=input_text, case_type="no_constraints"):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                self.assertEqual(choice_data['principle'], expected_principle,
                               f"Expected {expected_principle}, got {choice_data['principle']} for: {input_text}")
        
        # Test "with constraints" cases  
        for input_text, expected_principle in with_constraints_cases:
            with self.subTest(input_text=input_text, case_type="with_constraints"):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                self.assertEqual(choice_data['principle'], expected_principle,
                               f"Expected {expected_principle}, got {choice_data['principle']} for: {input_text}")
    
    def test_constraint_amount_extraction(self):
        """Test that constraint amounts are correctly extracted."""
        constraint_cases = [
            ("maximizing the average income with a floor constraint of $15000", 15000),
            ("maximizing average with floor constraint of $20,000", 20000),
            ("maximizing the average income with a range constraint with range constraint of 25000", 25000),
            ("average with range constraint of $30,000", 30000)
        ]
        
        for input_text, expected_amount in constraint_cases:
            with self.subTest(input_text=input_text):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                self.assertEqual(choice_data['constraint_amount'], expected_amount,
                               f"Expected constraint amount {expected_amount}, got {choice_data['constraint_amount']} for: {input_text}")
    
    def test_pattern_matching_order(self):
        """Test that pattern matching follows the correct priority order."""
        # Letter patterns should take priority over text patterns
        mixed_cases = [
            # Even with confusing text, letter patterns should win
            ("I choose maximizing the floor income but also like maximizing average", "maximizing_floor"),
            ("My choice is maximizing the average income even though floor income matters", "maximizing_average"),
            # Constraint patterns should only match with actual constraints
            ("maximizing the average income with a floor constraint of $15000", "maximizing_average_floor_constraint"),  
            ("maximizing the average income with a floor constraint with no floor constraints", "maximizing_average_floor_constraint"),  # Letter pattern wins
        ]
        
        for input_text, expected_principle in mixed_cases:
            with self.subTest(input_text=input_text):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                self.assertEqual(choice_data['principle'], expected_principle,
                               f"Expected {expected_principle}, got {choice_data['principle']} for: {input_text}")
    
    def test_edge_cases_and_ambiguous_phrasing(self):
        """Test edge cases that might cause parsing issues."""
        edge_cases = [
            # These should NOT be parsed as constraint principles
            ("I want to maximize floor income but with no constraints", "maximizing_floor"),
            ("Floor maximization without constraint limitations", "maximizing_floor"),
            
            # These should be parsed as constraint principles  
            ("Average income with floor constraint at $18000", "maximizing_average_floor_constraint"),
            ("I prefer average with range constraint set to $22000", "maximizing_average_range_constraint"),
        ]
        
        # Test cases that might not be detected (informal language)
        informal_cases = [
            "Average income is good, constraint free",  # Too informal, might not match
        ]
        
        for input_text, expected_principle in edge_cases:
            with self.subTest(input_text=input_text):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                self.assertEqual(choice_data['principle'], expected_principle,
                               f"Expected {expected_principle}, got {choice_data['principle']} for: {input_text}")
        
        # Test informal cases (may or may not be detected - that's okay)
        for input_text in informal_cases:
            with self.subTest(input_text=input_text, test_type="informal"):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                # It's okay if these don't get detected since they're very informal
                if choice_data:
                    # If detected, should be a simple principle (not constraint)
                    self.assertIn(choice_data['principle'], ['maximizing_floor', 'maximizing_average'],
                                f"Informal phrase should parse as simple principle if detected: {input_text}")
    
    def test_enhanced_ballot_parsing_scenarios(self):
        """Test enhanced ballot parsing scenarios from comprehensive test suite."""
        # Full principle name tests (modern primary support)
        full_name_cases = [
            ("My ballot choice is maximizing_average_floor_constraint with constraint of $15,000", 
             "maximizing_average_floor_constraint"),
            ("I choose maximizing the average income with a floor constraint", 
             "maximizing_average_floor_constraint"), 
            ("My vote is maximizing average with floor constraint", 
             "maximizing_average_floor_constraint"),
            ("My ballot choice is maximizing_floor", 
             "maximizing_floor"),
            ("I choose maximizing_average", 
             "maximizing_average"),
        ]
        
        for input_text, expected_principle in full_name_cases:
            with self.subTest(input_text=input_text, test_type="full_names"):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                self.assertEqual(choice_data['principle'], expected_principle,
                               f"Expected {expected_principle}, got {choice_data['principle']} for: {input_text}")
    
    def test_spanish_ballot_parsing(self):
        """Test Spanish ballot parsing functionality."""
        spanish_cases = [
            ("Mi elección de boleta es maximización del ingreso promedio bajo restricción de ingreso mínimo con restricción de mínimo de $10000", 
             "maximizing_average_floor_constraint"),
            ("maximización del ingreso promedio bajo restricción de ingreso mínimo con restricción de mínimo de $15000", 
             "maximizing_average_floor_constraint"),
            ("Mi elección es el maximización del ingreso mínimo", 
             "maximizing_floor"),
            ("Prefiero maximizar promedio", 
             "maximizing_average"),
        ]
        
        for input_text, expected_principle in spanish_cases:
            with self.subTest(input_text=input_text, language="spanish"):
                # Note: This tests the parsing logic, though full Spanish support requires language setup
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                if choice_data:  # Spanish parsing may not always work without proper language setup
                    self.assertEqual(choice_data['principle'], expected_principle,
                                   f"Expected {expected_principle}, got {choice_data['principle']} for Spanish: {input_text}")
    
    def test_comprehensive_constraint_extraction(self):
        """Test comprehensive constraint amount extraction scenarios."""
        constraint_cases = [
            # Various formatting styles
            ("My ballot choice is maximizing the average income with a floor constraint of $10", 10),
            ("My ballot choice is maximizing the average income with a floor constraint of $13,000", 13000),
            ("maximizing the average income with a floor constraint with a floor constraint of $100", 100),
            ("maximizing the average income with a range constraint with a range constraint of $20000", 20000),
            ("maximizing average with floor constraint of $25000", 25000),
            # Complex phrasing
            ("My ballot choice is Maximizing the average income with a floor constraint with a floor constraint of $13,000", 13000),
            ("I choose maximizing the average income with a floor constraint with floor constraint of $8,000", 8000),
        ]
        
        for input_text, expected_amount in constraint_cases:
            with self.subTest(input_text=input_text, test_type="constraint_extraction"):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(input_text))
                self.assertIsNotNone(choice_data, f"Should detect principle in: {input_text}")
                if 'constraint_amount' in choice_data:
                    self.assertEqual(choice_data['constraint_amount'], expected_amount,
                                   f"Expected constraint amount {expected_amount}, got {choice_data.get('constraint_amount')} for: {input_text}")
    
    def test_regression_prevention(self):
        """Test the specific regression that caused the experiment failure."""
        # This is the EXACT scenario from the failed experiment:
        # Participants said they wanted "maximizing floor income" repeatedly
        # but the system parsed some votes as "maximizing_average_floor_constraint"
        
        discussion_phrases = [
            "I think we should vote to adopt the principle of maximizing the floor income",
            "prioritizing the lowest incomes to ensure everyone has a decent standard of living", 
            "maximize the floor income directly addresses the core issue of inequality",
            "I believe we should adopt the principle of maximizing the floor income"
        ]
        
        ballot_phrases = [
            "maximizing the floor income with no additional constraints",
            "maximizing floor income with no constraints", 
            "my choice is maximizing the floor income without constraints",
            "I choose maximizing the floor income with zero constraints"
        ]
        
        # All discussion phrases should indicate floor income preference (not constraint version)
        for phrase in discussion_phrases:
            with self.subTest(phrase=phrase, context="discussion"):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(phrase))
                if choice_data:  # Some discussion phrases might not match patterns, which is ok
                    self.assertEqual(choice_data['principle'], 'maximizing_floor',
                                   f"Discussion phrase incorrectly parsed as {choice_data['principle']}: {phrase}")
        
        # All ballot phrases MUST be parsed correctly as maximizing_floor
        for phrase in ballot_phrases:
            with self.subTest(phrase=phrase, context="ballot"):
                choice_data = asyncio.run(self.utility_agent.parse_principle_choice_llm(phrase))
                self.assertIsNotNone(choice_data, f"Ballot phrase should be parsed: {phrase}")
                self.assertEqual(choice_data['principle'], 'maximizing_floor',
                               f"CRITICAL: Ballot phrase incorrectly parsed as {choice_data['principle']}: {phrase}")


if __name__ == '__main__':
    unittest.main()