"""
Test multilingual principle parsing functionality.

Focused tests for core production parsing methods in UtilityAgent,
protecting against regressions in multilingual parsing logic.
"""

import pytest
import json
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple
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


class TestMultilingualParsing:
    """Test cases for multilingual principle parsing using production UtilityAgent methods."""

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
    async def test_principle_parsing_basic_functionality(self, utility_agent, stubbed_runner):
        """Test basic principle parsing functionality."""

        # Test core principle parsing
        test_cases = [
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

        # Set up parser and validator responses
        queue_parser_outputs(stubbed_runner, test_cases)
        queue_validator_outputs(stubbed_runner, ["test"] * len(test_cases))

        for expected_data in test_cases:
            result = await utility_agent.parse_principle_choice_enhanced("dummy input")

            assert result is not None, f"Should parse principle"
            assert result.principle.value == expected_data["principle"], \
                f"Expected {expected_data['principle']}, got {result.principle.value}"
            assert result.constraint_amount == expected_data["constraint_amount"], \
                f"Expected constraint {expected_data['constraint_amount']}, got {result.constraint_amount}"
            assert result.certainty == expected_data["certainty"], \
                f"Expected certainty {expected_data['certainty']}, got {result.certainty}"

    @pytest.mark.asyncio
    async def test_constraint_amount_parsing(self, utility_agent, stubbed_runner):
        """Test constraint amount parsing for constraint principles."""

        constraint_cases = [
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": 10000,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average_floor_constraint",
                "constraint_amount": 50000,
                "certainty": "sure"
            },
            {
                "principle": "maximizing_average_range_constraint",
                "constraint_amount": 30000,
                "certainty": "sure"
            }
        ]

        queue_parser_outputs(stubbed_runner, constraint_cases)
        queue_validator_outputs(stubbed_runner, ["test"] * len(constraint_cases))

        for expected_data in constraint_cases:
            result = await utility_agent.parse_principle_choice_enhanced("dummy input")

            assert result is not None
            assert result.principle.value == expected_data["principle"]
            assert result.constraint_amount == expected_data["constraint_amount"], \
                f"Expected constraint {expected_data['constraint_amount']}, got {result.constraint_amount}"

    @pytest.mark.asyncio
    async def test_certainty_level_parsing(self, utility_agent, stubbed_runner):
        """Test certainty level parsing."""

        certainty_cases = [
            {
                "principle": "maximizing_floor",
                "constraint_amount": None,
                "certainty": "very_sure"
            },
            {
                "principle": "maximizing_average",
                "constraint_amount": None,
                "certainty": "unsure"
            },
            {
                "principle": "maximizing_floor",
                "constraint_amount": None,
                "certainty": "very_unsure"
            }
        ]

        queue_parser_outputs(stubbed_runner, certainty_cases)
        queue_validator_outputs(stubbed_runner, ["test"] * len(certainty_cases))

        for expected_data in certainty_cases:
            result = await utility_agent.parse_principle_choice_enhanced("dummy input")

            assert result is not None
            assert result.certainty == expected_data["certainty"], \
                f"Expected certainty {expected_data['certainty']}, got {result.certainty}"

    @pytest.mark.asyncio
    async def test_principle_ranking_functionality(self, utility_agent, stubbed_runner):
        """Test principle ranking parsing functionality."""

        ranking_response = {
            "rankings": [
                {"principle": "maximizing_floor", "rank": 1},
                {"principle": "maximizing_average", "rank": 2},
                {"principle": "maximizing_average_floor_constraint", "rank": 3},
                {"principle": "maximizing_average_range_constraint", "rank": 4}
            ]
        }

        # Set up parser response for ranking
        stubbed_runner.register("Response Parser", [json.dumps(ranking_response)])
        queue_validator_outputs(stubbed_runner, ["test"])

        result = await utility_agent.parse_principle_ranking_enhanced("dummy ranking input")

        assert result is not None
        assert len(result.rankings) == 4

        # Check ranking order
        sorted_rankings = sorted(result.rankings, key=lambda x: x.rank)
        expected_order = ["maximizing_floor", "maximizing_average", "maximizing_average_floor_constraint", "maximizing_average_range_constraint"]
        actual_order = [r.principle.value for r in sorted_rankings]
        assert actual_order == expected_order

    @pytest.mark.asyncio
    async def test_multilingual_language_manager(self):
        """Test that different language managers can be created without error."""

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
            assert agent.language_manager is not None

    @pytest.mark.asyncio
    async def test_ballot_consensus_validation(self, utility_agent, stubbed_runner):
        """Test ballot consensus checking functionality."""

        from models.principle_types import PrincipleChoice

        # Test consensus case
        consensus_ballots = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_FLOOR,
                constraint_amount=None,
                certainty="sure",
                reasoning="Floor income choice"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_FLOOR,
                constraint_amount=None,
                certainty="sure",
                reasoning="Floor income choice"
            )
        ]

        has_consensus, consensus_choice, warnings = utility_agent.check_ballot_consensus(consensus_ballots)

        assert has_consensus is True
        assert consensus_choice is not None
        assert consensus_choice.principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert len(warnings) == 0

        # Test no consensus case
        no_consensus_ballots = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_FLOOR,
                constraint_amount=None,
                certainty="sure",
                reasoning="Floor income choice"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=None,
                certainty="sure",
                reasoning="Average income choice"
            )
        ]

        has_consensus, consensus_choice, warnings = utility_agent.check_ballot_consensus(no_consensus_ballots)

        assert has_consensus is False
        assert consensus_choice is None