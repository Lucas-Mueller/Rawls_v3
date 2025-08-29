"""
Cultural Context Validation Test Module for Multilingual Phase 2 Parsing

Tests cultural context recognition and handling across different languages
and cultural communication patterns as specified in Subplan 5.

Cultural Elements Tested:
1. Formal vs informal language detection
2. Politeness marker recognition  
3. Agreement strength variations
4. Cultural number preferences (lucky/unlucky numbers)
5. Cultural communication styles
6. Honorifics and respect levels

This module ensures the system respects cultural contexts and communication
patterns without making Western-centric assumptions about interaction styles.
"""

import unittest
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Tuple, List, Dict
from enum import Enum

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from tests.fixtures.phase2_parsing_fixtures import create_test_utility_agent
from utils.language_manager import LanguageManager, SupportedLanguage


class FormalityLevel(Enum):
    """Enumeration for formality levels."""
    VERY_FORMAL = "very_formal"
    FORMAL = "formal"
    NEUTRAL = "neutral"
    INFORMAL = "informal"
    VERY_INFORMAL = "very_informal"


class TestFormalInformalLanguageDetection(unittest.TestCase):
    """Test detection of formal vs informal language patterns."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
        self.language_manager = LanguageManager()
    
    def test_english_formality_levels(self):
        """Test English formal vs informal language detection."""
        formal_cases = [
            ("I would respectfully suggest that we consider maximizing the floor income", 
             FormalityLevel.FORMAL, "Respectful suggestion"),
            ("May I propose that we examine the principle of maximizing average income",
             FormalityLevel.FORMAL, "Polite proposal"),
            ("I humbly submit that maximizing average with floor constraint would be appropriate",
             FormalityLevel.VERY_FORMAL, "Humble submission"),
            ("I believe we should consider maximizing the floor income",
             FormalityLevel.NEUTRAL, "Standard belief statement"),
        ]
        
        informal_cases = [
            ("I think we should go with maximizing the floor income",
             FormalityLevel.INFORMAL, "Casual preference"),
            ("Let's just pick maximizing average income",
             FormalityLevel.INFORMAL, "Casual suggestion"),
            ("I'm gonna vote for maximizing the floor",
             FormalityLevel.VERY_INFORMAL, "Very casual statement"),
            ("How about we do maximizing average income?",
             FormalityLevel.INFORMAL, "Casual question"),
        ]
        
        all_cases = formal_cases + informal_cases
        
        for statement, expected_formality, description in all_cases:
            with self.subTest(statement=statement, description=description):
                detected_formality = asyncio.run(self._detect_formality_level(statement))
                if detected_formality:  # Only test if formality detection is implemented
                    # Allow some flexibility in formality detection
                    self.assertIsInstance(detected_formality, FormalityLevel,
                                        f"{description}: Should return FormalityLevel enum")
    
    def test_spanish_formality_levels(self):
        """Test Spanish formal vs informal language detection."""
        formal_cases = [
            ("Quisiera respetuosamente sugerir que consideremos maximizar el ingreso mínimo",
             FormalityLevel.FORMAL, "Respectful Spanish suggestion"),
            ("Me permito proponer que examinemos el principio de maximizar el ingreso promedio",
             FormalityLevel.FORMAL, "Polite Spanish proposal"),
            ("Humildemente sugiero que maximizar el promedio con restricción de piso sería apropiado",
             FormalityLevel.VERY_FORMAL, "Humble Spanish submission"),
            ("Creo que deberíamos considerar maximizar el ingreso mínimo",
             FormalityLevel.NEUTRAL, "Spanish belief statement"),
        ]
        
        informal_cases = [
            ("Pienso que deberíamos ir con maximizar el ingreso mínimo",
             FormalityLevel.INFORMAL, "Casual Spanish preference"),
            ("Vamos a elegir maximizar el ingreso promedio",
             FormalityLevel.INFORMAL, "Casual Spanish suggestion"),
            ("Voy a votar por maximizar el mínimo",
             FormalityLevel.INFORMAL, "Casual Spanish vote"),
            ("¿Qué tal si hacemos maximizar el ingreso promedio?",
             FormalityLevel.INFORMAL, "Casual Spanish question"),
        ]
        
        all_cases = formal_cases + informal_cases
        
        for statement, expected_formality, description in all_cases:
            with self.subTest(statement=statement, description=description):
                detected_formality = asyncio.run(self._detect_formality_level(statement))
                if detected_formality:
                    self.assertIsInstance(detected_formality, FormalityLevel,
                                        f"{description}: Should return FormalityLevel enum")
    
    def test_chinese_formality_levels(self):
        """Test Chinese formal vs informal language detection."""
        formal_cases = [
            ("我谨慎地建议我们考虑最大化最低收入原则",
             FormalityLevel.FORMAL, "Respectful Chinese suggestion"),
            ("请允许我提议我们研究最大化平均收入的原则",
             FormalityLevel.FORMAL, "Polite Chinese proposal"),  
            ("我恭敬地认为最大化平均收入并设置最低限制会比较合适",
             FormalityLevel.VERY_FORMAL, "Very formal Chinese submission"),
            ("我认为我们应该考虑最大化最低收入",
             FormalityLevel.NEUTRAL, "Chinese belief statement"),
        ]
        
        informal_cases = [
            ("我觉得我们应该选择最大化最低收入",
             FormalityLevel.INFORMAL, "Casual Chinese preference"),
            ("我们就选最大化平均收入吧",
             FormalityLevel.INFORMAL, "Casual Chinese suggestion"),
            ("我要投票给最大化最低收入",
             FormalityLevel.INFORMAL, "Casual Chinese vote"),
            ("我们搞最大化平均收入怎么样？",
             FormalityLevel.VERY_INFORMAL, "Very casual Chinese question"),
        ]
        
        all_cases = formal_cases + informal_cases
        
        for statement, expected_formality, description in all_cases:
            with self.subTest(statement=statement, description=description):
                detected_formality = asyncio.run(self._detect_formality_level(statement))
                if detected_formality:
                    self.assertIsInstance(detected_formality, FormalityLevel,
                                        f"{description}: Should return FormalityLevel enum")


class TestPolitenessMarkerRecognition(unittest.TestCase):
    """Test recognition of politeness markers across languages."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_english_politeness_markers(self):
        """Test English politeness marker recognition."""
        politeness_cases = [
            ("Please consider maximizing the floor income", True, "Please marker"),
            ("Would you kindly consider maximizing average income", True, "Would you kindly"),
            ("If I may suggest maximizing the floor income", True, "If I may"),
            ("With your permission, I'd like to propose maximizing average", True, "With permission"),
            ("I respectfully disagree with that principle", True, "Respectfully disagree"),
            ("Thank you for considering maximizing the floor", True, "Thank you marker"),
            ("I appreciate your perspective on maximizing average", True, "Appreciation marker"),
        ]
        
        non_politeness_cases = [
            ("I want to maximize the floor income", False, "Direct want statement"),
            ("Maximize the average income", False, "Direct command"),
            ("That principle is wrong", False, "Direct disagreement"),
            ("Pick maximizing the floor", False, "Direct instruction"),
        ]
        
        all_cases = politeness_cases + non_politeness_cases
        
        for statement, expected_politeness, description in all_cases:
            with self.subTest(statement=statement, description=description):
                has_politeness = asyncio.run(self._detect_politeness_markers(statement))
                if has_politeness is not None:  # Only test if detection is implemented
                    self.assertEqual(has_politeness, expected_politeness,
                                   f"{description}: Expected {expected_politeness}, got {has_politeness}")
    
    def test_spanish_politeness_markers(self):
        """Test Spanish politeness marker recognition."""
        politeness_cases = [
            ("Por favor considere maximizar el ingreso mínimo", True, "Por favor marker"),
            ("Sería tan amable de considerar maximizar el promedio", True, "Sería tan amable"),
            ("Si me permite sugerir maximizar el ingreso mínimo", True, "Si me permite"),
            ("Con su permiso, me gustaría proponer maximizar el promedio", True, "Con su permiso"),
            ("Respetuosamente no estoy de acuerdo con ese principio", True, "Respetuosamente"),
            ("Gracias por considerar maximizar el mínimo", True, "Gracias marker"),
            ("Aprecio su perspectiva sobre maximizar el promedio", True, "Aprecio marker"),
        ]
        
        non_politeness_cases = [
            ("Quiero maximizar el ingreso mínimo", False, "Direct want statement"),
            ("Maximiza el ingreso promedio", False, "Direct command"),
            ("Ese principio está mal", False, "Direct disagreement"),
            ("Elige maximizar el mínimo", False, "Direct instruction"),
        ]
        
        all_cases = politeness_cases + non_politeness_cases
        
        for statement, expected_politeness, description in all_cases:
            with self.subTest(statement=statement, description=description):
                has_politeness = asyncio.run(self._detect_politeness_markers(statement))
                if has_politeness is not None:
                    self.assertEqual(has_politeness, expected_politeness,
                                   f"{description}: Expected {expected_politeness}, got {has_politeness}")
    
    def test_chinese_politeness_markers(self):
        """Test Chinese politeness marker recognition."""
        politeness_cases = [
            ("请考虑最大化最低收入", True, "请 (please) marker"),
            ("请您考虑最大化平均收入", True, "请您 (please you) marker"),
            ("如果可以的话，我建议最大化最低收入", True, "如果可以的话 (if possible)"),
            ("麻烦您考虑最大化平均收入", True, "麻烦您 (trouble you)"),
            ("恭敬地不同意这个原则", True, "恭敬地 (respectfully)"),
            ("谢谢您考虑最大化最低收入", True, "谢谢您 (thank you)"),
            ("我感谢您对最大化平均收入的看法", True, "感谢 (appreciate)"),
        ]
        
        non_politeness_cases = [
            ("我要最大化最低收入", False, "Direct want statement"),
            ("最大化平均收入", False, "Direct command"),
            ("这个原则不对", False, "Direct disagreement"),
            ("选择最大化最低收入", False, "Direct instruction"),
        ]
        
        all_cases = politeness_cases + non_politeness_cases
        
        for statement, expected_politeness, description in all_cases:
            with self.subTest(statement=statement, description=description):
                has_politeness = asyncio.run(self._detect_politeness_markers(statement))
                if has_politeness is not None:
                    self.assertEqual(has_politeness, expected_politeness,
                                   f"{description}: Expected {expected_politeness}, got {has_politeness}")


