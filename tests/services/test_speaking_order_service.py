"""Contract tests for `SpeakingOrderService`."""
from __future__ import annotations

import random
from dataclasses import dataclass

import pytest

from core.services.speaking_order_service import SpeakingOrderService
from config.phase2_settings import Phase2Settings

pytestmark = pytest.mark.contracts


@dataclass
class StubSeedManager:
    seed: int

    def __post_init__(self) -> None:
        self.random = random.Random(self.seed)


@dataclass
class StubLogger:
    warnings: list

    def log_warning(self, message: str) -> None:  # pragma: no cover - log-only helper
        self.warnings.append(message)


@pytest.fixture
def phase2_settings():
    settings = Phase2Settings.get_default()
    settings.min_agents_for_experiment = 2
    return settings


def test_fixed_order_rotates_to_avoid_same_starter(phase2_settings):
    service = SpeakingOrderService(settings=phase2_settings)

    order_round1 = service.generate_speaking_order(
        round_num=1,
        num_participants=3,
        randomize_speaking_order=False,
        strategy="fixed",
        last_round_finisher=None,
    )
    order_round2 = service.generate_speaking_order(
        round_num=2,
        num_participants=3,
        randomize_speaking_order=False,
        strategy="fixed",
        last_round_finisher=order_round1[-1],
    )

    assert order_round1 == [0, 1, 2]
    # Rotation should avoid the last finisher starting again
    assert order_round2[0] != order_round1[-1]


def test_random_order_reproducible_with_seed_and_finisher_restriction(phase2_settings):
    seed_manager = StubSeedManager(seed=42)
    service = SpeakingOrderService(seed_manager=seed_manager, settings=phase2_settings)

    order = service.generate_speaking_order(
        round_num=2,
        num_participants=4,
        randomize_speaking_order=True,
        strategy="random",
        last_round_finisher=3,
    )

    # Deterministic outcome based on seed
    assert order == [2, 1, 3, 0]
    assert order[0] != 3  # finisher restriction applied


def test_unknown_strategy_logs_warning_and_falls_back(phase2_settings):
    logger = StubLogger(warnings=[])
    service = SpeakingOrderService(settings=phase2_settings, logger=logger)

    order = service.generate_speaking_order(
        round_num=1,
        num_participants=3,
        randomize_speaking_order=True,
        strategy="nonexistent",
        last_round_finisher=2,
    )

    assert order == [0, 1, 2]
    assert any("Unknown speaking order strategy" in warning for warning in logger.warnings)
