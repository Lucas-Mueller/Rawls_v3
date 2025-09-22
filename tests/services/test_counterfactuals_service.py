"""Contract tests for `CounterfactualsService`."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.services.counterfactuals_service import CounterfactualsService
from config.phase2_settings import Phase2Settings
from models import (
    GroupDiscussionResult,
    PrincipleChoice,
    JusticePrinciple,
    CertaintyLevel,
    DistributionSet,
    IncomeDistribution,
    IncomeClass,
)

pytestmark = pytest.mark.contracts


def make_distribution_set() -> DistributionSet:
    base = IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000)
    return DistributionSet(distributions=[base] * 4, multiplier=1.0)


@pytest.mark.asyncio
async def test_apply_group_principle_with_consensus(monkeypatch, minimal_experiment_config):
    settings = Phase2Settings.get_default()
    service = CounterfactualsService(language_manager=None, settings=settings)

    distribution_set = make_distribution_set()

    monkeypatch.setattr(
        "core.services.counterfactuals_service.DistributionGenerator.generate_dynamic_distribution",
        lambda _: distribution_set,
    )

    monkeypatch.setattr(
        "core.services.counterfactuals_service.DistributionGenerator.apply_principle_to_distributions",
        lambda distributions, choice, probabilities=None: (distributions.distributions[0], "ok"),
    )

    monkeypatch.setattr(
        "core.services.counterfactuals_service.DistributionGenerator.calculate_payoff",
        lambda distribution: (IncomeClass.MEDIUM, 15000.0),
    )

    discussion = GroupDiscussionResult(
        consensus_reached=True,
        agreed_principle=PrincipleChoice.create_for_parsing(
            JusticePrinciple.MAXIMIZING_FLOOR,
            certainty=CertaintyLevel.SURE,
        ),
        final_round=1,
        discussion_history="",
        vote_history=[],
    )

    participants = [SimpleNamespace(name="AgentA"), SimpleNamespace(name="AgentB")]

    payoffs, assigned_classes, _, _ = await service.apply_group_principle_and_calculate_payoffs(
        discussion,
        minimal_experiment_config,
        participants,
    )

    assert payoffs == {"AgentA": 15000.0, "AgentB": 15000.0}
    assert assigned_classes == {"AgentA": IncomeClass.MEDIUM.value, "AgentB": IncomeClass.MEDIUM.value}
*** End Patch