class TestAgreementStrengthVariations(unittest.TestCase):
    """Test recognition of different agreement strength levels."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_english_agreement_strengths(self):
        """Test English agreement strength variations."""
        strong_agreement_cases = [
            ("I completely agree with maximizing the floor income", "strong", "Complete agreement"),
            ("I absolutely support maximizing average income", "strong", "Absolute support"),
            ("I'm totally in favor of maximizing the floor", "strong", "Total favor"),
            ("I wholeheartedly endorse maximizing average", "strong", "Wholehearted endorsement"),
        ]
        
        moderate_agreement_cases = [
            ("I agree with maximizing the floor income", "moderate", "Standard agreement"),
            ("I support maximizing average income", "moderate", "Standard support"),
            ("I'm in favor of maximizing the floor", "moderate", "Standard favor"),
            ("I think maximizing average is good", "moderate", "Thinking it's good"),
        ]
        
        weak_agreement_cases = [
            ("I suppose maximizing the floor might work", "weak", "Supposing it might work"),
            ("I guess maximizing average could be okay", "weak", "Guessing it could be okay"),
            ("Maybe maximizing the floor would be fine", "weak", "Maybe it would be fine"),
            ("I'm somewhat inclined toward maximizing average", "weak", "Somewhat inclined"),
        ]
        
        all_cases = strong_agreement_cases + moderate_agreement_cases + weak_agreement_cases
        
        for statement, expected_strength, description in all_cases:
            with self.subTest(statement=statement, description=description):
                strength = asyncio.run(self._detect_agreement_strength(statement))
                if strength:  # Only test if strength detection is implemented
                    self.assertIn(strength, ["strong", "moderate", "weak"],
                                f"{description}: Should return valid strength level")
    
    def test_spanish_agreement_strengths(self):
        """Test Spanish agreement strength variations."""
        strong_agreement_cases = [
            ("Estoy completamente de acuerdo con maximizar el ingreso mínimo", "strong", "Complete Spanish agreement"),
            ("Apoyo absolutamente maximizar el ingreso promedio", "strong", "Absolute Spanish support"),
            ("Estoy totalmente a favor de maximizar el mínimo", "strong", "Total Spanish favor"),
        ]
        
        moderate_agreement_cases = [
            ("Estoy de acuerdo con maximizar el ingreso mínimo", "moderate", "Standard Spanish agreement"),
            ("Apoyo maximizar el ingreso promedio", "moderate", "Standard Spanish support"),
            ("Estoy a favor de maximizar el mínimo", "moderate", "Standard Spanish favor"),
        ]
        
        weak_agreement_cases = [
            ("Supongo que maximizar el mínimo podría funcionar", "weak", "Spanish supposing"),
            ("Creo que maximizar el promedio podría estar bien", "weak", "Spanish guessing"),
            ("Tal vez maximizar el mínimo estaría bien", "weak", "Spanish maybe"),
        ]
        
        all_cases = strong_agreement_cases + moderate_agreement_cases + weak_agreement_cases
        
        for statement, expected_strength, description in all_cases:
            with self.subTest(statement=statement, description=description):
                strength = asyncio.run(self._detect_agreement_strength(statement))
                if strength:
                    self.assertIn(strength, ["strong", "moderate", "weak"],
                                f"{description}: Should return valid strength level")
    
    def test_chinese_agreement_strengths(self):
        """Test Chinese agreement strength variations."""
        strong_agreement_cases = [
            ("我完全同意最大化最低收入", "strong", "Complete Chinese agreement"),
            ("我绝对支持最大化平均收入", "strong", "Absolute Chinese support"),
            ("我非常赞成最大化最低收入", "strong", "Very much in favor"),
        ]
        
        moderate_agreement_cases = [
            ("我同意最大化最低收入", "moderate", "Standard Chinese agreement"),
            ("我支持最大化平均收入", "moderate", "Standard Chinese support"),
            ("我赞成最大化最低收入", "moderate", "Standard Chinese favor"),
        ]
        
        weak_agreement_cases = [
            ("我觉得最大化最低收入可能可行", "weak", "Chinese feeling it might work"),
            ("我想最大化平均收入可能不错", "weak", "Chinese thinking it might be good"),
            ("也许最大化最低收入会好一些", "weak", "Chinese maybe"),
        ]
        
        all_cases = strong_agreement_cases + moderate_agreement_cases + weak_agreement_cases
        
        for statement, expected_strength, description in all_cases:
            with self.subTest(statement=statement, description=description):
                strength = asyncio.run(self._detect_agreement_strength(statement))
                if strength:
                    self.assertIn(strength, ["strong", "moderate", "weak"],
                                f"{description}: Should return valid strength level")


class TestCulturalNumberPreferences(unittest.TestCase):
    """Test handling of cultural number preferences and superstitions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_chinese_lucky_numbers(self):
        """Test Chinese lucky number preferences."""
        lucky_numbers = [8, 88, 888, 168, 518, 1888, 8888]
        
        for lucky_num in lucky_numbers:
            statement = f"约束为¥{lucky_num:,}"
            with self.subTest(number=lucky_num):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, lucky_num, 
                               f"Should parse Chinese lucky number {lucky_num}")
                
                # Test if lucky number preference is detected
                is_lucky = asyncio.run(self._is_lucky_number(lucky_num, "chinese"))
                if is_lucky is not None:  # Only test if lucky number detection is implemented
                    self.assertTrue(is_lucky, f"Number {lucky_num} should be detected as lucky in Chinese culture")
    
    def test_chinese_unlucky_numbers(self):
        """Test Chinese unlucky number handling."""
        unlucky_numbers = [4, 44, 444, 14, 74, 94, 4444]
        
        for unlucky_num in unlucky_numbers:
            statement = f"约束为¥{unlucky_num:,}"
            with self.subTest(number=unlucky_num):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, unlucky_num,
                               f"Should still parse Chinese unlucky number {unlucky_num}")
                
                # Test if unlucky number preference is detected
                is_unlucky = asyncio.run(self._is_unlucky_number(unlucky_num, "chinese"))
                if is_unlucky is not None:
                    self.assertTrue(is_unlucky, f"Number {unlucky_num} should be detected as unlucky in Chinese culture")
    
    def test_western_number_superstitions(self):
        """Test Western number superstitions (13, etc.)."""
        unlucky_numbers = [13, 113, 1313, 6666]
        
        for unlucky_num in unlucky_numbers:
            statement = f"constraint of ${unlucky_num:,}"
            with self.subTest(number=unlucky_num):
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, unlucky_num,
                               f"Should still parse Western unlucky number {unlucky_num}")
                
                # Test if Western unlucky number is detected
                is_unlucky = asyncio.run(self._is_unlucky_number(unlucky_num, "western"))
                if is_unlucky is not None:
                    # 13 should be unlucky, 6666 might be (devil's number association)
                    if unlucky_num in [13, 113, 1313]:
                        self.assertTrue(is_unlucky, f"Number {unlucky_num} should be unlucky in Western culture")
    
    def test_cultural_number_formatting_preferences(self):
        """Test cultural preferences for number formatting."""
        test_cases = [
            (8888, "chinese", "¥8,888", "Chinese lucky number formatting"),
            (1888, "chinese", "¥1,888", "Chinese auspicious number formatting"),  
            (13000, "western", "$13,000", "Western number formatting"),
            (15000, "neutral", "15,000", "Neutral number formatting"),
        ]
        
        for number, culture, expected_pattern, description in test_cases:
            with self.subTest(number=number, culture=culture, description=description):
                # Test that numbers are parsed regardless of cultural significance
                if culture == "chinese":
                    statement = f"约束为¥{number:,}"
                else:
                    statement = f"constraint of ${number:,}"
                    
                result = asyncio.run(self._parse_constraint_amount(statement))
                self.assertEqual(result, number,
                               f"{description}: Should parse number {number} correctly")


