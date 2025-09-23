"""Component tests for the SpeakingOrderService."""
from __future__ import annotations

import random

import pytest

from core.services.speaking_order_service import SpeakingOrderService
from config.phase2_settings import Phase2Settings


class StubSeedManager:
    """Deterministic seed manager for speaking order tests."""

    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)

    @property
    def random(self) -> random.Random:
        return self._random


@pytest.mark.component
def test_speaking_order_fixed_rotation():
    service = SpeakingOrderService(
        seed_manager=StubSeedManager(42),
        settings=Phase2Settings.get_default(),
    )
    order_round1 = service.generate_speaking_order(1, 3, randomize_speaking_order=False, strategy="fixed")
    order_round2 = service.generate_speaking_order(
        2,
        3,
        randomize_speaking_order=False,
        strategy="fixed",
        last_round_finisher=order_round1[-1],
    )
    assert order_round1 == [0, 1, 2]
    assert order_round2[0] != order_round1[-1]


@pytest.mark.component
def test_speaking_order_random_finisher_restriction():
    service = SpeakingOrderService(
        seed_manager=StubSeedManager(99),
        settings=Phase2Settings.get_default(),
    )
    order = service.generate_speaking_order(
        round_num=2,
        num_participants=4,
        randomize_speaking_order=True,
        strategy="random",
        last_round_finisher=1,
    )
    assert len(order) == 4
    assert order[0] != 1
    assert sorted(order) == [0, 1, 2, 3]
