"""Unit tests for principle choice validation workflows."""
from __future__ import annotations

import pytest

from models.principle_types import PrincipleChoice, JusticePrinciple, CertaintyLevel


@pytest.mark.parametrize(
    "principle,constraint,should_raise",
    [
        (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 15000, False),
        (JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, None, True),
        (JusticePrinciple.MAXIMIZING_AVERAGE, None, False),
    ],
)
def test_principle_choice_validation(principle, constraint, should_raise):
    choice = PrincipleChoice.create_for_parsing(
        principle=principle,
        constraint_amount=constraint,
        certainty=CertaintyLevel.SURE,
        reasoning="Test reasoning",
    )

    if should_raise:
        with pytest.raises(ValueError):
            choice.validate_for_voting()
    else:
        validated = choice.validate_for_voting()
        assert validated.principle == principle
        if principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT:
            assert validated.constraint_amount == constraint
        else:
            assert validated.constraint_amount is None
