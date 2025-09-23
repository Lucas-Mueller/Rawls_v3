"""
Test constraint validation and correction functionality.

Tests production UtilityAgent methods for constraint validation,
re-prompting, and ballots handling for constraint principles.
"""

import pytest
from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple, PrincipleChoice
from utils.language_manager import create_language_manager, SupportedLanguage


class TestConstraintCorrection:
    """Test constraint validation and correction using production methods."""

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
    async def test_constraint_validation_floor_principle(self, utility_agent):
        """Test constraint validation for floor constraint principle."""

        # Valid floor constraint
        valid_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=15000,
            certainty="sure",
            reasoning="Floor constraint of $15,000"
        )

        # Invalid floor constraint (missing amount)
        invalid_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=None,
            certainty="sure",
            reasoning="Floor constraint without amount"
        )

        # Invalid floor constraint (zero amount)
        zero_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=0,
            certainty="sure",
            reasoning="Floor constraint with zero"
        )

        # Test valid constraint
        assert await utility_agent.validate_constraint_specification(valid_choice) is True

        # Test invalid constraints
        assert await utility_agent.validate_constraint_specification(invalid_choice) is False
        assert await utility_agent.validate_constraint_specification(zero_choice) is False

    @pytest.mark.asyncio
    async def test_constraint_validation_range_principle(self, utility_agent):
        """Test constraint validation for range constraint principle."""

        # Valid range constraint
        valid_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            constraint_amount=25000,
            certainty="sure",
            reasoning="Range constraint of $25,000"
        )

        # Invalid range constraint (missing amount)
        invalid_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            constraint_amount=None,
            certainty="sure",
            reasoning="Range constraint without amount"
        )

        # Test valid constraint
        assert await utility_agent.validate_constraint_specification(valid_choice) is True

        # Test invalid constraint
        assert await utility_agent.validate_constraint_specification(invalid_choice) is False

    @pytest.mark.asyncio
    async def test_constraint_validation_non_constraint_principles(self, utility_agent):
        """Test that non-constraint principles don't require constraint amounts."""

        # Maximizing floor (no constraint needed)
        floor_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_FLOOR,
            constraint_amount=None,
            certainty="sure",
            reasoning="Just maximizing floor income"
        )

        # Maximizing average (no constraint needed)
        average_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE,
            constraint_amount=None,
            certainty="sure",
            reasoning="Just maximizing average income"
        )

        # Both should be valid without constraint amounts
        assert await utility_agent.validate_constraint_specification(floor_choice) is True
        assert await utility_agent.validate_constraint_specification(average_choice) is True

        # They should also be valid WITH constraint amounts (ignored)
        floor_choice.constraint_amount = 10000
        average_choice.constraint_amount = 20000

        assert await utility_agent.validate_constraint_specification(floor_choice) is True
        assert await utility_agent.validate_constraint_specification(average_choice) is True

    @pytest.mark.asyncio
    async def test_constraint_re_prompt_generation(self, utility_agent):
        """Test re-prompt generation for missing constraints."""

        # Floor constraint missing
        floor_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=None,
            certainty="sure",
            reasoning="Floor constraint without amount"
        )

        # Range constraint missing
        range_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            constraint_amount=None,
            certainty="sure",
            reasoning="Range constraint without amount"
        )

        # Test re-prompt generation
        floor_prompt = await utility_agent.re_prompt_for_constraint("TestAgent", floor_choice)
        range_prompt = await utility_agent.re_prompt_for_constraint("TestAgent", range_choice)

        assert floor_prompt is not None
        assert isinstance(floor_prompt, str)
        assert len(floor_prompt) > 0

        assert range_prompt is not None
        assert isinstance(range_prompt, str)
        assert len(range_prompt) > 0

        # Prompts should be different for different constraint types
        assert floor_prompt != range_prompt

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
    async def test_ballot_consensus_missing_constraints(self, utility_agent, stubbed_runner):
        """Test ballot consensus fails with missing constraint amounts."""

        # Missing constraint amounts
        missing_constraint_ballots = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=None,
                certainty="sure",
                reasoning="Floor constraint without amount"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=None,
                certainty="sure",
                reasoning="Floor constraint without amount"
            )
        ]

        has_consensus, consensus_choice, warnings = utility_agent.check_ballot_consensus(missing_constraint_ballots)

        # Should not achieve consensus with missing constraints
        assert has_consensus is False
        assert consensus_choice is None

    @pytest.mark.asyncio
    async def test_mixed_constraint_scenarios(self, utility_agent, stubbed_runner):
        """Test various mixed constraint scenarios."""

        # One valid, one invalid constraint
        mixed_ballots = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=15000,
                certainty="sure",
                reasoning="Floor constraint of $15,000"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
                constraint_amount=None,
                certainty="sure",
                reasoning="Floor constraint without amount"
            )
        ]

        has_consensus, consensus_choice, warnings = utility_agent.check_ballot_consensus(mixed_ballots)

        assert has_consensus is False
        assert consensus_choice is None

    @pytest.mark.asyncio
    async def test_non_constraint_principle_consensus(self, utility_agent, stubbed_runner):
        """Test consensus works for non-constraint principles."""

        # Non-constraint principles should achieve consensus easily
        non_constraint_ballots = [
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_FLOOR,
                constraint_amount=None,
                certainty="sure",
                reasoning="Maximizing floor income"
            ),
            PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_FLOOR,
                constraint_amount=None,
                certainty="sure",
                reasoning="Maximizing floor income"
            )
        ]

        has_consensus, consensus_choice, warnings = utility_agent.check_ballot_consensus(non_constraint_ballots)

        assert has_consensus is True
        assert consensus_choice is not None
        assert consensus_choice.principle == JusticePrinciple.MAXIMIZING_FLOOR
        assert len(warnings) == 0

    @pytest.mark.asyncio
    async def test_constraint_amount_validation_edge_cases(self, utility_agent):
        """Test edge cases for constraint amount validation."""

        # Negative constraint amount
        negative_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=-1000,
            certainty="sure",
            reasoning="Negative constraint"
        )

        # Very large constraint amount
        large_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=1000000,
            certainty="sure",
            reasoning="Large constraint"
        )

        # Minimal valid constraint amount
        minimal_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=1,
            certainty="sure",
            reasoning="Minimal constraint"
        )

        # Test validations
        assert await utility_agent.validate_constraint_specification(negative_choice) is False
        assert await utility_agent.validate_constraint_specification(large_choice) is True
        assert await utility_agent.validate_constraint_specification(minimal_choice) is True

    @pytest.mark.asyncio
    async def test_multilingual_constraint_validation(self, utility_agent):
        """Test constraint validation works with multilingual reasoning."""

        # English reasoning
        english_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=15000,
            certainty="sure",
            reasoning="Floor constraint of $15,000"
        )

        # Spanish reasoning
        spanish_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=15000,
            certainty="sure",
            reasoning="Restricción de piso de $15,000"
        )

        # Mandarin reasoning
        mandarin_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            constraint_amount=15000,
            certainty="sure",
            reasoning="底线约束为$15,000"
        )

        # All should validate regardless of reasoning language
        assert await utility_agent.validate_constraint_specification(english_choice) is True
        assert await utility_agent.validate_constraint_specification(spanish_choice) is True
        assert await utility_agent.validate_constraint_specification(mandarin_choice) is True