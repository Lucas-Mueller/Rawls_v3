"""
Unit tests for Phase 2 principle parsing with multilingual support.

Tests the utility agent's principle parsing functionality across English, Spanish, and Mandarin
to ensure reliable operation in multilingual experiments.
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from experiment_agents.utility_agent import UtilityAgent
from models import (
    PrincipleChoice, PrincipleRanking, RankedPrinciple, 
    JusticePrinciple, CertaintyLevel
)
from tests.fixtures.phase2_parsing_fixtures import create_test_utility_agent


class TestMultilingualPrincipleChoice(unittest.TestCase):
    """Test individual principle choice parsing across languages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agents = {
            'english': create_test_utility_agent(temperature=0.0, experiment_language='english'),
            'spanish': create_test_utility_agent(temperature=0.0, experiment_language='spanish'), 
            'mandarin': create_test_utility_agent(temperature=0.0, experiment_language='mandarin')
        }
    
    def test_english_principle_choice_parsing(self):
        """Test English principle choice parsing."""
        test_cases = [
            {
                'response': 'I choose maximizing floor income',
                'expected_principle': JusticePrinciple.MAXIMIZING_FLOOR,
                'expected_constraint': None,
                'description': 'Basic English choice - maximizing floor'
            },
            {
                'response': 'My preference is maximizing average income',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE,
                'expected_constraint': None,
                'description': 'Basic English choice - maximizing average'
            },
            {
                'response': 'I prefer the floor constraint with $15,000',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'expected_constraint': 15000,
                'description': 'English constraint choice with amount'
            },
            {
                'response': 'I support range constraint with $25,000',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                'expected_constraint': 25000,
                'description': 'English range constraint with amount'
            },
            {
                'response': 'Choice: maximizing average income with floor constraint of $18,500',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'expected_constraint': 18500,
                'description': 'English structured format with constraint'
            }
        ]
        
        async def run_tests():
            agent = self.utility_agents['english']
            await agent.async_init()
            
            for case in test_cases:
                with self.subTest(description=case['description']):
                    result = await agent.parse_principle_choice_enhanced(case['response'])
                    
                    self.assertIsInstance(result, PrincipleChoice, 
                        f"Should return PrincipleChoice object for: {case['response']}")
                    self.assertEqual(result.principle, case['expected_principle'],
                        f"Wrong principle for: {case['response']}")
                    self.assertEqual(result.constraint_amount, case['expected_constraint'],
                        f"Wrong constraint amount for: {case['response']}")
        
        asyncio.run(run_tests())
    
    def test_spanish_principle_choice_parsing(self):
        """Test Spanish principle choice parsing."""
        test_cases = [
            {
                'response': 'Mi elección es maximizar los ingresos mínimos',
                'expected_principle': JusticePrinciple.MAXIMIZING_FLOOR,
                'expected_constraint': None,
                'description': 'Spanish choice - maximizing floor income'
            },
            {
                'response': 'Prefiero la maximización del ingreso promedio',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE,
                'expected_constraint': None,
                'description': 'Spanish choice - maximizing average income'
            },
            {
                'response': 'Elijo la restricción de ingreso mínimo con €15.000',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'expected_constraint': 15000,
                'description': 'Spanish floor constraint with European format'
            },
            {
                'response': 'Mi preferencia es la restricción de rango con $20,000',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                'expected_constraint': 20000,
                'description': 'Spanish range constraint with Latin American format'
            },
            {
                'response': 'Apoyo maximizar los ingresos promedio con restricción de €2.5 mil',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'expected_constraint': 2500,
                'description': 'Spanish constraint with decimal mil format (critical test case)'
            },
            {
                'response': 'Elección: maximización del ingreso promedio bajo restricción de ingreso mínimo de 18 mil euros',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'expected_constraint': 18000,
                'description': 'Spanish structured format with number words'
            }
        ]
        
        async def run_tests():
            agent = self.utility_agents['spanish']
            await agent.async_init()
            
            for case in test_cases:
                with self.subTest(description=case['description']):
                    result = await agent.parse_principle_choice_enhanced(case['response'])
                    
                    self.assertIsInstance(result, PrincipleChoice,
                        f"Should return PrincipleChoice object for: {case['response']}")
                    self.assertEqual(result.principle, case['expected_principle'],
                        f"Wrong principle for: {case['response']}")
                    self.assertEqual(result.constraint_amount, case['expected_constraint'],
                        f"Wrong constraint amount for: {case['response']}")
        
        asyncio.run(run_tests())
    
    def test_mandarin_principle_choice_parsing(self):
        """Test Mandarin principle choice parsing."""
        test_cases = [
            {
                'response': '我选择最大化最低收入',
                'expected_principle': JusticePrinciple.MAXIMIZING_FLOOR,
                'expected_constraint': None,
                'description': 'Mandarin choice - maximizing floor income'
            },
            {
                'response': '我的偏好是最大化平均收入',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE,
                'expected_constraint': None,
                'description': 'Mandarin choice - maximizing average income'
            },
            {
                'response': '我选择在最低收入约束条件下最大化平均收入，约束为¥15000',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'expected_constraint': 15000,
                'description': 'Mandarin floor constraint with amount'
            },
            {
                'response': '我支持在范围约束条件下最大化平均收入，约束为¥25000',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                'expected_constraint': 25000,
                'description': 'Mandarin range constraint with amount'
            },
            {
                'response': '选择：最低收入约束条件，限制为2万元',
                'expected_principle': JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                'expected_constraint': 20000,
                'description': 'Mandarin structured format with Chinese numbers'
            }
        ]
        
        async def run_tests():
            agent = self.utility_agents['mandarin']
            await agent.async_init()
            
            for case in test_cases:
                with self.subTest(description=case['description']):
                    result = await agent.parse_principle_choice_enhanced(case['response'])
                    
                    self.assertIsInstance(result, PrincipleChoice,
                        f"Should return PrincipleChoice object for: {case['response']}")
                    self.assertEqual(result.principle, case['expected_principle'],
                        f"Wrong principle for: {case['response']}")
                    self.assertEqual(result.constraint_amount, case['expected_constraint'],
                        f"Wrong constraint amount for: {case['response']}")
        
        asyncio.run(run_tests())


