#!/usr/bin/env python3
"""Simple test script to verify multilingual principle extraction fixes."""

import unittest
from experiment_agents.utility_agent import UtilityAgent


class TestMultilingualParsing(unittest.TestCase):
    """Test cases for multilingual principle parsing."""
    
    def setUp(self):
        """Set up test utility agent."""
        self.utility_agent = UtilityAgent("test")
    
    def test_multilingual_llm_response_parsing(self):
        """Test that the _parse_llm_principle_response handles multilingual anchors."""
        
        test_cases = [
            # English
            ("PRINCIPLE_DETECTED: maximizing_floor | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
            ("PRINCIPLE_DETECTED: maximizing_average | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
            
            # Spanish
            ("PRINCIPIO_DETECTADO: maximizar_piso | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
            ("PRINCIPIO_DETECTADO: maximizar_promedio | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
            
            # Mandarin
            ("检测到原则：最大化底线 | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
            ("检测到原则：最大化平均 | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
            
            # Test canonical forms with constraints
            ("PRINCIPLE_DETECTED: maximizing_average_floor_constraint | constraint: $15000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
            ("PRINCIPIO_DETECTADO: maximizar_promedio_restriccion_piso | constraint: $15000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
            ("检测到原则：最大化平均底线约束 | constraint: $15000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
        ]
        
        passed = 0
        failed = 0
        
        for llm_response, expected_principle in test_cases:
            with self.subTest(llm_response=llm_response[:50]):
                try:
                    result = self.utility_agent._parse_llm_principle_response(llm_response)
                    
                    if result and result.get('principle') == expected_principle:
                        passed += 1
                    else:
                        failed += 1
                        self.fail(f"Expected: {expected_principle}, Got: {result.get('principle') if result else None}")
                        
                except Exception as e:
                    failed += 1
                    self.fail(f"Exception parsing '{llm_response[:50]}...': {str(e)}")
        
        # Assert overall success rate
        total = len(test_cases)
        success_rate = passed / total
        self.assertGreaterEqual(success_rate, 0.8, f"Success rate too low: {success_rate:.1%} ({passed}/{total})")
    
    def test_english_principle_parsing(self):
        """Test specific English principle parsing."""
        test_cases = [
            ("PRINCIPLE_DETECTED: maximizing_floor | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
            ("PRINCIPLE_DETECTED: maximizing_average | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
            ("PRINCIPLE_DETECTED: maximizing_average_floor_constraint | constraint: $20000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
            ("PRINCIPLE_DETECTED: maximizing_average_range_constraint | constraint: $25000 | certainty: sure | confidence: 0.95", "maximizing_average_range_constraint"),
        ]
        
        for llm_response, expected_principle in test_cases:
            with self.subTest(principle=expected_principle):
                result = self.utility_agent._parse_llm_principle_response(llm_response)
                self.assertIsNotNone(result, f"Failed to parse: {llm_response}")
                self.assertEqual(result.get('principle'), expected_principle)
    
    def test_spanish_principle_parsing(self):
        """Test specific Spanish principle parsing."""
        test_cases = [
            ("PRINCIPIO_DETECTADO: maximizar_piso | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
            ("PRINCIPIO_DETECTADO: maximizar_promedio | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
            ("PRINCIPIO_DETECTADO: maximizar_promedio_restriccion_piso | constraint: $18000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
        ]
        
        for llm_response, expected_principle in test_cases:
            with self.subTest(principle=expected_principle):
                result = self.utility_agent._parse_llm_principle_response(llm_response)
                self.assertIsNotNone(result, f"Failed to parse: {llm_response}")
                self.assertEqual(result.get('principle'), expected_principle)
    
    def test_mandarin_principle_parsing(self):
        """Test specific Mandarin principle parsing."""
        test_cases = [
            ("检测到原则：最大化底线 | constraint: none | certainty: sure | confidence: 0.9", "maximizing_floor"),
            ("检测到原则：最大化平均 | constraint: none | certainty: sure | confidence: 0.9", "maximizing_average"),
            ("检测到原则：最大化平均底线约束 | constraint: $22000 | certainty: sure | confidence: 0.95", "maximizing_average_floor_constraint"),
        ]
        
        for llm_response, expected_principle in test_cases:
            with self.subTest(principle=expected_principle):
                result = self.utility_agent._parse_llm_principle_response(llm_response)
                self.assertIsNotNone(result, f"Failed to parse: {llm_response}")
                self.assertEqual(result.get('principle'), expected_principle)
    
    def test_invalid_responses(self):
        """Test handling of invalid or malformed responses."""
        invalid_cases = [
            "",  # Empty string
            "INVALID_FORMAT: some text",  # Wrong anchor
            "PRINCIPLE_DETECTED: invalid_principle | constraint: none",  # Invalid principle
            "PRINCIPLE_DETECTED: | constraint: none",  # Missing principle
        ]
        
        for invalid_response in invalid_cases:
            with self.subTest(response=invalid_response):
                result = self.utility_agent._parse_llm_principle_response(invalid_response)
                # Should return None or empty dict for invalid responses
                if result:
                    self.assertIsNone(result.get('principle'), f"Should not parse invalid response: {invalid_response}")
    
    def test_constraint_extraction(self):
        """Test constraint amount extraction from responses."""
        test_cases = [
            ("PRINCIPLE_DETECTED: maximizing_average_floor_constraint | constraint: $15000 | certainty: sure | confidence: 0.95", 15000),
            ("PRINCIPIO_DETECTADO: maximizar_promedio_restriccion_piso | constraint: $25000 | certainty: sure | confidence: 0.95", 25000),
            ("检测到原则：最大化平均底线约束 | constraint: $10000 | certainty: sure | confidence: 0.95", 10000),
            ("PRINCIPLE_DETECTED: maximizing_average | constraint: none | certainty: sure | confidence: 0.9", None),
        ]
        
        for llm_response, expected_constraint in test_cases:
            with self.subTest(constraint=expected_constraint):
                result = self.utility_agent._parse_llm_principle_response(llm_response)
                self.assertIsNotNone(result, f"Failed to parse: {llm_response}")
                
                if expected_constraint is None:
                    self.assertIn(result.get('constraint_amount'), [None, 0, "none"])
                else:
                    self.assertEqual(result.get('constraint_amount'), expected_constraint)


if __name__ == "__main__":
    unittest.main()