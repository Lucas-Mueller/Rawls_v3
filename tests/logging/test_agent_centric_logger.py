"""Logging contract tests for `AgentCentricLogger`."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from utils.logging.agent_centric_logger import AgentCentricLogger
from models.principle_types import JusticePrinciple, CertaintyLevel, PrincipleRanking, RankedPrinciple

pytestmark = pytest.mark.contracts


def make_ranking() -> PrincipleRanking:
    return PrincipleRanking(
        rankings=[
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=1),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=2),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4),
        ],
        certainty=CertaintyLevel.SURE,
    )


def test_logger_initialization_and_updates(minimal_experiment_config):
    participants = [SimpleNamespace(name=cfg.name) for cfg in minimal_experiment_config.agents[:2]]

    logger = AgentCentricLogger()
    logger.initialize_experiment(participants, minimal_experiment_config)

    assert set(logger.agent_logs.keys()) == {p.name for p in participants}

    ranking = make_ranking()
    logger.log_initial_ranking(participants[0].name, ranking, "memory", 100.0)
    stored_log = logger.agent_logs[participants[0].name].phase_1.initial_ranking
    assert stored_log.ranking_result.rankings[0].principle == JusticePrinciple.MAXIMIZING_FLOOR
    assert stored_log.bank_balance == 100.0

    logger.set_seed_info(1234, "generated")
    assert logger.seed_used == 1234
    assert logger.seed_source == "generated"


def test_agent_logger_isolation_between_experiments(minimal_experiment_config):
    participants_a = [SimpleNamespace(name=cfg.name) for cfg in minimal_experiment_config.agents[:2]]
    participants_b = [SimpleNamespace(name=cfg.name + "-B") for cfg in minimal_experiment_config.agents[:2]]

    logger_a = AgentCentricLogger()
    logger_b = AgentCentricLogger()

    logger_a.initialize_experiment(participants_a, minimal_experiment_config)
    logger_b.initialize_experiment(participants_b, minimal_experiment_config)

    assert set(logger_a.agent_logs) == {p.name for p in participants_a}
    assert set(logger_b.agent_logs) == {p.name for p in participants_b}
    # Ensure internal state is not shared across experiment instances
    logger_a.log_initial_ranking(participants_a[0].name, make_ranking(), "memory", 42.0)
    assert participants_b[0].name not in logger_a.agent_logs
    assert logger_b.agent_logs[participants_b[0].name].phase_1.initial_ranking.ranking_result.rankings == []
*** End Patch