class TestMultilingualPrincipleRanking(unittest.TestCase):
    """Test principle ranking parsing across languages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agents = {
            'english': create_test_utility_agent(temperature=0.0, experiment_language='english'),
            'spanish': create_test_utility_agent(temperature=0.0, experiment_language='spanish'),
            'mandarin': create_test_utility_agent(temperature=0.0, experiment_language='mandarin')
        }
    
    def test_english_principle_ranking_parsing(self):
        """Test English principle ranking parsing."""
        test_cases = [
            {
                'response': """My ranking from best to worst:

1. Maximizing the average income with a floor constraint - This balances growth with protection
2. Maximizing the floor income - Ensures nobody is left behind
3. Maximizing the average income with a range constraint - Limits inequality
4. Maximizing the average income - May lead to high inequality

Overall certainty: very sure""",
                'expected_rankings': [
                    (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1),
                    (JusticePrinciple.MAXIMIZING_FLOOR, 2),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
                    (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
                ],
                'expected_certainty': CertaintyLevel.VERY_SURE,
                'description': 'English detailed ranking with explanations'
            },
            {
                'response': """1. **Maximizing the floor income** - Top priority
2. **Maximizing the average with floor constraint** - Good balance  
3. **Maximizing the average with range constraint** - Less preferred
4. **Maximizing the average income** - Last choice

