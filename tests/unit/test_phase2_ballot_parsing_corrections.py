"""
Critical parsing suite for real-world ballot parsing fixes using actual UtilityAgent methods.

This test suite restores comprehensive ballot parsing coverage that exercises
production UtilityAgent parsing logic to catch real bugs in ballot statement processing.

Tests cover:
1. Real-world ballot statement parsing patterns
2. Malformed JSON recovery from LLM responses
3. Constraint amount edge cases and validation
4. Multilingual ballot statement variations
5. Complex voting scenarios with edge cases
6. Error recovery from known parsing failures

CRITICAL: These tests exercise actual UtilityAgent.parse_* methods with realistic
ballot inputs and LLM-like JSON responses that mirror production scenarios.
"""

import pytest
import json
import asyncio
from typing import Optional, List

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
from utils.language_manager import create_language_manager, SupportedLanguage
from utils.error_handling import ExperimentError
from tests.utils.stubbed_runner import StubbedRunner


@pytest.fixture
def english_utility_agent():
    """Create English-configured utility agent for ballot parsing tests."""
    language_manager = create_language_manager(SupportedLanguage.ENGLISH)
    return UtilityAgent(
        utility_model="stub-model",
        temperature=0.0,
        experiment_language="english",
        language_manager=language_manager
    )


@pytest.fixture
def spanish_utility_agent():
    """Create Spanish-configured utility agent for multilingual ballot tests."""
    language_manager = create_language_manager(SupportedLanguage.SPANISH)
    return UtilityAgent(
        utility_model="stub-model",
        temperature=0.0,
        experiment_language="spanish",
        language_manager=language_manager
    )


@pytest.fixture
def stubbed_runner(monkeypatch):
    """Create stubbed runner and patch UtilityAgent to use it."""
    runner = StubbedRunner()

    # Patch the utility agent's run_without_tracing function
    async def mock_run_without_tracing(agent, prompt, context=None):
        return await runner.run(agent, prompt, context)

    monkeypatch.setattr(
        "experiment_agents.utility_agent.run_without_tracing",
        mock_run_without_tracing
    )
    return runner


