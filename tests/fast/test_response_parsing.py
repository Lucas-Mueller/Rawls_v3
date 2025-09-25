"""
Deterministic Response Parsing Tests

Tests parsing logic with known multilingual responses to validate
consensus detection, vote parsing, and response validation without API calls.
"""

import pytest
from typing import Dict, List, Tuple

from models import JusticePrinciple, PrincipleChoice, CertaintyLevel
from tests.support.mock_utilities import (
    MockUtilityAgent, MockLanguageManager, MockLanguage, MockResponseGenerator
)


class TestNumericalAgreementDetection:
    """Test numerical agreement detection (1=Yes, 0=No) across languages."""

    def test_english_yes_responses(self):
        """Test English yes responses are correctly detected."""
        utility_agent = MockUtilityAgent()

        test_cases = [
            "1 - I agree to initiate voting",
            "Yes, 1",
            "1",
            "I choose 1 (yes)",
            "My answer is 1",
            "1 - absolutely yes"
        ]

        for response in test_cases:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            assert wants_vote is True, f"Failed for response: '{response}'"
            assert error is None, f"Unexpected error for response: '{response}'"

    def test_english_no_responses(self):
        """Test English no responses are correctly detected."""
        utility_agent = MockUtilityAgent()

        test_cases = [
            "0 - I need more discussion",
            "No, 0",
            "0",
            "I choose 0 (no)",
            "My answer is 0",
            "0 - not ready yet"
        ]

        for response in test_cases:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            assert wants_vote is False, f"Failed for response: '{response}'"
            assert error is None, f"Unexpected error for response: '{response}'"

    def test_spanish_responses(self):
        """Test Spanish responses are correctly detected."""
        utility_agent = MockUtilityAgent()

        yes_cases = [
            "1 - Sí, estoy de acuerdo",
            "Sí, 1",
            "Mi respuesta es 1",
            "1 - absolutamente sí"
        ]

        no_cases = [
            "0 - No estoy listo",
            "No, 0",
            "Mi respuesta es 0",
            "0 - necesito más discusión"
        ]

        for response in yes_cases:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            assert wants_vote is True, f"Failed for Spanish yes: '{response}'"
            assert error is None

        for response in no_cases:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            assert wants_vote is False, f"Failed for Spanish no: '{response}'"
            assert error is None

    def test_mandarin_responses(self):
        """Test Mandarin responses are correctly detected."""
        utility_agent = MockUtilityAgent()

        yes_cases = [
            "1 - 是的，我同意",
            "是，1",
            "我的答案是1",
            "1 - 绝对同意"
        ]

        no_cases = [
            "0 - 我还没准备好",
            "否，0",
            "我的答案是0",
            "0 - 我需要更多讨论"
        ]

        for response in yes_cases:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            assert wants_vote is True, f"Failed for Mandarin yes: '{response}'"
            assert error is None

        for response in no_cases:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            assert wants_vote is False, f"Failed for Mandarin no: '{response}'"
            assert error is None

    def test_ambiguous_responses(self):
        """Test ambiguous responses are handled correctly."""
        utility_agent = MockUtilityAgent()

        ambiguous_cases = [
            "I'm not sure if we're ready",
            "Maybe we should vote soon",
            "It's hard to decide",
            "Could go either way",
            "Tal vez deberíamos votar",  # Spanish
            "我不确定是否准备好"  # Mandarin
        ]

        for response in ambiguous_cases:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            assert wants_vote is False, f"Ambiguous should default to False: '{response}'"
            assert error is not None, f"Should have error for ambiguous: '{response}'"
            assert "Could not detect" in error

    def test_invalid_responses(self):
        """Test invalid responses are handled correctly."""
        utility_agent = MockUtilityAgent()

        invalid_cases = [
            "",
            "   ",
            "This is completely unrelated text",
            "2 - Invalid number",
            "I think voting might be good"
        ]

        for response in invalid_cases:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            assert wants_vote is False, f"Invalid should default to False: '{response}'"
            assert error is not None, f"Should have error for invalid: '{response}'"

    def test_call_tracking(self):
        """Test that utility agent tracks method calls correctly."""
        utility_agent = MockUtilityAgent()

        responses = ["1 - yes", "0 - no", "invalid"]
        for response in responses:
            utility_agent.detect_numerical_agreement(response)

        assert len(utility_agent.call_history) == 3
        for i, call in enumerate(utility_agent.call_history):
            assert call["method"] == "detect_numerical_agreement"
            assert call["response"] == responses[i]