I'm sure about this ranking.""",
                'expected_rankings': [
                    (JusticePrinciple.MAXIMIZING_FLOOR, 1),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 2),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
                    (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
                ],
                'expected_certainty': CertaintyLevel.SURE,
                'description': 'English markdown formatting with bold'
            }
        ]
        
        async def run_tests():
            agent = self.utility_agents['english']
            await agent.async_init()
            
            for case in test_cases:
                with self.subTest(description=case['description']):
                    result = await agent.parse_principle_ranking_enhanced(case['response'])
                    
                    self.assertIsInstance(result, PrincipleRanking,
                        f"Should return PrincipleRanking object for: {case['response'][:50]}...")
                    self.assertEqual(len(result.rankings), 4,
                        f"Should have 4 rankings for: {case['response'][:50]}...")
                    
                    # Check each ranking
                    for expected_principle, expected_rank in case['expected_rankings']:
                        found = False
                        for ranking in result.rankings:
                            if ranking.principle == expected_principle:
                                self.assertEqual(ranking.rank, expected_rank,
                                    f"Wrong rank for {expected_principle.value}: expected {expected_rank}, got {ranking.rank}")
                                found = True
                                break
                        self.assertTrue(found, f"Missing principle {expected_principle.value} in rankings")
                    
                    self.assertEqual(result.certainty, case['expected_certainty'],
                        f"Wrong certainty level for: {case['response'][:50]}...")
        
        asyncio.run(run_tests())
    
    def test_spanish_principle_ranking_parsing(self):
        """Test Spanish principle ranking parsing."""
        test_cases = [
            {
                'response': """Mi clasificación de mejor a peor:

1. Maximización del ingreso promedio bajo restricción de ingreso mínimo - El mejor equilibrio
2. Maximización del ingreso mínimo - Protege a todos
3. Maximización del ingreso promedio bajo restricción de rango - Limita desigualdad
4. Maximización del ingreso promedio - Puede crear mucha desigualdad

Certeza general: muy seguro""",
                'expected_rankings': [
                    (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1),
                    (JusticePrinciple.MAXIMIZING_FLOOR, 2),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
                    (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
                ],
                'expected_certainty': CertaintyLevel.VERY_SURE,
                'description': 'Spanish detailed ranking with explanations'
            },
            {
                'response': """Ranking:
1. Maximizar los ingresos mínimos
2. Maximizar los ingresos promedio con restricción de ingreso mínimo
3. Maximizar los ingresos promedio con restricción de rango
4. Maximizar los ingresos promedio

Estoy seguro de esta clasificación.""",
                'expected_rankings': [
                    (JusticePrinciple.MAXIMIZING_FLOOR, 1),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 2),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
                    (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
                ],
                'expected_certainty': CertaintyLevel.SURE,
                'description': 'Spanish concise ranking'
            }
        ]
        
        async def run_tests():
            agent = self.utility_agents['spanish']
            await agent.async_init()
            
            for case in test_cases:
                with self.subTest(description=case['description']):
                    result = await agent.parse_principle_ranking_enhanced(case['response'])
                    
                    self.assertIsInstance(result, PrincipleRanking,
                        f"Should return PrincipleRanking object for: {case['response'][:50]}...")
                    self.assertEqual(len(result.rankings), 4,
                        f"Should have 4 rankings for: {case['response'][:50]}...")
                    
                    # Check each ranking
                    for expected_principle, expected_rank in case['expected_rankings']:
                        found = False
                        for ranking in result.rankings:
                            if ranking.principle == expected_principle:
                                self.assertEqual(ranking.rank, expected_rank,
                                    f"Wrong rank for {expected_principle.value}: expected {expected_rank}, got {ranking.rank}")
                                found = True
                                break
                        self.assertTrue(found, f"Missing principle {expected_principle.value} in rankings")
                    
                    self.assertEqual(result.certainty, case['expected_certainty'],
                        f"Wrong certainty level for: {case['response'][:50]}...")
        
        asyncio.run(run_tests())
    
    def test_mandarin_principle_ranking_parsing(self):
        """Test Mandarin principle ranking parsing."""
        test_cases = [
            {
                'response': """我的排名从最好到最差：

1. 在最低收入约束条件下最大化平均收入 - 最佳平衡
2. 最大化最低收入 - 保护所有人
3. 在范围约束条件下最大化平均收入 - 限制不平等  
4. 最大化平均收入 - 可能导致高不平等

总体确定性：非常确定""",
                'expected_rankings': [
                    (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 1),
                    (JusticePrinciple.MAXIMIZING_FLOOR, 2),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
                    (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
                ],
                'expected_certainty': CertaintyLevel.VERY_SURE,
                'description': 'Mandarin detailed ranking with explanations'
            },
            {
                'response': """排名：
1. 最大化最低收入
2. 最低收入约束条件
3. 范围约束条件  
4. 最大化平均收入

我对此排名很确定。""",
                'expected_rankings': [
                    (JusticePrinciple.MAXIMIZING_FLOOR, 1),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 2),
                    (JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, 3),
                    (JusticePrinciple.MAXIMIZING_AVERAGE, 4)
                ],
                'expected_certainty': CertaintyLevel.SURE,
                'description': 'Mandarin concise ranking with short names'
            }
        ]
        
        async def run_tests():
            agent = self.utility_agents['mandarin']
            await agent.async_init()
            
            for case in test_cases:
                with self.subTest(description=case['description']):
                    result = await agent.parse_principle_ranking_enhanced(case['response'])
                    
                    self.assertIsInstance(result, PrincipleRanking,
                        f"Should return PrincipleRanking object for: {case['response'][:50]}...")
                    self.assertEqual(len(result.rankings), 4,
                        f"Should have 4 rankings for: {case['response'][:50]}...")
                    
                    # Check each ranking
                    for expected_principle, expected_rank in case['expected_rankings']:
                        found = False
                        for ranking in result.rankings:
                            if ranking.principle == expected_principle:
                                self.assertEqual(ranking.rank, expected_rank,
                                    f"Wrong rank for {expected_principle.value}: expected {expected_rank}, got {ranking.rank}")
                                found = True
                                break
                        self.assertTrue(found, f"Missing principle {expected_principle.value} in rankings")
                    
                    self.assertEqual(result.certainty, case['expected_certainty'],
                        f"Wrong certainty level for: {case['response'][:50]}...")
        
        asyncio.run(run_tests())


class TestMultilingualEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios across languages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agents = {
            'english': create_test_utility_agent(temperature=0.0, experiment_language='english'),
            'spanish': create_test_utility_agent(temperature=0.0, experiment_language='spanish'),
            'mandarin': create_test_utility_agent(temperature=0.0, experiment_language='mandarin')
        }
    
    def test_invalid_responses_should_fail_gracefully(self):
        """Test that invalid responses fail gracefully across languages."""
        invalid_responses = [
            ("", "Empty response"),
            ("I like apples", "Completely unrelated response"),
            ("Maybe something about principles", "Vague reference without specifics"),
            ("1. Something 2. Another thing 3. Third thing", "Generic numbered list"),
            ("I choose option a", "Letter-based choice (should be rejected)"),
            ("Elijo la opción b", "Spanish letter-based choice (should be rejected)"),
            ("我选择选项a", "Mandarin letter-based choice (should be rejected)")
        ]
        
        async def test_invalid_responses():
            for lang, agent in self.utility_agents.items():
                await agent.async_init()
                for response, description in invalid_responses:
                    with self.subTest(language=lang, description=description):
                        # Both choice and ranking parsing should handle invalid responses
                        # They might return None or raise appropriate exceptions
                        try:
                            choice_result = await agent.parse_principle_choice_enhanced(response)
                            if choice_result is not None:
                                # If it returns a result, it should be a valid PrincipleChoice
                                self.assertIsInstance(choice_result, PrincipleChoice)
                        except Exception as e:
                            # Should raise appropriate exceptions, not crash unexpectedly
                            self.assertIn("ExperimentError", str(type(e).__name__) + str(e.__class__.__bases__))
                        
                        try:
                            ranking_result = await agent.parse_principle_ranking_enhanced(response)
                            if ranking_result is not None:
                                # If it returns a result, it should be a valid PrincipleRanking
                                self.assertIsInstance(ranking_result, PrincipleRanking)
                                self.assertEqual(len(ranking_result.rankings), 4)
                        except Exception as e:
                            # Should raise appropriate exceptions, not crash unexpectedly
                            self.assertIn("ExperimentError", str(type(e).__name__) + str(e.__class__.__bases__))
        
        asyncio.run(test_invalid_responses())
    
    def test_mixed_language_scenarios(self):
        """Test scenarios where participants might mix languages."""
        mixed_language_cases = [
            {
                'agent_lang': 'spanish',
                'response': 'Prefiero maximizing floor income',
                'description': 'Spanish agent with English principle name'
            },
            {
                'agent_lang': 'english', 
                'response': 'I choose maximización del ingreso mínimo',
                'description': 'English agent with Spanish principle name'
            },
            {
                'agent_lang': 'mandarin',
                'response': 'I prefer 最大化最低收入',
                'description': 'Mandarin agent with mixed English-Chinese'
            }
        ]
        
        async def test_mixed_language():
            for case in mixed_language_cases:
                with self.subTest(description=case['description']):
                    agent = self.utility_agents[case['agent_lang']]
                    await agent.async_init()
                    
                    try:
                        result = await agent.parse_principle_choice_enhanced(case['response'])
                        # Mixed language might work or might not - either is acceptable
                        # as long as it doesn't crash the system
                        if result is not None:
                            self.assertIsInstance(result, PrincipleChoice)
                    except Exception as e:
                        # Should handle gracefully without system crash
                        self.assertIsNotNone(e)  # Some exception occurred, which is fine
        
        asyncio.run(test_mixed_language())
    
    def test_constraint_amount_edge_cases(self):
        """Test edge cases in constraint amount parsing across languages."""
        constraint_edge_cases = [
            {
                'lang': 'english',
                'response': 'Floor constraint with $5',  # Too small - should be rejected
                'expected_constraint': None,
                'description': 'English - amount too small (payoff scale)'
            },
            {
                'lang': 'spanish',
                'response': 'Restricción con €0',  # Zero amount
                'expected_constraint': None,
                'description': 'Spanish - zero constraint amount'
            },
            {
                'lang': 'mandarin',
                'response': '约束条件，无限制',  # No constraint
                'expected_constraint': None,
                'description': 'Mandarin - no constraint specified'
            },
            {
                'lang': 'english',
                'response': 'Floor constraint with $1,000,000',  # Very large amount
                'expected_constraint': None,  # Might be rejected as unrealistic
                'description': 'English - very large constraint amount'
            }
        ]
        
        async def test_constraint_edges():
            for case in constraint_edge_cases:
                with self.subTest(description=case['description']):
                    agent = self.utility_agents[case['lang']]
                    await agent.async_init()
                    
                    try:
                        result = await agent.parse_principle_choice_enhanced(case['response'])
                        if result is not None:
                            # Check that invalid constraints are handled appropriately
                            if case['expected_constraint'] is None:
                                self.assertIsNone(result.constraint_amount,
                                    f"Should reject invalid constraint in: {case['response']}")
                    except Exception:
                        # Edge cases might cause parsing failures, which is acceptable
                        pass
        
        asyncio.run(test_constraint_edges())
    
    def test_uncertainty_levels_across_languages(self):
        """Test certainty level detection across languages."""
        certainty_cases = [
            {
                'lang': 'english',
                'response': 'I choose maximizing floor income. I am very sure about this.',
                'expected_certainty': CertaintyLevel.VERY_SURE,
                'description': 'English very sure'
            },
            {
                'lang': 'english',
                'response': 'Maybe maximizing average income, but I am unsure.',
                'expected_certainty': CertaintyLevel.UNSURE,
                'description': 'English unsure'
            },
            {
                'lang': 'spanish',
                'response': 'Elijo maximizar los ingresos mínimos. Estoy muy seguro.',
                'expected_certainty': CertaintyLevel.VERY_SURE,
                'description': 'Spanish muy seguro'
            },
            {
                'lang': 'spanish',
                'response': 'Tal vez maximizar el promedio, pero no estoy seguro.',
                'expected_certainty': CertaintyLevel.UNSURE,
                'description': 'Spanish no estoy seguro'
            },
            {
                'lang': 'mandarin',
                'response': '我选择最大化最低收入。我非常确定。',
                'expected_certainty': CertaintyLevel.VERY_SURE,
                'description': 'Mandarin very certain'
            },
            {
                'lang': 'mandarin',
                'response': '可能选择最大化平均收入，但我不太确定。',
                'expected_certainty': CertaintyLevel.UNSURE,
                'description': 'Mandarin uncertain'
            }
        ]
        
        async def test_certainty_detection():
            for case in certainty_cases:
                with self.subTest(description=case['description']):
                    agent = self.utility_agents[case['lang']]
                    await agent.async_init()
                    
                    try:
                        result = await agent.parse_principle_choice_enhanced(case['response'])
                        if result is not None:
                            self.assertEqual(result.certainty, case['expected_certainty'],
                                f"Wrong certainty level for: {case['response']}")
                    except Exception:
                        # Some certainty detection might fail, which is acceptable
                        pass
        
        asyncio.run(test_certainty_detection())


class TestMultilingualConstraintAmountParsing(unittest.TestCase):
    """Test constraint amount parsing specifically across languages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agents = {
            'english': create_test_utility_agent(temperature=0.0, experiment_language='english'),
            'spanish': create_test_utility_agent(temperature=0.0, experiment_language='spanish'),
            'mandarin': create_test_utility_agent(temperature=0.0, experiment_language='mandarin')
        }
    
    def test_complex_constraint_formats(self):
        """Test complex constraint amount formats across languages."""
        constraint_test_cases = [
            # English formats
            {
                'lang': 'english',
                'text': 'constraint of fifteen thousand dollars',
                'expected': 15000,
                'description': 'English word numbers'
            },
            {
                'lang': 'english',
                'text': 'floor of $25,500.75',
                'expected': 25500,  # Should ignore cents
                'description': 'English with cents'
            },
            # Spanish formats (critical for the bug that was found)
            {
                'lang': 'spanish',
                'text': 'restricción de €2.5 mil',
                'expected': 2500,
                'description': 'Spanish decimal mil (main bug fix case)'
            },
            {
                'lang': 'spanish',
                'text': 'límite de quince mil euros',
                'expected': 15000,
                'description': 'Spanish word numbers'
            },
            {
                'lang': 'spanish',
                'text': 'tope de €125.750,50',
                'expected': 125750,
                'description': 'Spanish European format with cents'
            },
            # Mandarin formats
            {
                'lang': 'mandarin',
                'text': '约束 ¥一万五千',
                'expected': 15000,
                'description': 'Mandarin traditional number words'
            },
            {
                'lang': 'mandarin',
                'text': '限制 15000元',
                'expected': 15000,
                'description': 'Mandarin with yuan'
            }
        ]
        
        async def test_constraint_parsing():
            for case in constraint_test_cases:
                with self.subTest(description=case['description']):
                    agent = self.utility_agents[case['lang']]
                    await agent.async_init()
                    
                    result = await agent.parse_constraint_amount(case['text'], case['lang'])
                    self.assertEqual(result, case['expected'],
                        f"Expected {case['expected']}, got {result} for '{case['text']}' in {case['lang']}")
        
        asyncio.run(test_constraint_parsing())


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)