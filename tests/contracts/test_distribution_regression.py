import random

from core.distribution_generator import DistributionGenerator
from models import JusticePrinciple, PrincipleChoice, CertaintyLevel
from models.experiment_types import IncomeClassProbabilities


def test_dynamic_distribution_structure():
    rng = random.Random(123)
    distribution_set = DistributionGenerator.generate_dynamic_distribution((0.8, 1.2), random_gen=rng)

    assert len(distribution_set.distributions) == 4
    assert all(dist.low > 0 for dist in distribution_set.distributions)
    assert 0.8 <= distribution_set.multiplier <= 1.2


def test_principle_application_maximizing_average():
    probs = IncomeClassProbabilities()
    distributions = DistributionGenerator.BASE_DISTRIBUTIONS
    choice = PrincipleChoice.create_for_parsing(
        JusticePrinciple.MAXIMIZING_AVERAGE,
        certainty=CertaintyLevel.SURE,
    )

    selected, explanation = DistributionGenerator.apply_principle_to_distributions(distributions, choice, probabilities=probs)

    assert selected in distributions
    assert "average" in explanation.lower()


def test_principle_application_floor_focus():
    distributions = DistributionGenerator.BASE_DISTRIBUTIONS
    choice = PrincipleChoice.create_for_parsing(
        JusticePrinciple.MAXIMIZING_FLOOR,
        certainty=CertaintyLevel.SURE,
    )

    selected, explanation = DistributionGenerator.apply_principle_to_distributions(distributions, choice)
    floor_values = [dist.low for dist in distributions]

    assert selected.low == max(floor_values)
    assert str(selected.low) in explanation
