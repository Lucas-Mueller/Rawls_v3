"""Unit tests for Phase2Manager context initialization continuity."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from config import ExperimentConfiguration, AgentConfiguration
from core.phase2_manager import Phase2Manager
from models import (
    Phase1Results,
    PrincipleRanking,
    RankedPrinciple,
    JusticePrinciple,
    CertaintyLevel,
    ApplicationResult,
    PrincipleChoice,
    IncomeClass,
    IncomeDistribution,
)


def _build_principle_ranking() -> PrincipleRanking:
    return PrincipleRanking(
        rankings=[
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4),
        ],
        certainty=CertaintyLevel.SURE,
    )


def _build_application_result(choice: PrincipleChoice) -> ApplicationResult:
    distribution = IncomeDistribution(
        high=32000,
        medium_high=27000,
        medium=24000,
        medium_low=13000,
        low=12000,
    )
    return ApplicationResult(
        round_number=1,
        principle_choice=choice,
        chosen_distribution=distribution,
        assigned_income_class=IncomeClass.HIGH,
        earnings=25.0,
    )


@pytest.mark.unit
def test_initialize_phase2_contexts_transfers_memory_and_balance():
    config = ExperimentConfiguration(
        language="English",
        agents=[
            AgentConfiguration(name="TestAgent1", personality="P1"),
            AgentConfiguration(name="TestAgent2", personality="P2"),
        ],
        phase2_rounds=3,
    )

    participants = []
    utility_agent = MagicMock()
    manager = Phase2Manager(participants, utility_agent, experiment_config=config)

    manager._initialize_services = MagicMock()
    manager.memory_service = MagicMock()
    manager.memory_service.validate_and_sanitize_memory.side_effect = [
        "sanitized memory one",
        "sanitized memory two",
    ]

    ranking = _build_principle_ranking()
    choice = PrincipleChoice.create_for_parsing(
        principle=JusticePrinciple.MAXIMIZING_FLOOR,
        certainty=CertaintyLevel.SURE,
    )
    application_result = _build_application_result(choice)

    phase1_results = [
        Phase1Results(
            participant_name="TestAgent1",
            initial_ranking=ranking,
            post_explanation_ranking=ranking,
            application_results=[application_result],
            final_ranking=ranking,
            total_earnings=42.0,
            final_memory_state="memory one",
        ),
        Phase1Results(
            participant_name="TestAgent2",
            initial_ranking=ranking,
            post_explanation_ranking=ranking,
            application_results=[application_result],
            final_ranking=ranking,
            total_earnings=55.0,
            final_memory_state="memory two",
        ),
    ]

    contexts = manager._initialize_phase2_contexts(phase1_results, config)

    assert [ctx.name for ctx in contexts] == ["TestAgent1", "TestAgent2"]
    assert contexts[0].memory == "sanitized memory one"
    assert contexts[1].memory == "sanitized memory two"
    assert contexts[0].bank_balance == pytest.approx(42.0)
    assert contexts[1].bank_balance == pytest.approx(55.0)
    assert contexts[0].phase.value == "phase_2"
    assert contexts[0].round_number == 1


@pytest.mark.unit
def test_initialize_phase2_contexts_handles_mismatched_results(monkeypatch):
    config = ExperimentConfiguration(
        language="English",
        agents=[
            AgentConfiguration(name="TestAgent1", personality="P1"),
            AgentConfiguration(name="TestAgent2", personality="P2"),
        ],
        phase2_rounds=3,
    )

    participants = []
    utility_agent = MagicMock()
    manager = Phase2Manager(participants, utility_agent, experiment_config=config)

    manager._initialize_services = MagicMock()
    manager.memory_service = MagicMock()
    manager.memory_service.validate_and_sanitize_memory.return_value = "sanitized"

    ranking = _build_principle_ranking()
    choice = PrincipleChoice.create_for_parsing(
        principle=JusticePrinciple.MAXIMIZING_FLOOR,
        certainty=CertaintyLevel.SURE,
    )
    application_result = _build_application_result(choice)

    phase1_results = [
        Phase1Results(
            participant_name="TestAgent1",
            initial_ranking=ranking,
            post_explanation_ranking=ranking,
            application_results=[application_result],
            final_ranking=ranking,
            total_earnings=42.0,
            final_memory_state="memory one",
        )
    ]

    contexts = manager._initialize_phase2_contexts(phase1_results, config)
    assert len(contexts) == 1
    assert contexts[0].name == "TestAgent1"
