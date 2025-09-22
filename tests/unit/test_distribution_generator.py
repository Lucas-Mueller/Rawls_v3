"""Pytest suite for `DistributionGenerator`."""
from __future__ import annotations

import pytest

from core.distribution_generator import DistributionGenerator
from models import (
    IncomeDistribution,
    JusticePrinciple,
    PrincipleChoice,
    CertaintyLevel,
    IncomeClass,
)
from utils.language_manager import LanguageManager

pytestmark = pytest.mark.contracts


def test_generate_dynamic_distribution():
    dist_set = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0))
    assert len(dist_set.distributions) == 4
    assert 0.5 <= dist_set.multiplier <= 2.0
    for dist in dist_set.distributions:
        assert all(value > 0 for value in [dist.high, dist.medium_high, dist.medium, dist.medium_low, dist.low])


def test_apply_principle_maximizing_floor():
    distributions = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000),
        IncomeDistribution(high=31000, medium_high=24000, medium=21000, medium_low=16000, low=14000),
        IncomeDistribution(high=21000, medium_high=20000, medium=19000, medium_low=16000, low=15000),
    ]

    principle = PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE)
    chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(distributions, principle, language_manager=None)
    assert chosen_dist.low == 15000
    assert "floor" in explanation.lower()


def test_apply_principle_maximizing_average():
    distributions = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=40000, medium_high=35000, medium=30000, medium_low=25000, low=20000),
    ]

    principle = PrincipleChoice(principle=JusticePrinciple.MAXIMIZING_AVERAGE, certainty=CertaintyLevel.SURE)
    chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(distributions, principle, language_manager=None)
    assert chosen_dist.high == 40000
    assert "average" in explanation.lower()


def test_apply_principle_with_floor_constraint():
    distributions = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=15000),
    ]

    principle = PrincipleChoice(
        principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
        constraint_amount=14000,
        certainty=CertaintyLevel.SURE,
    )

    chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(distributions, principle, language_manager=None)
    assert chosen_dist.low >= 14000
    assert "floor constraint" in explanation.lower()


def test_calculate_payoff():
    distribution = IncomeDistribution(high=30000, medium_high=25000, medium=20000, medium_low=15000, low=10000)
    assigned_class, payoff = DistributionGenerator.calculate_payoff(distribution)
    assert assigned_class in list(IncomeClass)
    expected_income = distribution.get_income_by_class(assigned_class)
    assert payoff == expected_income / 10000.0


def test_format_distributions_table():
    distributions = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000),
    ]

    language_manager = LanguageManager()
    table = DistributionGenerator.format_distributions_table(distributions, language_manager=language_manager)

    assert "Income Class" in table
    assert "Dist. 1" in table
    assert "$32,000" in table
    assert "$28,000" in table
*** End Patch