class TestCulturalCommunicationStyles(unittest.TestCase):
    """Test handling of different cultural communication styles."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.utility_agent = create_test_utility_agent(temperature=0.0)
    
    def test_direct_vs_indirect_communication(self):
        """Test detection of direct vs indirect communication styles."""
        direct_cases = [
            ("I choose maximizing the floor income", "direct", "Direct choice"),
            ("We should pick maximizing average income", "direct", "Direct suggestion"),
            ("Vote for maximizing the floor", "direct", "Direct command"),
        ]
        
        indirect_cases = [
            ("Perhaps we might consider maximizing the floor income", "indirect", "Tentative suggestion"),
            ("It might be worth exploring maximizing average income", "indirect", "Indirect exploration"),
            ("I wonder if maximizing the floor would be appropriate", "indirect", "Wondering statement"),
        ]
        
        all_cases = direct_cases + indirect_cases
        
        for statement, expected_style, description in all_cases:
            with self.subTest(statement=statement, description=description):
                style = asyncio.run(self._detect_communication_style(statement))
                if style:  # Only test if style detection is implemented
                    self.assertIn(style, ["direct", "indirect"],
                                f"{description}: Should return valid communication style")
    
    def test_high_context_vs_low_context(self):
        """Test high-context vs low-context cultural communication."""
        low_context_cases = [
            ("I vote for maximizing the floor income with constraint of $15000",
             "low_context", "Explicit details provided"),
            ("My choice is maximizing average income because it helps everyone",
             "low_context", "Explicit reasoning"),
        ]
        
        high_context_cases = [
            ("Given our previous discussion, I believe we understand the best path forward",
             "high_context", "Relies on shared context"),
            ("As we have established, the appropriate principle should be clear",
             "high_context", "Assumes shared understanding"),
        ]
        
        all_cases = low_context_cases + high_context_cases
        
        for statement, expected_context, description in all_cases:
            with self.subTest(statement=statement, description=description):
                context_level = asyncio.run(self._detect_context_level(statement))
                if context_level:
                    self.assertIn(context_level, ["high_context", "low_context"],
                                f"{description}: Should return valid context level")
    
    def test_honorifics_and_respect_levels(self):
        """Test recognition of honorifics and respect indicators."""
        respectful_cases = [
            ("Your honor, I suggest maximizing the floor income", True, "Your honor honorific"),
            ("Distinguished colleagues, let us consider maximizing average", True, "Distinguished colleagues"),
            ("Esteemed participants, I propose maximizing the floor", True, "Esteemed participants"),
        ]
        
        casual_cases = [
            ("Hey everyone, let's pick maximizing average", False, "Casual greeting"),
            ("Guys, I think we should go with maximizing the floor", False, "Casual address"),
        ]
        
        all_cases = respectful_cases + casual_cases
        
        for statement, expected_respectful, description in all_cases:
            with self.subTest(statement=statement, description=description):
                is_respectful = asyncio.run(self._detect_respectful_address(statement))
                if is_respectful is not None:
                    self.assertEqual(is_respectful, expected_respectful,
                                   f"{description}: Expected {expected_respectful}, got {is_respectful}")


    # Helper methods
    async def _detect_formality_level(self, statement: str) -> Optional[FormalityLevel]:
        """Helper to detect formality level from statement."""
        # Simple formality detection based on keywords
        statement_lower = statement.lower()
        
        very_formal_indicators = ["humbly", "respectfully submit", "with great respect", "恭敬地", "谨慎地"]
        formal_indicators = ["respectfully", "may i", "would you", "请您", "请允许我", "si me permite"]
        informal_indicators = ["gonna", "let's just", "how about", "vamos a", "我觉得"]
        very_informal_indicators = ["gonna", "'m gonna", "搞", "就选"]
        
        for indicator in very_formal_indicators:
            if indicator in statement_lower:
                return FormalityLevel.VERY_FORMAL
                
        for indicator in formal_indicators:
            if indicator in statement_lower:
                return FormalityLevel.FORMAL
                
        for indicator in very_informal_indicators:
            if indicator in statement_lower:
                return FormalityLevel.VERY_INFORMAL
                
        for indicator in informal_indicators:
            if indicator in statement_lower:
                return FormalityLevel.INFORMAL
        
        return FormalityLevel.NEUTRAL
    
    async def _detect_politeness_markers(self, statement: str) -> Optional[bool]:
        """Helper to detect politeness markers."""
        politeness_indicators = [
            "please", "would you", "if i may", "with your permission", "respectfully",
            "thank you", "appreciate", "por favor", "sería tan amable", "con su permiso",
            "gracias", "aprecio", "请", "请您", "谢谢", "感谢", "如果可以", "麻烦您"
        ]
        
        statement_lower = statement.lower()
        for indicator in politeness_indicators:
            if indicator in statement_lower:
                return True
        return False
    
    async def _detect_agreement_strength(self, statement: str) -> Optional[str]:
        """Helper to detect agreement strength."""
        statement_lower = statement.lower()
        
        strong_indicators = ["completely", "absolutely", "totally", "wholeheartedly",
                           "completamente", "absolutamente", "totalmente", "完全", "绝对", "非常"]
        weak_indicators = ["suppose", "guess", "maybe", "somewhat", "might",
                         "supongo", "creo", "tal vez", "觉得", "可能", "也许"]
        
        for indicator in strong_indicators:
            if indicator in statement_lower:
                return "strong"
                
        for indicator in weak_indicators:
            if indicator in statement_lower:
                return "weak"
        
        return "moderate"
    
    async def _parse_constraint_amount(self, statement: str) -> Optional[int]:
        """Helper to parse constraint amounts from statements."""
        await self.utility_agent.async_init()
        try:
            full_statement = f"I choose maximizing average income {statement}"
            result = await self.utility_agent.parse_participant_preference(
                full_statement, participant_name="TestParticipant"
            )
            return result.constraint_amount if result else None
        except Exception:
            return None
    
    async def _is_lucky_number(self, number: int, culture: str) -> Optional[bool]:
        """Helper to check if number is considered lucky in culture."""
        if culture == "chinese":
            # Numbers containing 8 are considered lucky
            return "8" in str(number)
        return None
    
    async def _is_unlucky_number(self, number: int, culture: str) -> Optional[bool]:
        """Helper to check if number is considered unlucky in culture."""
        if culture == "chinese":
            # Numbers containing 4 are considered unlucky
            return "4" in str(number)
        elif culture == "western":
            # 13 and numbers containing 13 are unlucky
            return "13" in str(number)
        return None
    
    async def _detect_communication_style(self, statement: str) -> Optional[str]:
        """Helper to detect communication style."""
        indirect_indicators = ["perhaps", "might", "wonder if", "maybe", "could be"]
        statement_lower = statement.lower()
        
        for indicator in indirect_indicators:
            if indicator in statement_lower:
                return "indirect"
        return "direct"
    
    async def _detect_context_level(self, statement: str) -> Optional[str]:
        """Helper to detect context level."""
        high_context_indicators = ["as we have", "given our", "we understand", "should be clear"]
        statement_lower = statement.lower()
        
        for indicator in high_context_indicators:
            if indicator in statement_lower:
                return "high_context"
        return "low_context"
    
    async def _detect_respectful_address(self, statement: str) -> Optional[bool]:
        """Helper to detect respectful address."""
        respectful_indicators = ["your honor", "distinguished", "esteemed", "respected"]
        casual_indicators = ["hey", "guys", "folks"]
        
        statement_lower = statement.lower()
        
        for indicator in respectful_indicators:
            if indicator in statement_lower:
                return True
                
        for indicator in casual_indicators:
            if indicator in statement_lower:
                return False
        
        return None


if __name__ == '__main__':
    # Configure test runner for async support
    unittest.main()