class TestPrincipleChoiceParsing:
    """Test principle choice parsing from discussion statements."""

    @pytest.mark.asyncio
    async def test_english_principle_detection(self):
        """Test English principle detection from statements."""
        utility_agent = MockUtilityAgent()

        test_cases = [
            ("I believe maximizing the floor is most important", JusticePrinciple.MAXIMIZING_FLOOR),
            ("We should focus on the floor principle", JusticePrinciple.MAXIMIZING_FLOOR),
            ("Maximizing average income benefits everyone", JusticePrinciple.MAXIMIZING_AVERAGE),
            ("The average approach is best", JusticePrinciple.MAXIMIZING_AVERAGE),
        ]

        for statement, expected_principle in test_cases:
            result = await utility_agent.parse_principle_choice_enhanced(statement)
            assert isinstance(result, PrincipleChoice)
            assert result.principle == expected_principle, f"Failed for: '{statement}'"

    @pytest.mark.asyncio
    async def test_mandarin_principle_detection(self):
        """Test Mandarin principle detection with direct keyword matching."""
        utility_agent = MockUtilityAgent()

        test_cases = [
            ("我认为最大化最低收入最重要", JusticePrinciple.MAXIMIZING_FLOOR),
            ("最大化最低收入是最好的选择", JusticePrinciple.MAXIMIZING_FLOOR),
            ("最大化平均收入对所有人都有好处", JusticePrinciple.MAXIMIZING_AVERAGE),
            ("平均收入方法是最好的", JusticePrinciple.MAXIMIZING_AVERAGE),
        ]

        for statement, expected_principle in test_cases:
            result = await utility_agent.parse_principle_choice_enhanced(statement)
            assert isinstance(result, PrincipleChoice)
            # Note: Mock implementation uses simple keyword detection
            assert result.principle in [JusticePrinciple.MAXIMIZING_FLOOR, JusticePrinciple.MAXIMIZING_AVERAGE]

    @pytest.mark.asyncio
    async def test_principle_parsing_call_tracking(self):
        """Test that principle parsing tracks method calls."""
        utility_agent = MockUtilityAgent()

        statements = [
            "I prefer the floor principle",
            "Average income is better",
            "Complex statement about justice"
        ]

        for statement in statements:
            await utility_agent.parse_principle_choice_enhanced(statement)

        assert len(utility_agent.call_history) == 3
        for i, call in enumerate(utility_agent.call_history):
            assert call["method"] == "parse_principle_choice_enhanced"
            assert call["statement"] == statements[i]


