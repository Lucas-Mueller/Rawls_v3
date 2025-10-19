"""
Unit tests for distribution generation system.
"""
import random

from core.distribution_generator import DistributionGenerator
from models import CertaintyLevel, IncomeDistribution, IncomeClass, JusticePrinciple, PrincipleChoice
from models.experiment_types import IncomeClassProbabilities
from utils.language_manager import LanguageManager


def test_generate_dynamic_distribution():
    """Test dynamic distribution generation with multipliers."""
    dist_set = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0))

    assert len(dist_set.distributions) == 4
    assert 0.5 <= dist_set.multiplier <= 2.0

    for dist in dist_set.distributions:
        assert dist.high > 0
        assert dist.medium_high > 0
        assert dist.medium > 0
        assert dist.medium_low > 0
        assert dist.low > 0


def test_apply_principle_maximizing_floor():
    """Test principle application logic for maximizing floor."""
    distributions = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000),
        IncomeDistribution(high=31000, medium_high=24000, medium=21000, medium_low=16000, low=14000),
        IncomeDistribution(high=21000, medium_high=20000, medium=19000, medium_low=16000, low=15000),
    ]

    principle = PrincipleChoice(
        principle=JusticePrinciple.MAXIMIZING_FLOOR,
        certainty=CertaintyLevel.SURE,
    )

    chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(
        distributions, principle, language_manager=None
    )

    assert chosen_dist.low == 15000  # highest floor
    assert "floor" in explanation.lower()


def test_apply_principle_maximizing_average():
    """Test principle application for maximizing average."""
    distributions = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=40000, medium_high=35000, medium=30000, medium_low=25000, low=20000),
    ]

    principle = PrincipleChoice(
        principle=JusticePrinciple.MAXIMIZING_AVERAGE,
        certainty=CertaintyLevel.SURE,
    )

    chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(
        distributions, principle, language_manager=None
    )

    assert chosen_dist.high == 40000
    assert "average" in explanation.lower()


def test_apply_principle_with_floor_constraint():
    """Test constraint principle validation and application."""
    distributions = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=15000),
    ]

    principle = PrincipleChoice(
        principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
        constraint_amount=14000,
        certainty=CertaintyLevel.SURE,
    )

    chosen_dist, explanation = DistributionGenerator.apply_principle_to_distributions(
        distributions, principle, language_manager=None
    )

    assert chosen_dist.low >= 14000
    assert "floor constraint" in explanation.lower()


def test_calculate_payoff():
    """Test payoff calculation."""
    distribution = IncomeDistribution(
        high=30000,
        medium_high=25000,
        medium=20000,
        medium_low=15000,
        low=10000,
    )

    assigned_class, payoff = DistributionGenerator.calculate_payoff(distribution)

    assert assigned_class in list(IncomeClass)

    expected_income = distribution.get_income_by_class(assigned_class)
    expected_payoff = expected_income / 10000.0
    assert payoff == expected_payoff


def test_format_distributions_table():
    """Test distribution table formatting."""
    distributions = [
        IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000),
        IncomeDistribution(high=28000, medium_high=22000, medium=20000, medium_low=17000, low=13000),
    ]

    language_manager = LanguageManager()
    table = DistributionGenerator.format_distributions_table(distributions, language_manager=language_manager)

    assert "Income Class" in table
    assert "Dist. 1" in table
    assert "Dist. 2" in table
    assert "$32,000" in table
    assert "$28,000" in table


def test_alternative_earnings_respect_seed():
    """Ensure alternative earnings use provided random generator deterministically."""
    distributions = DistributionGenerator.BASE_DISTRIBUTIONS
    rng_one = random.Random(99)
    rng_two = random.Random(99)

    earnings_one = DistributionGenerator.calculate_alternative_earnings(
        distributions,
        random_gen=rng_one,
    )
    earnings_two = DistributionGenerator.calculate_alternative_earnings(
        distributions,
        random_gen=rng_two,
    )

    assert earnings_one == earnings_two


def test_weighted_alternative_earnings_respect_probabilities():
    """Weighted alternative earnings should reflect provided class probabilities."""
    distributions = [
        IncomeDistribution(high=40000, medium_high=35000, medium=30000, medium_low=25000, low=10000),
        IncomeDistribution(high=42000, medium_high=36000, medium=30000, medium_low=25000, low=20000),
    ]
    probs = IncomeClassProbabilities(high=0.0, medium_high=0.0, medium=0.0, medium_low=0.0, low=1.0)

    earnings = DistributionGenerator.calculate_alternative_earnings(
        distributions,
        probabilities=probs,
        random_gen=random.Random(7),
    )

    assert earnings["distribution_1"] == 1.0
    assert earnings["distribution_2"] == 2.0


def test_weighted_principle_counterfactuals_use_probabilities():
    """Counterfactual principle earnings should choose weighted-optimal distributions."""
    distributions = [
        IncomeDistribution(high=50000, medium_high=40000, medium=30000, medium_low=20000, low=20000),
        IncomeDistribution(high=60000, medium_high=55000, medium=45000, medium_low=30000, low=10000),
    ]
    probs = IncomeClassProbabilities(high=0.0, medium_high=0.0, medium=0.0, medium_low=0.0, low=1.0)

    weighted_same_class = DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class(
        distributions,
        IncomeClass.LOW,
        probabilities=probs,
    )
    unweighted_same_class = DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class(
        distributions,
        IncomeClass.LOW,
    )

    assert weighted_same_class[JusticePrinciple.MAXIMIZING_AVERAGE.value] == 2.0
    assert unweighted_same_class[JusticePrinciple.MAXIMIZING_AVERAGE.value] == 1.0

    weighted_by_principle = DistributionGenerator.calculate_alternative_earnings_by_principle(
        distributions,
        probabilities=probs,
        random_gen=random.Random(11),
    )
    assert weighted_by_principle[JusticePrinciple.MAXIMIZING_AVERAGE.value] == 2.0
