"""
Test ballot parsing functionality and critical regression prevention.

Focused tests for the specific parsing vulnerabilities that caused experiment failures.
Critical for preventing silent regressions in ballot parsing logic.
"""

import pytest
import json
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice
from utils.language_manager import create_language_manager, SupportedLanguage


def queue_parser_outputs(stubbed_runner, responses, agent_name="Response Parser"):
    """Register a sequence of JSON payloads for the parser agent."""
    stubbed_runner.register(
        agent_name,
        [json.dumps(response) for response in responses]
    )


def queue_validator_outputs(stubbed_runner, responses, agent_name="Response Validator"):
    """Register a sequence of outputs for the validator agent."""
    stubbed_runner.register(
        agent_name,
        [response for response in responses]
    )


class TestBallotParsingVulnerabilities:
    """Test critical ballot parsing vulnerabilities using production UtilityAgent methods."""

    @pytest.fixture
    def utility_agent(self):
        """Create utility agent for testing."""
        language_manager = create_language_manager(SupportedLanguage.ENGLISH)
        return UtilityAgent(
            utility_model="stub-model",
            temperature=0.0,
            experiment_language="english",
            language_manager=language_manager,
        )

    @pytest.mark.asyncio
    async def test_critical_regression_prevention(self, utility_agent, stubbed_runner):
        """Test the exact parsing scenarios that caused the experiment failure."""

        # The critical test: ensure "no constraints" is parsed as simple principles
        # not constraint principles. This is the EXACT regression that caused experiment failure.

        no_constraints_cases = [
            {
                "principle": "maximizing_floor",
                "constraint_amount": None,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average",
                "constraint_amount": None,
                "certainty": "sure"
            }
        ]

        # These should parse as simple principles (NOT constraint versions)
        queue_parser_outputs(stubbed_runner, no_constraints_cases)
        queue_validator_outputs(stubbed_runner, ["test"] * len(no_constraints_cases))

        for expected_data in no_constraints_cases:
            result = await utility_agent.parse_principle_choice_enhanced("dummy input with no constraints")

            assert result is not None, "Should parse principle"
            assert result.principle.value == expected_data["principle"], \
                f"CRITICAL REGRESSION: Should parse as {expected_data['principle']}, got {result.principle.value}"
            assert result.constraint_amount is None, \
                f"No constraints case should have null constraint_amount, got {result.constraint_amount}"

    @pytest.mark.asyncio
    async def test_constraint_vs_no_constraint_distinction(self, utility_agent, stubbed_runner):
        """Test correct distinction between constraint and non-constraint principles."""

        # Non-constraint principles
        no_constraint_cases = [
            {
                "principle": "maximizing_floor",
                "constraint_amount": None,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average",
                "constraint_amount": None,
                "certainty": "sure"
            }
        ]

        # Constraint principles
        constraint_cases = [
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": 15000,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average_range_constraint",
                "constraint_amount": 25000,
                "certainty": "sure"
            }
        ]

        all_cases = no_constraint_cases + constraint_cases

        queue_parser_outputs(stubbed_runner, all_cases)
        queue_validator_outputs(stubbed_runner, ["test"] * len(all_cases))

        for expected_data in all_cases:
            result = await utility_agent.parse_principle_choice_enhanced("dummy input")

            assert result is not None
            assert result.principle.value == expected_data["principle"]
            assert result.constraint_amount == expected_data["constraint_amount"]

    @pytest.mark.asyncio
    async def test_constraint_amount_extraction(self, utility_agent, stubbed_runner):
        """Test constraint amount extraction for various scenarios."""

        constraint_extraction_cases = [
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": 10,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": 13000,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average_range_constraint",
                "constraint_amount": 20000,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": 8000,
                "certainty": "sure"
            }
        ]

        queue_parser_outputs(stubbed_runner, constraint_extraction_cases)
        queue_validator_outputs(stubbed_runner, ["test"] * len(constraint_extraction_cases))

        for expected_data in constraint_extraction_cases:
            result = await utility_agent.parse_principle_choice_enhanced("dummy input")

            assert result is not None
            assert result.constraint_amount == expected_data["constraint_amount"], \
                f"Expected constraint amount {expected_data['constraint_amount']}, got {result.constraint_amount}"

    @pytest.mark.asyncio
    async def test_ballot_consensus_with_constraints(self, utility_agent, stubbed_runner):
        """Test ballot consensus checking with constraint principles."""

        # Consensus case: All agents choose same principle with same constraint
        consensus_ballots = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=15000,
                certainty="sure",
                reasoning="Floor constraint of $15,000"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=15000,
                certainty="sure",
                reasoning="Floor constraint of $15,000"
            )
        ]

        has_consensus, consensus_choice, warnings = utility_agent.check_ballot_consensus(consensus_ballots)

        assert has_consensus is True
        assert consensus_choice is not None
        assert consensus_choice.principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT
        assert consensus_choice.constraint_amount == 15000
        assert len(warnings) == 0

    @pytest.mark.asyncio
    async def test_ballot_consensus_different_constraints(self, utility_agent, stubbed_runner):
        """Test ballot consensus fails with different constraint amounts."""

        # No consensus case: Same principle, different constraints
        different_constraint_ballots = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=15000,
                certainty="sure",
                reasoning="Floor constraint of $15,000"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=20000,
                certainty="sure",
                reasoning="Floor constraint of $20,000"
            )
        ]

        has_consensus, consensus_choice, warnings = utility_agent.check_ballot_consensus(different_constraint_ballots)

        assert has_consensus is False
        assert consensus_choice is None
        assert len(warnings) > 0
        assert "Different constraint amounts" in str(warnings)

    @pytest.mark.asyncio
    async def test_edge_cases_parsing(self, utility_agent, stubbed_runner):
        """Test edge cases that might cause parsing issues."""

        edge_cases = [
            # Simple principles should NOT be parsed as constraint principles
            {
                "principle": "maximizing_floor",
                "constraint_amount": None,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average",
                "constraint_amount": None,
                "certainty": "sure"
            },
            # Constraint principles should be parsed correctly
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": 18000,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average_range_constraint",
                "constraint_amount": 22000,
                "certainty": "sure"
            }
        ]

        queue_parser_outputs(stubbed_runner, edge_cases)
        queue_validator_outputs(stubbed_runner, ["test"] * len(edge_cases))

        for expected_data in edge_cases:
            result = await utility_agent.parse_principle_choice_enhanced("dummy input")

            assert result is not None
            assert result.principle.value == expected_data["principle"], \
                f"Expected {expected_data['principle']}, got {result.principle.value}"
            assert result.constraint_amount == expected_data["constraint_amount"], \
                f"Expected constraint {expected_data['constraint_amount']}, got {result.constraint_amount}"

    @pytest.mark.asyncio
    async def test_multilingual_parsing_capability(self):
        """Test that multilingual parsing infrastructure is available."""

        # Test creating utility agents with different languages
        languages = [SupportedLanguage.ENGLISH, SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN]

        for language in languages:
            language_manager = create_language_manager(language)
            agent = UtilityAgent(
                utility_model="stub-model",
                temperature=0.0,
                experiment_language=language.value,
                language_manager=language_manager,
            )
            assert agent is not None
            assert agent.experiment_language.lower() == language.value.lower()

    @pytest.mark.asyncio
    async def test_full_principle_name_parsing(self, utility_agent, stubbed_runner):
        """Test parsing of full principle names in responses."""

        full_name_cases = [
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": 15000,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": None,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_floor",
                "constraint_amount": None,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average",
                "constraint_amount": None,
                "certainty": "sure"
            }
        ]

        queue_parser_outputs(stubbed_runner, full_name_cases)
        queue_validator_outputs(stubbed_runner, ["test"] * len(full_name_cases))

        for expected_data in full_name_cases:
            result = await utility_agent.parse_principle_choice_enhanced("dummy input")

            assert result is not None
            assert result.principle.value == expected_data["principle"], \
                f"Expected {expected_data['principle']}, got {result.principle.value}"
            assert result.constraint_amount == expected_data["constraint_amount"], \
                f"Expected constraint {expected_data['constraint_amount']}, got {result.constraint_amount}"