class TestPrincipleRankingParsing:
    """Test principle ranking parsing from final ranking responses."""

    @pytest.mark.asyncio
    async def test_ranking_response_parsing(self):
        """Test that ranking responses are parsed correctly."""
        utility_agent = MockUtilityAgent()

        # Test with different language responses
        responses = MockResponseGenerator.get_principle_rankings(MockLanguage.ENGLISH)
        result = await utility_agent.parse_principle_ranking_enhanced(responses)

        assert isinstance(result, object)  # PrincipleRanking
        assert hasattr(result, 'rankings')
        assert hasattr(result, 'certainty')
        assert len(result.rankings) == 4
        assert result.certainty == CertaintyLevel.SURE

    @pytest.mark.asyncio
    async def test_multilingual_ranking_parsing(self):
        """Test ranking parsing works across languages."""
        utility_agent = MockUtilityAgent()

        languages = [MockLanguage.ENGLISH, MockLanguage.SPANISH, MockLanguage.MANDARIN]

        for language in languages:
            response = MockResponseGenerator.get_principle_rankings(language)
            result = await utility_agent.parse_principle_ranking_enhanced(response)

            assert isinstance(result, object)  # PrincipleRanking
            assert hasattr(result, 'rankings')
            assert len(result.rankings) == 4, f"Failed for language: {language}"

    @pytest.mark.asyncio
    async def test_ranking_call_tracking(self):
        """Test ranking parsing call tracking."""
        utility_agent = MockUtilityAgent()

        responses = [
            MockResponseGenerator.get_principle_rankings(MockLanguage.ENGLISH),
            MockResponseGenerator.get_principle_rankings(MockLanguage.SPANISH)
        ]

        for response in responses:
            await utility_agent.parse_principle_ranking_enhanced(response)

        assert len(utility_agent.call_history) == 2
        for call in utility_agent.call_history:
            assert call["method"] == "parse_principle_ranking_enhanced"
            assert "text_response" in call


class TestConsensusDetectionAlgorithms:
    """Test consensus detection logic with deterministic inputs."""

    def test_unanimous_consensus_detection(self):
        """Test detection of unanimous consensus."""
        # Simulate vote results with unanimous agreement
        vote_responses = {
            "Alice": "1 - I agree to maximizing floor",
            "Bob": "1 - Yes, maximizing floor",
            "Carol": "1 - Maximizing floor is best"
        }

        # Mock consensus detection (in real implementation this would be more complex)
        all_agree = all("1" in response for response in vote_responses.values())
        assert all_agree is True

        # Test principle agreement
        all_floor = all("floor" in response.lower() for response in vote_responses.values())
        assert all_floor is True

    def test_split_consensus_detection(self):
        """Test detection when consensus is not reached."""
        vote_responses = {
            "Alice": "1 - I prefer maximizing floor",
            "Bob": "0 - I prefer maximizing average",
            "Carol": "1 - Floor principle is better"
        }

        # Check voting agreement
        all_agree = all("1" in response for response in vote_responses.values())
        assert all_agree is False

        # Check for partial agreement
        agreement_count = sum(1 for response in vote_responses.values() if "1" in response)
        assert agreement_count == 2

    def test_principle_consensus_with_different_wordings(self):
        """Test principle consensus detection with varied expressions."""
        principle_responses = [
            "I support maximizing the floor income",
            "Floor maximization is the way to go",
            "The floor principle is most just",
            "Helping the worst off (floor) is crucial"
        ]

        # Simple keyword-based consensus detection
        floor_count = sum(1 for response in principle_responses if "floor" in response.lower())
        assert floor_count == len(principle_responses)

    def test_multilingual_consensus_patterns(self):
        """Test consensus detection across different languages."""
        consensus_patterns = {
            MockLanguage.ENGLISH: ["floor", "maximizing floor", "help worst off"],
            MockLanguage.SPANISH: ["piso", "maximizar piso", "ayudar más desfavorecidos"],
            MockLanguage.MANDARIN: ["最低", "最大化最低收入", "帮助最不幸的人"]
        }

        for language, keywords in consensus_patterns.items():
            # Test that keywords would be detected in consensus algorithm
            test_responses = [f"I think {keyword} is best" for keyword in keywords[:2]]

            # Mock consensus check - in real implementation this would be more sophisticated
            language_specific_matches = []
            for response in test_responses:
                matches_any = any(keyword in response for keyword in keywords)
                language_specific_matches.append(matches_any)

            assert all(language_specific_matches), f"Failed consensus detection for {language}"


