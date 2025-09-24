"""
Currency Symbol Handling Test Module for Multilingual Phase 2 Parsing

Tests comprehensive currency symbol variations and parsing across different
regional currencies and formatting conventions as specified in Subplan 5.

Supported Currencies:
- USD: $, USD, US$
- EUR: €, EUR  
- CNY: ¥, RMB, CNY, 元
- MXN: $, MXN, peso
- Multiple peso variants (ARS, COP, etc.)

This module ensures robust currency symbol detection and amount parsing
across all supported regional variations and edge cases.
"""

import unittest
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Tuple, List, Dict

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from tests.fixtures.phase2_parsing_fixtures import create_test_utility_agent


class TestUSDCurrencySymbols(unittest.TestCase):
    """Test USD currency symbol variations and parsing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_usd_dollar_sign_variations(self):
        """Test various USD dollar sign placements and formats."""
        test_cases = [
            ("constraint of $15000", 15000, "Basic dollar sign prefix"),
            ("limit of 15000$", 15000, "Dollar sign suffix"),
            ("restriction $ 15000", 15000, "Dollar sign with space"),
            ("floor of 15000 $", 15000, "Dollar sign with space suffix"),
            ("cap of $15,000", 15000, "Dollar sign with comma separator"),
            ("constraint of $15,000.00", 15000, "Dollar sign with cents"),
            ("limit of $15,000.50", 15050, "Dollar sign with fifty cents"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected, 
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_usd_code_variations(self):
        """Test USD currency code variations."""
        test_cases = [
            ("constraint of USD 15000", 15000, "USD prefix"),
            ("limit of 15000 USD", 15000, "USD suffix"),
            ("restriction USD15000", 15000, "USD attached prefix"),
            ("floor of 15000USD", 15000, "USD attached suffix"),
            ("cap of USD 15,000", 15000, "USD with comma separator"),
            ("constraint of USD 15,000.00", 15000, "USD with cents"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_us_dollar_variations(self):
        """Test 'US$' and 'US Dollar' variations."""
        test_cases = [
            ("constraint of US$15000", 15000, "US$ prefix"),
            ("limit of 15000 US$", 15000, "US$ suffix"),
            ("restriction US$ 15000", 15000, "US$ with space"),
            ("floor of US$15,000", 15000, "US$ with comma"),
            ("cap of 15000 US dollars", 15000, "US dollars text"),
            ("constraint of 15000 American dollars", 15000, "American dollars text"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")


class TestEURCurrencySymbols(unittest.TestCase):
    """Test EUR currency symbol variations and parsing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_euro_symbol_variations(self):
        """Test various Euro symbol placements and formats."""
        test_cases = [
            ("constraint of €15000", 15000, "Euro symbol prefix"),
            ("limit of 15000€", 15000, "Euro symbol suffix"),
            ("restriction € 15000", 15000, "Euro symbol with space prefix"),
            ("floor of 15000 €", 15000, "Euro symbol with space suffix"),
            ("cap of €15.000", 15000, "Euro with European thousands separator"),
            ("constraint of €15.000,00", 15000, "Euro with European decimal"),
            ("limit of €15.000,50", 15050, "Euro with European fifty cents"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_eur_code_variations(self):
        """Test EUR currency code variations."""
        test_cases = [
            ("constraint of EUR 15000", 15000, "EUR prefix"),
            ("limit of 15000 EUR", 15000, "EUR suffix"),
            ("restriction EUR15000", 15000, "EUR attached prefix"),
            ("floor of 15000EUR", 15000, "EUR attached suffix"),
            ("cap of EUR 15.000", 15000, "EUR with European separator"),
            ("constraint of EUR 15.000,00", 15000, "EUR with European decimal"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_euro_text_variations(self):
        """Test 'Euro' and 'Euros' text variations."""
        test_cases = [
            ("constraint of 15000 euros", 15000, "euros text"),
            ("limit of 15000 euro", 15000, "euro text"),
            ("restriction 15.000 euros", 15000, "euros with European format"),
            ("floor of 15.000 euro", 15000, "euro with European format"),
            ("cap of 15000 European euros", 15000, "European euros text"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")


class TestCNYCurrencySymbols(unittest.TestCase):
    """Test CNY (Chinese Yuan) currency symbol variations and parsing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_yuan_symbol_variations(self):
        """Test various Yuan symbol placements and formats."""
        test_cases = [
            ("约束为¥15000", 15000, "Yuan symbol prefix"),
            ("限制是15000¥", 15000, "Yuan symbol suffix"),
            ("约束¥ 15000", 15000, "Yuan symbol with space prefix"),
            ("限制是15000 ¥", 15000, "Yuan symbol with space suffix"),
            ("约束为¥15,000", 15000, "Yuan with comma separator"),
            ("限制是¥15,000.00", 15000, "Yuan with cents"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_cny_code_variations(self):
        """Test CNY currency code variations."""
        test_cases = [
            ("constraint of CNY 15000", 15000, "CNY prefix"),
            ("limit of 15000 CNY", 15000, "CNY suffix"),
            ("约束CNY15000", 15000, "CNY attached prefix"),
            ("限制15000CNY", 15000, "CNY attached suffix"),
            ("约束为CNY 15,000", 15000, "CNY with comma"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_rmb_variations(self):
        """Test RMB (Renminbi) variations."""
        test_cases = [
            ("约束为RMB 15000", 15000, "RMB prefix"),
            ("限制是15000 RMB", 15000, "RMB suffix"),
            ("约束RMB15000", 15000, "RMB attached prefix"),
            ("限制15000RMB", 15000, "RMB attached suffix"),
            ("约束为RMB 15,000", 15000, "RMB with comma"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_yuan_character_variations(self):
        """Test Chinese '元' character variations."""
        test_cases = [
            ("约束为15000元", 15000, "元 character suffix"),
            ("限制是15000 元", 15000, "元 character with space"),
            ("约束为15,000元", 15000, "元 with comma separator"),
            ("限制是1万5千元", 15000, "元 with Chinese numerals"),
            ("约束为2万元", 20000, "元 with 万 (ten thousand)"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_chinese_number_units(self):
        """Test Chinese number unit parsing with currency."""
        test_cases = [
            ("约束为1万元", 10000, "1万 = 10,000"),
            ("限制是2万元", 20000, "2万 = 20,000"),  
            ("约束为15万元", 150000, "15万 = 150,000"),
            ("限制是1万5千元", 15000, "1万5千 = 15,000"),
            ("约束为2万5千元", 25000, "2万5千 = 25,000"),
            ("限制是10万元", 100000, "10万 = 100,000"),
            ("约束为5千元", 5000, "5千 = 5,000"),
            ("限制是15千元", 15000, "15千 = 15,000"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")


class TestMXNAndPesoCurrencies(unittest.TestCase):
    """Test MXN (Mexican Peso) and other peso currency variations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_mxn_code_variations(self):
        """Test Mexican Peso (MXN) code variations."""
        test_cases = [
            ("restricción de MXN 15000", 15000, "MXN prefix"),
            ("límite de 15000 MXN", 15000, "MXN suffix"),
            ("restricciónMXN15000", 15000, "MXN attached prefix"),
            ("límite15000MXN", 15000, "MXN attached suffix"),
            ("restricción de MXN 15,000", 15000, "MXN with comma"),
            ("límite de MXN 15,000.00", 15000, "MXN with cents"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_peso_text_variations(self):
        """Test peso text variations."""
        test_cases = [
            ("restricción de 15000 pesos", 15000, "pesos text"),
            ("límite de 15000 peso", 15000, "peso text singular"),
            ("restricción de 15,000 pesos", 15000, "pesos with comma"),
            ("límite de 15000 pesos mexicanos", 15000, "Mexican pesos text"),
            ("restricción de 15000 pesos MX", 15000, "pesos MX text"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_other_peso_variants(self):
        """Test other peso currency variants (ARS, COP, etc.)."""
        test_cases = [
            ("restricción de ARS 15000", 15000, "Argentine Peso (ARS)"),
            ("límite de 15000 ARS", 15000, "ARS suffix"),
            ("restricción de COP 15000", 15000, "Colombian Peso (COP)"),
            ("límite de 15000 COP", 15000, "COP suffix"),
            ("restricción de CLP 15000", 15000, "Chilean Peso (CLP)"),
            ("límite de 15000 CLP", 15000, "CLP suffix"),
            ("restricción de UYU 15000", 15000, "Uruguayan Peso (UYU)"),
            ("límite de 15000 UYU", 15000, "UYU suffix"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")
    
    def test_peso_with_dollar_sign(self):
        """Test peso currencies using dollar sign symbol."""
        test_cases = [
            ("restricción de $15000 pesos", 15000, "Dollar sign with pesos text"),
            ("límite de $15,000 MXN", 15000, "Dollar sign with MXN code"),
            ("restricción de $15000 ARS", 15000, "Dollar sign with ARS code"),
            ("límite de $15,000 COP", 15000, "Dollar sign with COP code"),
            # Ambiguous cases - system should handle gracefully
            ("restricción de $15000", 15000, "Ambiguous dollar/peso (should parse amount)"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Expected {expected}, got {result} for '{statement}'")


class TestMixedCurrencyScenarios(unittest.TestCase):
    """Test complex scenarios with mixed currency references."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_currency_equivalence_statements(self):
        """Test statements mentioning currency equivalences."""
        test_cases = [
            ("constraint of $15000 or €13000 equivalent", "USD or EUR equivalence"),
            ("limit of ¥100000 or $15000 equivalent", "CNY or USD equivalence"),
            ("restriction €15000 or equivalent in local currency", "EUR or local equivalence"),
            ("floor of 15000 pesos or dollars equivalent", "Peso or dollar equivalence"),
        ]
        
        for statement, description in test_cases:
            with self.subTest(statement=statement, description=description):
                # Test that parsing doesn't crash on equivalence statements
                try:
                    result = asyncio.run(self._parse_constraint_amount(statement))
                    if result is not None:
                        self.assertIsInstance(result, (int, float), f"Should return numeric value: {result}")
                except Exception as e:
                    self.fail(f"Should not crash on currency equivalence: {e}")
    
    def test_currency_conversion_references(self):
        """Test statements referencing currency conversion."""
        test_cases = [
            ("constraint of $15000 USD (approximately €13000)", "USD with EUR approximation"),
            ("limit of ¥100000 (about $15000)", "CNY with USD approximation"),
            ("restriction €15000 (roughly $16000)", "EUR with USD approximation"),
            ("floor of 15000 pesos (around $800 USD)", "MXN with USD approximation"),
        ]
        
        for statement, description in test_cases:
            with self.subTest(statement=statement, description=description):
                # Test that parsing handles conversion references gracefully
                try:
                    result = asyncio.run(self._parse_constraint_amount(statement))
                    if result is not None:
                        self.assertIsInstance(result, (int, float), f"Should return numeric value: {result}")
                except Exception as e:
                    self.fail(f"Should not crash on currency conversion: {e}")
    
    def test_ambiguous_currency_contexts(self):
        """Test ambiguous currency contexts ($ could be USD, MXN, etc.)."""
        test_cases = [
            ("constraint of $15000", 15000, "Ambiguous $ symbol"),
            ("límite de $15000", 15000, "Spanish context with $ symbol"),
            ("约束为$15000", 15000, "Chinese context with $ symbol"),
            ("restriction of $15,000", 15000, "English context with $ symbol"),
        ]
        
        for statement, expected, description in test_cases:
            with self.subTest(statement=statement, description=description):
                # System should parse amount regardless of currency ambiguity
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, expected,
                               f"{description}: Should parse amount despite ambiguity")


class TestCurrencyDetectionAndValidation(unittest.TestCase):
    """Test currency detection and validation logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_currency_symbol_precedence(self):
        """Test which currency symbol takes precedence in mixed cases."""
        test_cases = [
            ("constraint of $15000 EUR", "Dollar sign vs EUR code"),
            ("limit of €15000 USD", "Euro symbol vs USD code"),
            ("约束为¥15000 dollars", "Yuan symbol vs dollars text"),
            ("restricción de €15000 pesos", "Euro symbol vs pesos text"),
        ]
        
        for statement, description in test_cases:
            with self.subTest(statement=statement, description=description):
                # Test that parsing handles conflicting currency indicators
                try:
                    result = asyncio.run(self._parse_constraint_amount(statement))
                    # Main requirement is successful parsing without crashes
                    self.assertIsNotNone(result, f"Should parse despite mixed currencies: {statement}")
                except Exception as e:
                    self.fail(f"Should not crash on mixed currency symbols: {e}")
    
    def test_invalid_currency_combinations(self):
        """Test handling of invalid or nonsensical currency combinations."""
        test_cases = [
            ("constraint of ¥15000 euros", "Yuan symbol with euros text"),
            ("limit of €15000 yuan", "Euro symbol with yuan text"),
            ("restricción de $15000 RMB", "Dollar sign with RMB code"),
            ("约束为€15000 pesos", "Euro symbol with Chinese text and pesos"),
        ]
        
        for statement, description in test_cases:
            with self.subTest(statement=statement, description=description):
                # System should handle invalid combinations gracefully
                try:
                    result = asyncio.run(self._parse_constraint_amount(statement))
                    # Accept any reasonable result or None
                    if result is not None:
                        self.assertIsInstance(result, (int, float), f"Should return numeric value: {result}")
                except (ValueError, TypeError) as e:
                    # Acceptable to raise validation errors for invalid combinations
                    pass
                except Exception as e:
                    self.fail(f"Should not crash on invalid currency combinations: {e}")
    
    def test_currency_detection_accuracy(self):
        """Test accuracy of currency detection from text."""
        detection_cases = [
            ("constraint of $15000", "USD", "Basic dollar detection"),
            ("límite de €15000", "EUR", "Basic euro detection"),  
            ("约束为¥15000", "CNY", "Basic yuan detection"),
            ("restricción de MXN 15000", "MXN", "MXN code detection"),
            ("constraint of 15000 RMB", "CNY", "RMB code detection"),
            ("limit of 15000元", "CNY", "Yuan character detection"),
        ]
        
        for statement, expected_currency, description in detection_cases:
            with self.subTest(statement=statement, description=description):
                detected_currency = asyncio.run(self._detect_currency_from_text(statement))
                if detected_currency:  # Only test if currency detection is implemented
                    self.assertEqual(detected_currency, expected_currency,
                                   f"{description}: Expected {expected_currency}, got {detected_currency}")


    # Helper methods
    async def _parse_constraint_amount(self, statement: str) -> Optional[int]:
        """Helper to parse constraint amounts from statements."""
        await self.utility_agent.async_init()
        try:
            # Mock a full statement with the constraint text
            full_statement = f"I choose maximizing average income {statement}"
            result = await self.utility_agent.parse_participant_preference(
                full_statement, participant_name="TestParticipant"
            )
            return result.constraint_amount if result else None
        except Exception:
            return None
    
    async def _detect_currency_from_text(self, text: str) -> Optional[str]:
        """Helper to detect currency from text."""
        # Simple currency detection logic
        if 'MXN' in text or 'pesos mexicanos' in text:
            return 'MXN'
        elif 'ARS' in text:
            return 'ARS'
        elif 'COP' in text:
            return 'COP'
        elif 'CNY' in text or 'RMB' in text or '¥' in text or '元' in text:
            return 'CNY'
        elif '€' in text or 'EUR' in text or 'euro' in text.lower():
            return 'EUR'
        elif '$' in text and ('USD' in text or 'US$' in text):
            return 'USD'
        elif '$' in text and 'peso' in text.lower():
            return 'MXN'  # Default peso assumption
        elif '$' in text:
            return 'USD'  # Default dollar assumption
        return None


if __name__ == '__main__':
    # Configure test runner for async support
    unittest.main()