class TestRealWorldBallotStatements:
    """Test parsing of real-world ballot statements from production experiments."""

    @pytest.mark.asyncio
    async def test_formal_ballot_statement_patterns(self, english_utility_agent, stubbed_runner):
        """Test parsing of formal voting ballot statements."""

        # Real-world ballot statement patterns from production
        test_cases = [
            (
                "My vote is for maximizing the floor income with a constraint of $50,000",
                '{"principle": "maximizing_floor", "constraint_amount": 50000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR,
                50000
            ),
            (
                "I cast my ballot for maximizing average income principle",
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE,
                None
            ),
            (
                "For my secret ballot, I choose maximizing average with floor constraint at $35,000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 35000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                35000
            ),
            (
                "My formal vote: maximizing average income with range constraint of $75,000",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": 75000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
                75000
            )
        ]

        # Register initialization + actual responses
        responses = ["test"] + [response for _, response, _, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle, expected_amount in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Ballot parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )
            assert result.constraint_amount == expected_amount, (
                f"Constraint parsing failed for '{statement}': "
                f"expected {expected_amount}, got {result.constraint_amount}"
            )

    @pytest.mark.asyncio
    async def test_informal_ballot_statement_variations(self, english_utility_agent, stubbed_runner):
        """Test parsing of informal ballot statement variations."""

        # Less formal ballot statements that still need to be parsed correctly
        test_cases = [
            (
                "Ok, I'm going with maximizing floor",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Let's go with average income maximization, sounds good",
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE
            ),
            (
                "I'll vote for the average with floor option, maybe $40k constraint",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 40000, "certainty": "unsure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            ),
            (
                "Range constraint version of maximizing average - let's say $60,000",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": 60000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Informal ballot parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )

    @pytest.mark.asyncio
    async def test_ballot_statements_with_reasoning(self, english_utility_agent, stubbed_runner):
        """Test parsing ballot statements that include reasoning or justification."""

        # Ballot statements with explanatory reasoning
        test_cases = [
            (
                "I vote for maximizing floor income because it protects the most vulnerable people in our society",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "very_sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "My choice is maximizing average income since it leads to the highest total welfare for everyone",
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE
            ),
            (
                "I believe we should maximize average with a floor constraint of $45,000 to balance efficiency and equity",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 45000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Reasoned ballot parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )


class TestMalformedJSONRecovery:
    """Test recovery from malformed JSON responses in ballot parsing."""

    @pytest.mark.asyncio
    async def test_incomplete_json_recovery(self, english_utility_agent, stubbed_runner):
        """Test recovery from incomplete or truncated JSON responses."""

        # Test cases with incomplete JSON that the LLM might produce
        test_cases = [
            (
                "I choose maximizing floor income",
                '{"principle": "maximizing_floor", "constraint_amount": null',  # Missing closing brace
                "Invalid JSON structure"
            ),
            (
                "My vote is for average income",
                '{"principle": "maximizing_average"',  # Incomplete JSON
                "Invalid JSON structure"
            ),
            (
                "I prefer floor constraint option",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount":',  # Cut off
                "Invalid JSON structure"
            )
        ]

        # Register responses with malformed JSON, then retry responses
        all_responses = ["test"]
        for _, malformed_json, _ in test_cases:
            all_responses.append(malformed_json)  # First attempt (malformed)
            all_responses.append('{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}')  # Retry

        stubbed_runner.register("Response Parser", all_responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, malformed_json, expected_error in test_cases:
            # The parsing should succeed on retry with a valid fallback
            result = await english_utility_agent.parse_principle_choice_enhanced(statement, max_retries=2)
            assert result.principle == JusticePrinciple.MAXIMIZING_FLOOR
            assert result.constraint_amount is None

    @pytest.mark.asyncio
    async def test_invalid_json_structure_recovery(self, english_utility_agent, stubbed_runner):
        """Test recovery from structurally invalid JSON responses."""

        test_cases = [
            (
                "I vote for maximizing average",
                '{principle: maximizing_average, constraint_amount: null}',  # Missing quotes
                "Invalid JSON syntax"
            ),
            (
                "Floor income is my choice",
                '{"principle": maximizing_floor, "constraint_amount": null, "certainty": "sure"}',  # Missing quotes on value
                "Invalid JSON syntax"
            ),
            (
                "Range constraint option please",
                '[{"principle": "maximizing_average_range_constraint"}]',  # Array instead of object
                "Invalid JSON structure"
            )
        ]

        # Register responses with invalid JSON, then retry responses
        all_responses = ["test"]
        for _, invalid_json, _ in test_cases:
            all_responses.append(invalid_json)  # First attempt (invalid)
            all_responses.append('{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}')  # Retry

        stubbed_runner.register("Response Parser", all_responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, invalid_json, expected_error in test_cases:
            # The parsing should succeed on retry
            result = await english_utility_agent.parse_principle_choice_enhanced(statement, max_retries=2)
            assert result.principle == JusticePrinciple.MAXIMIZING_AVERAGE
            assert result.constraint_amount is None


class TestConstraintAmountEdgeCases:
    """Test edge cases in constraint amount parsing from ballot statements."""

    @pytest.mark.asyncio
    async def test_large_constraint_amounts(self, english_utility_agent, stubbed_runner):
        """Test parsing of very large constraint amounts."""

        test_cases = [
            (
                "I vote for floor constraint with $1,000,000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 1000000, "certainty": "sure"}',
                1000000
            ),
            (
                "Range constraint of $5,000,000 for maximizing average",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": 5000000, "certainty": "sure"}',
                5000000
            ),
            (
                "My choice: maximizing average with floor at $10,000,000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 10000000, "certainty": "sure"}',
                10000000
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_amount in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.constraint_amount == expected_amount, (
                f"Large constraint parsing failed for '{statement}': "
                f"expected {expected_amount}, got {result.constraint_amount}"
            )

    @pytest.mark.asyncio
    async def test_zero_and_negative_constraints(self, english_utility_agent, stubbed_runner):
        """Test parsing of zero and negative constraint amounts."""

        test_cases = [
            (
                "Floor constraint of $0",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 0, "certainty": "sure"}',
                0
            ),
            (
                "Range constraint with negative $-1000",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": -1000, "certainty": "sure"}',
                -1000
            ),
            (
                "Constraint amount: $0.00",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 0, "certainty": "sure"}',
                0
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_amount in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.constraint_amount == expected_amount, (
                f"Zero/negative constraint parsing failed for '{statement}': "
                f"expected {expected_amount}, got {result.constraint_amount}"
            )

    @pytest.mark.asyncio
    async def test_fractional_constraint_amounts(self, english_utility_agent, stubbed_runner):
        """Test parsing of fractional constraint amounts (should be converted to integers)."""

        test_cases = [
            (
                "Floor constraint of $50,000.50",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 50000, "certainty": "sure"}',
                50000  # Fractional part should be dropped
            ),
            (
                "Range constraint: $75,999.99",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": 75999, "certainty": "sure"}',
                75999
            ),
            (
                "Constraint amount of $100,000.01",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 100000, "certainty": "sure"}',
                100000
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_amount in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.constraint_amount == expected_amount, (
                f"Fractional constraint parsing failed for '{statement}': "
                f"expected {expected_amount}, got {result.constraint_amount}"
            )


class TestMultilingualBallotStatements:
    """Test ballot parsing across different languages."""

    @pytest.mark.asyncio
    async def test_spanish_ballot_statements(self, spanish_utility_agent, stubbed_runner):
        """Test Spanish ballot statement parsing."""

        test_cases = [
            (
                "Mi voto es para maximizar los ingresos mínimos",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Elijo maximizar el promedio con restricción de €25,000",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 25000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            ),
            (
                "Mi voto secreto: maximizar promedio con restricción de rango de €40,000",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": 40000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in test_cases:
            result = await spanish_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Spanish ballot parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )

    @pytest.mark.asyncio
    async def test_mixed_language_ballot_statements(self, english_utility_agent, stubbed_runner):
        """Test ballot statements with mixed language elements."""

        test_cases = [
            (
                "Mi vote es maximizing_floor with $30,000",
                '{"principle": "maximizing_floor", "constraint_amount": 30000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "I choose maximizar el promedio (maximizing average)",
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE
            ),
            (
                "Vote: maximizing_average_floor_constraint con restricción $50k",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 50000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Mixed language ballot parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )


class TestComplexVotingScenarios:
    """Test parsing in complex voting scenarios with edge cases."""

    @pytest.mark.asyncio
    async def test_conditional_ballot_statements(self, english_utility_agent, stubbed_runner):
        """Test parsing of conditional or uncertain ballot statements."""

        test_cases = [
            (
                "If I have to choose, I guess maximizing floor income",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "unsure"}',
                JusticePrinciple.MAXIMIZING_FLOOR,
                CertaintyLevel.UNSURE
            ),
            (
                "I'm not completely sure, but probably maximizing average",
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "unsure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE,
                CertaintyLevel.UNSURE
            ),
            (
                "Definitely choosing maximizing floor with $60,000 constraint",
                '{"principle": "maximizing_average_floor_constraint", "constraint_amount": 60000, "certainty": "very_sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                CertaintyLevel.VERY_SURE
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle, expected_certainty in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Conditional ballot parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )
            assert result.certainty == expected_certainty, (
                f"Certainty parsing failed for '{statement}': "
                f"expected {expected_certainty.value}, got {result.certainty.value}"
            )

    @pytest.mark.asyncio
    async def test_multiple_choice_mentions_in_ballots(self, english_utility_agent, stubbed_runner):
        """Test parsing when ballot mentions multiple principles but expresses clear preference."""

        test_cases = [
            (
                "I considered maximizing average and floor, but my vote is for maximizing floor income",
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Both range and floor constraints are good options, however I choose maximizing average with range constraint at $80,000",
                '{"principle": "maximizing_average_range_constraint", "constraint_amount": 80000, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT
            ),
            (
                "While maximizing floor and average both have merits, my final ballot selection is maximizing average income",
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}',
                JusticePrinciple.MAXIMIZING_AVERAGE
            )
        ]

        # Register responses
        responses = ["test"] + [response for _, response, _ in test_cases]
        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, llm_response, expected_principle in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement)
            assert result.principle == expected_principle, (
                f"Multiple choice ballot parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )


class TestBallotParsingErrorRecovery:
    """Test error recovery mechanisms in ballot parsing."""

    @pytest.mark.asyncio
    async def test_retry_mechanism_on_parsing_failure(self, english_utility_agent, stubbed_runner):
        """Test that parsing retries work correctly for ballot statements."""

        statement = "I vote for maximizing floor income with constraint"

        # Register sequence: init, failed attempt, failed attempt, successful attempt
        responses = [
            "test",  # init
            "invalid json response",  # first attempt fails
            '{"invalid": "structure"}',  # second attempt fails
            '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "sure"}'  # third succeeds
        ]

        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        result = await english_utility_agent.parse_principle_choice_enhanced(statement, max_retries=3)
        assert result.principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert result.constraint_amount is None

    @pytest.mark.asyncio
    async def test_fallback_parsing_for_malformed_responses(self, english_utility_agent, stubbed_runner):
        """Test fallback parsing mechanisms for malformed LLM responses."""

        test_cases = [
            (
                "My ballot: maximizing floor income",
                'Response: I choose maximizing_floor principle with no constraint. Certainty: sure.',  # Non-JSON response
                JusticePrinciple.MAXIMIZING_FLOOR
            ),
            (
                "Vote for average income maximization",
                'My selection is the maximizing_average option without any constraints.',  # Non-JSON response
                JusticePrinciple.MAXIMIZING_AVERAGE
            )
        ]

        # Register responses that will fail JSON parsing, then fallback attempts
        all_responses = ["test"]
        for _, malformed_response, expected_principle in test_cases:
            all_responses.append(malformed_response)  # Non-JSON response
            # Fallback success response
            all_responses.append(f'{{"principle": "{expected_principle.value}", "constraint_amount": null, "certainty": "sure"}}')

        stubbed_runner.register("Response Parser", all_responses)
        stubbed_runner.register("Response Validator", ["test"])

        for statement, malformed_response, expected_principle in test_cases:
            result = await english_utility_agent.parse_principle_choice_enhanced(statement, max_retries=2)
            assert result.principle == expected_principle, (
                f"Fallback parsing failed for '{statement}': "
                f"expected {expected_principle.value}, got {result.principle.value}"
            )

    @pytest.mark.asyncio
    async def test_exhausted_retries_error_handling(self, english_utility_agent, stubbed_runner):
        """Test proper error handling when all parsing retries are exhausted."""

        statement = "I vote for some unknown principle"

        # Register sequence of failed responses
        responses = [
            "test",  # init
            "invalid json",  # first attempt
            "still invalid",  # second attempt
            "also invalid"  # third attempt
        ]

        stubbed_runner.register("Response Parser", responses)
        stubbed_runner.register("Response Validator", ["test"])

        # Should raise ExperimentError after exhausting retries
        with pytest.raises(ExperimentError) as exc_info:
            await english_utility_agent.parse_principle_choice_enhanced(statement, max_retries=3)

        assert "Could not parse principle choice" in str(exc_info.value)
        assert "3 attempts" in str(exc_info.value)


class TestBallotConsensusValidation:
    """Test ballot consensus checking mechanisms."""

    @pytest.mark.asyncio
    async def test_identical_ballot_consensus(self, english_utility_agent, stubbed_runner):
        """Test consensus validation for identical ballots."""

        # Create identical ballots
        ballot1 = PrincipleChoice.create_for_parsing(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
            reasoning="Test ballot 1"
        )

        ballot2 = PrincipleChoice.create_for_parsing(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
            reasoning="Test ballot 2"
        )

        consensus, consensus_choice, errors = english_utility_agent.check_ballot_consensus([ballot1, ballot2])

        assert consensus is True, "Should detect consensus for identical ballots"
        assert consensus_choice.principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert len(errors) == 0, f"Should have no errors, got: {errors}"

    @pytest.mark.asyncio
    async def test_different_principles_no_consensus(self, english_utility_agent, stubbed_runner):
        """Test that different principles result in no consensus."""

        # Create ballots with different principles
        ballot1 = PrincipleChoice.create_for_parsing(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
            reasoning="Test ballot 1"
        )

        ballot2 = PrincipleChoice.create_for_parsing(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
            reasoning="Test ballot 2"
        )

        consensus, consensus_choice, errors = english_utility_agent.check_ballot_consensus([ballot1, ballot2])

        assert consensus is False, "Should not detect consensus for different principles"
        assert consensus_choice is None
        assert "different principles" in errors[0].lower()

    @pytest.mark.asyncio
    async def test_constraint_amount_mismatch_no_consensus(self, english_utility_agent, stubbed_runner):
        """Test that mismatched constraint amounts result in no consensus."""

        # Create ballots with same principle but different constraints
        ballot1 = PrincipleChoice.create_for_parsing(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=50000,
            certainty=CertaintyLevel.SURE,
            reasoning="Test ballot 1"
        )

        ballot2 = PrincipleChoice.create_for_parsing(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=60000,
            certainty=CertaintyLevel.SURE,
            reasoning="Test ballot 2"
        )

        consensus, consensus_choice, errors = english_utility_agent.check_ballot_consensus([ballot1, ballot2])

        assert consensus is False, "Should not detect consensus for different constraint amounts"
        assert consensus_choice is None
        assert "different constraint amounts" in errors[0].lower()

    @pytest.mark.asyncio
    async def test_empty_ballot_list_handling(self, english_utility_agent, stubbed_runner):
        """Test handling of empty ballot lists."""

        consensus, consensus_choice, errors = english_utility_agent.check_ballot_consensus([])

        assert consensus is False, "Should not detect consensus for empty ballot list"
        assert consensus_choice is None
        assert "no ballots" in errors[0].lower()