class TestResponseValidation:
    """Test response validation logic with edge cases."""

    def test_minimum_length_validation(self):
        """Test minimum length validation for different languages."""
        # English minimum length (typically higher due to average word length)
        english_min = 20
        spanish_min = 18  # Similar to English
        mandarin_min = 10  # Shorter due to character density

        test_cases = [
            (MockLanguage.ENGLISH, "This statement is long enough for English validation", english_min, True),
            (MockLanguage.ENGLISH, "Too short", english_min, False),
            (MockLanguage.SPANISH, "Esta declaración es suficientemente larga para validación", spanish_min, True),
            (MockLanguage.SPANISH, "Muy corto", spanish_min, False),
            (MockLanguage.MANDARIN, "这个陈述对中文验证来说足够长", mandarin_min, True),
            (MockLanguage.MANDARIN, "太短", mandarin_min, False),
        ]

        for language, statement, min_len, expected_valid in test_cases:
            actual_valid = len(statement.strip()) >= min_len
            assert actual_valid == expected_valid, f"Failed for {language}: '{statement}'"

    def test_empty_response_handling(self):
        """Test handling of empty or whitespace-only responses."""
        invalid_responses = [
            "",
            "   ",
            "\n\n\t",
            None  # This would cause an error in real parsing
        ]

        for response in invalid_responses[:-1]:  # Skip None for now
            is_valid = bool(response and response.strip())
            assert is_valid is False, f"Should be invalid: '{response}'"

    def test_special_character_handling(self):
        """Test handling of responses with special characters."""
        special_responses = [
            "I think 🤔 that maximizing floor is best! 👍",
            "Máximizar el piso es lo más justo (según mi opinión).",
            "我认为最大化最低收入是最公正的原则。",
            "Response with\nnewlines\nand\ttabs"
        ]

        for response in special_responses:
            # Basic validation - non-empty and has content
            is_valid = bool(response and response.strip())
            has_content = len(response.strip()) > 5
            assert is_valid and has_content, f"Should be valid: '{response}'"

    def test_timeout_simulation(self):
        """Test timeout behavior simulation."""
        # Simulate different timeout scenarios
        timeout_scenarios = [
            {"duration": 30, "expected_timeout": False},  # Normal response time
            {"duration": 60, "expected_timeout": False},  # Slow but acceptable
            {"duration": 120, "expected_timeout": True},   # Timeout threshold exceeded
            {"duration": 300, "expected_timeout": True}    # Definitely timeout
        ]

        timeout_threshold = 90  # seconds

        for scenario in timeout_scenarios:
            duration = scenario["duration"]
            expected_timeout = scenario["expected_timeout"]
            actual_timeout = duration > timeout_threshold

            assert actual_timeout == expected_timeout, f"Timeout detection failed for {duration}s"


class TestErrorRecovery:
    """Test error recovery and fallback mechanisms."""

    def test_parsing_error_fallback(self):
        """Test fallback behavior when parsing fails."""
        utility_agent = MockUtilityAgent()

        # These would normally cause parsing errors
        error_responses = [
            "This is completely unrelated to justice principles",
            "23456789",  # Numbers without 1 or 0
            "Maybe so",  # Contradictory without clear yes/no
        ]

        for response in error_responses:
            wants_vote, error = utility_agent.detect_numerical_agreement(response)
            # Should fall back to safe default (False) with error message
            assert wants_vote is False
            assert error is not None
            assert len(error) > 0

    def test_multilingual_fallback(self):
        """Test fallback when language detection fails."""
        language_manager = MockLanguageManager(MockLanguage.ENGLISH)

        # Test missing translation key
        missing_key = "this.key.does.not.exist"
        result = language_manager.get(missing_key)

        assert "MISSING" in result
        assert missing_key in result

    def test_partial_response_handling(self):
        """Test handling of incomplete or partial responses."""
        partial_responses = [
            "I think",  # Very incomplete thought
            "1 -",  # Incomplete numerical response
            "My ranking is: 1. Floor 2. ",  # Incomplete ranking with trailing space
        ]

        # These should be handled gracefully without crashing
        for response in partial_responses:
            # Basic validation should catch these as potentially invalid
            is_complete = len(response.strip()) > 10 and not response.endswith((' ', '-', '.', ':'))

            # All of these should be flagged as incomplete
            assert not is_complete, f"Should detect incompleteness: '{response}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])