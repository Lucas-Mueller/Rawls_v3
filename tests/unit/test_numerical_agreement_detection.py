#!/usr/bin/env python3
"""
Test the new numerical agreement detection logic (1=yes, 0=no).
"""
import unittest
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from experiment_agents.utility_agent import UtilityAgent


class TestNumericalAgreementDetection(unittest.TestCase):
    """Test cases for numerical agreement detection (1=yes, 0=no)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = UtilityAgent(experiment_language="english")
    
    def test_simple_numerical_agreement(self):
        """Test basic numerical agreement patterns."""
        test_cases = [
            ("1", True, None),  # Simple agreement
            ("0", False, None),  # Simple disagreement
            ("1.", True, None),  # With punctuation
            ("0.", False, None),  # With punctuation
            ("1!", True, None),  # With exclamation
            ("0!", False, None),  # With exclamation
            (" 1 ", True, None),  # With whitespace
            (" 0 ", False, None),  # With whitespace
        ]
        
        for response, expected_agreement, expected_error in test_cases:
            with self.subTest(response=response):
                agreement, error = self.utility_agent.detect_numerical_agreement(response)
                self.assertEqual(agreement, expected_agreement, f"Agreement failed for: '{response}'")
                self.assertEqual(error, expected_error, f"Error failed for: '{response}'")
    
    def test_multilingual_numerical_responses(self):
        """Test numerical responses work across all languages."""
        languages = ["english", "spanish", "mandarin"]
        test_cases = [
            ("1", True, None),
            ("0", False, None),
        ]
        
        for language in languages:
            utility_agent = UtilityAgent(experiment_language=language)
            
            for response, expected_agreement, expected_error in test_cases:
                with self.subTest(language=language, response=response):
                    agreement, error = utility_agent.detect_numerical_agreement(response)
                    self.assertEqual(agreement, expected_agreement, f"Agreement failed for {language}: '{response}'")
                    self.assertEqual(error, expected_error, f"Error failed for {language}: '{response}'")
    
    def test_mandarin_cultural_context_responses(self):
        """Test Mandarin responses with cultural context that should now work correctly."""
        utility_agent = UtilityAgent(experiment_language="mandarin")
        
        # Test cases specific to the Mandarin cultural fix
        mandarin_test_cases = [
            # Confirmation-style responses that should work with new prompt
            ("1 - 我确认", True, None),  # "1 - I confirm"
            ("确认：1", True, None),      # "Confirm: 1" 
            ("是的，1", True, None),      # "Yes, 1"
            ("我确认开始投票：1", True, None),  # "I confirm starting voting: 1"
            
            # Time-based rejection responses
            ("0 - 需要更多时间", False, None),  # "0 - need more time"
            ("我需要更多讨论：0", False, None),  # "I need more discussion: 0"
            ("还不行：0", False, None),      # "Not yet: 0"
            
            # Contextual responses that reflect the new framing
            ("我确认开始正式投票 1", True, None),   # "I confirm starting formal voting 1"
            ("我需要更多讨论时间 0", False, None),  # "I need more discussion time 0"
        ]
        
        for response, expected_agreement, expected_error in mandarin_test_cases:
            with self.subTest(response=response):
                agreement, error = utility_agent.detect_numerical_agreement(response)
                if expected_error is None:
                    self.assertEqual(agreement, expected_agreement, f"Mandarin cultural test failed for: '{response}'")
                    self.assertIsNone(error, f"Unexpected error for: '{response}'")
                else:
                    self.assertIsNotNone(error, f"Expected error for: '{response}'")
    
    def test_invalid_responses(self):
        """Test error handling for invalid responses."""
        # Test cases expecting errors
        error_test_cases = [
            ("", "No valid number found"),  # Empty response
            ("yes", "No valid number found"),  # Text response
            ("2", "No valid number found"),  # Invalid number
            ("3", "No valid number found"),  # Invalid number
            ("-1", "No valid number found"),  # Negative number  
            ("10", "No valid number found"),  # Multi-digit number
            ("abc", "No valid number found"),  # Non-numeric
        ]
        
        for response, expected_error_text in error_test_cases:
            with self.subTest(response=response):
                agreement, error = self.utility_agent.detect_numerical_agreement(response)
                self.assertIsNotNone(error, f"Expected error for: '{response}'")
                self.assertIn(expected_error_text, error, f"Error message wrong for: '{response}'")
        
        # Test cases expecting valid results
        valid_test_cases = [
            ("I choose 1", True),  # Mixed with valid number (should extract 1)
            ("My answer is 0", False),  # Mixed with valid number (should extract 0)
        ]
        
        for response, expected_agreement in valid_test_cases:
            with self.subTest(response=response):
                agreement, error = self.utility_agent.detect_numerical_agreement(response)
                self.assertEqual(agreement, expected_agreement, f"Agreement failed for: '{response}'")
                self.assertIsNone(error, f"Unexpected error for: '{response}'")
    
    def test_multiple_numbers_error(self):
        """Test error handling for responses with multiple numbers."""
        test_cases = [
            ("1 0", "Multiple numbers found"),
            ("0 1", "Multiple numbers found"), 
            ("I choose 1 but maybe 0", "Multiple numbers found"),
            ("1, 0", "Multiple numbers found"),
            ("0, 1", "Multiple numbers found"),
        ]
        
        for response, expected_error_text in test_cases:
            with self.subTest(response=response):
                agreement, error = self.utility_agent.detect_numerical_agreement(response)
                self.assertIsNotNone(error, f"Expected error for: '{response}'")
                self.assertIn(expected_error_text, error, f"Error message wrong for: '{response}'")
    
    def test_contextual_numerical_responses(self):
        """Test numerical responses in realistic conversational context."""
        test_cases = [
            # Agreement cases
            ("I agree to vote: 1", True, None),
            ("My response is 1", True, None), 
            ("1 - I want to vote now", True, None),
            ("Vote confirmation: 1", True, None),
            ("1 (yes, let's vote)", True, None),
            
            # Disagreement cases  
            ("I need more discussion: 0", False, None),
            ("My response is 0", False, None),
            ("0 - I want to continue discussion", False, None),
            ("Vote confirmation: 0", False, None),
            ("0 (no, more discussion please)", False, None),
        ]
        
        for response, expected_agreement, expected_error in test_cases:
            with self.subTest(response=response):
                agreement, error = self.utility_agent.detect_numerical_agreement(response)
                self.assertEqual(agreement, expected_agreement, f"Agreement failed for: '{response}'")
                self.assertEqual(error, expected_error, f"Error failed for: '{response}'")
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Valid cases
        valid_test_cases = [
            # Punctuation and formatting
            ("1.", True),
            ("0.", False),
            ("(1)", True), 
            ("(0)", False),
            ("[1]", True),
            ("[0]", False),
            
            # Word boundaries
            ("option 1", True),
            ("choice 0", False),
            ("number 1 please", True),
            ("select 0 please", False),
        ]
        
        for response, expected_agreement in valid_test_cases:
            with self.subTest(response=response):
                agreement, error = self.utility_agent.detect_numerical_agreement(response)
                self.assertEqual(agreement, expected_agreement, f"Agreement failed for: '{response}'")
                self.assertIsNone(error, f"Unexpected error for: '{response}'")
        
        # Invalid cases (should NOT match - part of larger numbers)
        invalid_test_cases = [
            ("10", "No valid number found"),  # Contains 1 and 0 but as "10"
            ("01", "No valid number found"),  # Leading zero
            ("100", "No valid number found"),  # Contains 1 and 0 but as "100"
        ]
        
        for response, expected_error_text in invalid_test_cases:
            with self.subTest(response=response):
                agreement, error = self.utility_agent.detect_numerical_agreement(response)
                self.assertIsNotNone(error, f"Expected error for: '{response}'")
                self.assertIn(expected_error_text, error, f"Error message wrong for: '{response}'")


if __name__ == '__main__':
    unittest.main()