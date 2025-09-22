"""Acceptance test exercising the experiment manager with stubbed phase managers."""

from __future__ import annotations

import pytest

from core.experiment_manager import FrohlichExperimentManager
from core.phase1_manager import Phase1Manager
from core.phase2_manager import Phase2Manager
from models import (
    Phase1Results,
    Phase2Results,
    PrincipleRanking,
    RankedPrinciple,
    PrincipleChoice,
    ApplicationResult,
    IncomeDistribution,
    IncomeClass,
    CertaintyLevel,
    JusticePrinciple,
    GroupDiscussionResult,
)
from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture
from tests.utils.stub_scripts import load_and_register, load_transcript


def _make_ranking() -> PrincipleRanking:
    return PrincipleRanking(
        rankings=[
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4),
        ],
        certainty=CertaintyLevel.SURE,
    )


async def _stub_phase1(self: Phase1Manager, config, logger=None, process_logger=None):
    ranking = _make_ranking()
    choice = PrincipleChoice.create_for_parsing(JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE)
    distribution = IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000)
    application = ApplicationResult(
        round_number=1,
        principle_choice=choice,
        chosen_distribution=distribution,
        assigned_income_class=IncomeClass.MEDIUM,
        earnings=18000,
        alternative_earnings={JusticePrinciple.MAXIMIZING_AVERAGE.value: 19500},
    )
    participant = self.participants[0]
    second_participant = self.participants[1]
    return [
        Phase1Results(
            participant_name=participant.name,
            initial_ranking=ranking,
            post_explanation_ranking=ranking,
            application_results=[application],
            final_ranking=ranking,
            total_earnings=52000,
            final_memory_state="Participant 1 memory",
        ),
        Phase1Results(
            participant_name=second_participant.name,
            initial_ranking=ranking,
            post_explanation_ranking=ranking,
            application_results=[application],
            final_ranking=ranking,
            total_earnings=48000,
            final_memory_state="Participant 2 memory",
        ),
    ]


async def _stub_phase2(self: Phase2Manager, config, phase1_results, logger=None, process_logger=None):
    discussion = GroupDiscussionResult(
        consensus_reached=True,
        agreed_principle=PrincipleChoice.create_for_parsing(
            JusticePrinciple.MAXIMIZING_FLOOR, certainty=CertaintyLevel.SURE
        ),
        final_round=1,
        discussion_history="AgentA: Floor principle wins",
        vote_history=[],
    )

    final_rankings = {result.participant_name: result.final_ranking for result in phase1_results}
    payoff_results = {result.participant_name: result.total_earnings for result in phase1_results}

    return Phase2Results(
        discussion_result=discussion,
        payoff_results=payoff_results,
        final_rankings=final_rankings,
    )


async def _stub_phase2_deadlock(self: Phase2Manager, config, phase1_results, logger=None, process_logger=None):
    discussion = GroupDiscussionResult(
        consensus_reached=False,
        agreed_principle=None,
        final_round=3,
        discussion_history="Agents could not reach agreement",
        vote_history=[],
    )

    final_rankings = {result.participant_name: result.final_ranking for result in phase1_results}
    payoff_results = {result.participant_name: 0 for result in phase1_results}

    return Phase2Results(
        discussion_result=discussion,
        payoff_results=payoff_results,
        final_rankings=final_rankings,
    )


def _build_discussion_history(transcript):
    lines = []
    for agent, statements in transcript.items():
        for idx, statement in enumerate(statements, start=1):
            lines.append(f"{agent} (round {idx}): {statement}")
    return "\n".join(lines)


@pytest.mark.asyncio
@pytest.mark.acceptance
async def test_run_complete_experiment(monkeypatch, stubbed_runner):
    """Verify the experiment manager orchestrates phases and returns results."""

    config = ExperimentTestFixture.create_minimal_config(num_agents=2)
    monkeypatch.setattr(Phase1Manager, "run_phase1", _stub_phase1, raising=False)
    monkeypatch.setattr(Phase2Manager, "run_phase2", _stub_phase2, raising=False)

    load_and_register(stubbed_runner, "consensus")

    manager = FrohlichExperimentManager(config)
    results = await manager.run_complete_experiment()

    assert results.phase2_results.discussion_result.consensus_reached is True
    assert set(results.phase2_results.payoff_results.keys()) == {"TestAgent1", "TestAgent2"}
    assert results.phase2_results.discussion_result.agreed_principle.principle == JusticePrinciple.MAXIMIZING_FLOOR


@pytest.mark.asyncio
@pytest.mark.acceptance
async def test_run_experiment_deadlock(monkeypatch, stubbed_runner):
    """Smoke test verifying non-consensus scenarios remain stable."""

    config = ExperimentTestFixture.create_minimal_config(num_agents=2)
    monkeypatch.setattr(Phase1Manager, "run_phase1", _stub_phase1, raising=False)
    monkeypatch.setattr(Phase2Manager, "run_phase2", _stub_phase2_deadlock, raising=False)

    load_and_register(stubbed_runner, "deadlock")

    manager = FrohlichExperimentManager(config)
    results = await manager.run_complete_experiment()

    assert results.phase2_results.discussion_result.consensus_reached is False
    assert all(value == 0 for value in results.phase2_results.payoff_results.values())


@pytest.mark.asyncio
@pytest.mark.acceptance
@pytest.mark.parametrize("language", [SupportedLanguage.ENGLISH, SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN])
async def test_multilingual_multi_round_discussion(monkeypatch, stubbed_runner, language):
    """Ensure multi-round, multi-language scenarios maintain discussion history."""

    transcript = load_transcript("multilingual_multi_round")
    history = _build_discussion_history(transcript)

    async def _phase2_multi(self: Phase2Manager, config, phase1_results, logger=None, process_logger=None):
        discussion = GroupDiscussionResult(
            consensus_reached=False,
            agreed_principle=None,
            final_round=3,
            discussion_history=history,
            vote_history=[],
        )
        return Phase2Results(
            discussion_result=discussion,
            payoff_results={result.participant_name: 0 for result in phase1_results},
            final_rankings={result.participant_name: result.final_ranking for result in phase1_results},
        )

    config = ExperimentTestFixture.create_minimal_config(num_agents=2)
    config.language = language.value
    monkeypatch.setattr(Phase1Manager, "run_phase1", _stub_phase1, raising=False)
    monkeypatch.setattr(Phase2Manager, "run_phase2", _phase2_multi, raising=False)

    load_and_register(stubbed_runner, "multilingual_multi_round")

    manager = FrohlichExperimentManager(config)
    results = await manager.run_complete_experiment()

    assert results.phase2_results.discussion_result.discussion_history == history
    assert results.phase2_results.discussion_result.final_round == 3
