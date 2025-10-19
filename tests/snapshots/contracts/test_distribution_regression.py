import random

from core.distribution_generator import DistributionGenerator
from models import CertaintyLevel, JusticePrinciple, PrincipleChoice
from models.experiment_types import IncomeClassProbabilities


def _serialize_distribution_set(distribution_set):
    return {
        "multiplier": distribution_set.multiplier,
        "distributions": [distribution.model_dump() for distribution in distribution_set.distributions],
    }


def test_dynamic_distribution_structure(data_regression):
    rng = random.Random(123)
    distribution_set = DistributionGenerator.generate_dynamic_distribution((0.8, 1.2), random_gen=rng)

    payload = _serialize_distribution_set(distribution_set)
    data_regression.check(payload)


def test_principle_application_maximizing_average(data_regression):
    probs = IncomeClassProbabilities()
    distributions = DistributionGenerator.BASE_DISTRIBUTIONS
    choice = PrincipleChoice.create_for_parsing(
        JusticePrinciple.MAXIMIZING_AVERAGE,
        certainty=CertaintyLevel.SURE,
    )

    selected, explanation = DistributionGenerator.apply_principle_to_distributions(
        distributions,
        choice,
        probabilities=probs,
    )

    payload = {
        "selected": selected.model_dump(),
        "explanation": explanation,
    }
    data_regression.check(payload)


def test_principle_application_floor_focus(data_regression):
    distributions = DistributionGenerator.BASE_DISTRIBUTIONS
    choice = PrincipleChoice.create_for_parsing(
        JusticePrinciple.MAXIMIZING_FLOOR,
        certainty=CertaintyLevel.SURE,
    )

    selected, explanation = DistributionGenerator.apply_principle_to_distributions(distributions, choice)

    payload = {
        "selected": selected.model_dump(),
        "explanation": explanation,
    }
    data_regression.check(payload)
