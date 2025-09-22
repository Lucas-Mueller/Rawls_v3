"""Trace metadata and integration coverage for the experiment manager."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from models import (
    Phase1Results,
    Phase2Results,
    GroupDiscussionResult,
    ApplicationResult,
)
from models.principle_types import (
    PrincipleRanking,
    RankedPrinciple,
    PrincipleChoice,
    JusticePrinciple,
    CertaintyLevel,
    IncomeClass,
)
from models.experiment_types import IncomeDistribution


class StubParticipant:
    def __init__(self, cfg):
        self.name = cfg.name
        self.config = cfg
        self.agent = SimpleNamespace(name=cfg.name)

    async def update_memory(self, *_args, **_kwargs):
        return "memory"


class StubUtilityAgent:
    def __init__(self, *args, **kwargs):
        pass

    async def async_init(self):  # pragma: no cover - behaviour verified via manager tests
        return None

    async def validate_consensus_against_discussion(self, *_args, **_kwargs):
        return True, []


class StubAgentLogger:
    def initialize_experiment(self, *_args, **_kwargs):
        return None

    def set_seed_info(self, *_args, **_kwargs):
        return None

    def initialize_voting_history(self):
        return None


class StubPhase1Manager:
    def __init__(self, participants, *_args, **_kwargs):
        self.participants = participants

    async def run_phase1(self, *_args, **_kwargs):
        ranking = PrincipleRanking(
            rankings=[
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4),
            ],
            certainty=CertaintyLevel.SURE,
        )

        application = ApplicationResult(
            round_number=1,
            principle_choice=PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=None,
                certainty=CertaintyLevel.SURE,
            ),
            chosen_distribution=IncomeDistribution(high=30_000, medium_high=25_000, medium=20_000, medium_low=15_000, low=10_000),
            assigned_income_class=IncomeClass.HIGH,
            earnings=12_000.0,
            alternative_earnings={},
            alternative_earnings_same_class={},
        )

        return [
            Phase1Results(
                participant_name=participant.name,
                initial_ranking=ranking,
                post_explanation_ranking=ranking,
                application_results=[application],
                final_ranking=ranking,
                total_earnings=12_000.0,
                final_memory_state="memory",
            )
            for participant in self.participants
        ]


class StubPhase2Manager:
    def __init__(self, participants, *_args, **_kwargs):
        self.participants = participants

    async def run_phase2(self, _config, phase1_results, *_args, **_kwargs):
        principle_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
        )
        discussion = GroupDiscussionResult(
            consensus_reached=True,
            agreed_principle=principle_choice,
            final_round=1,
            discussion_history="generated",
            vote_history=[],
        )

        payoff_results = {result.participant_name: 15_000.0 for result in phase1_results}
        final_rankings = {result.participant_name: result.final_ranking for result in phase1_results}

        return Phase2Results(
            discussion_result=discussion,
            payoff_results=payoff_results,
            final_rankings=final_rankings,
        )


@pytest.mark.asyncio
async def test_experiment_trace_metadata(monkeypatch):
    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    config.agents = config.agents[:2]
    config.language = "Spanish"

    participant_agents = [StubParticipant(cfg) for cfg in config.agents]

    async def fake_create_participants(*_args, **_kwargs):
        return participant_agents

    monkeypatch.setattr(
        "experiment_agents.participant_agent.create_participant_agents_with_dynamic_temperature",
        fake_create_participants,
    )
    monkeypatch.setattr("core.experiment_manager.UtilityAgent", StubUtilityAgent)
    monkeypatch.setattr("core.experiment_manager.Phase1Manager", StubPhase1Manager)
    monkeypatch.setattr("core.experiment_manager.Phase2Manager", StubPhase2Manager)
    monkeypatch.setattr("core.experiment_manager.build_experiment_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        FrohlichExperimentManager,
        "_set_general_logging_info",
        lambda self, _results: None,
    )
    monkeypatch.setattr(
        FrohlichExperimentManager,
        "_set_fallback_general_info",
        lambda self, _results: None,
    )

    captured_trace = {}

    class DummyTrace:
        def __init__(self, name: str, metadata: dict) -> None:
            captured_trace["name"] = name
            captured_trace["metadata"] = metadata

        def __enter__(self):
            return SimpleNamespace(trace_id="trace-12345")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("core.experiment_manager.trace", DummyTrace)

    language_manager = SimpleNamespace(get=lambda key, **kwargs: key)
    manager = FrohlichExperimentManager(config, "config/default_config.yaml", language_manager=language_manager)
    manager.agent_logger = StubAgentLogger()

    results = await manager.run_complete_experiment()

    metadata = captured_trace["metadata"]
    assert metadata["experiment_id"] == manager.experiment_id
    assert metadata["participant_count"] == str(len(config.agents))
    assert metadata["language"] == config.language
    expected_names = ", ".join(agent.name for agent in config.agents)
    assert metadata["participant_names"] == expected_names
    assert isinstance(results.phase1_results, list) and results.phase1_results
    assert results.phase2_results.discussion_result.consensus_reached is True
