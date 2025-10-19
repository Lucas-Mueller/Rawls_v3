from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import pytest

from config.models import AgentConfiguration, ExperimentConfiguration
from core.distribution_generator import DistributionGenerator
from core.phase1_manager import Phase1Manager
from utils.seed_manager import SeedManager


def _build_rng_fixture() -> Tuple[ExperimentConfiguration, Dict[str, object], Dict[str, object]]:
    agents = [
        AgentConfiguration(
            name="Sophie",
            personality="test",
            model="stub",
            temperature=0.0,
            memory_character_limit=100,
            reasoning_enabled=False,
            language="english",
        ),
        AgentConfiguration(
            name="Alice",
            personality="test",
            model="stub",
            temperature=0.0,
            memory_character_limit=100,
            reasoning_enabled=False,
            language="english",
        ),
    ]
    config = ExperimentConfiguration(
        language="English",
        agents=agents,
        utility_agent_model="stub",
        utility_agent_temperature=0.0,
        phase2_rounds=1,
        randomize_speaking_order=False,
        speaking_order_strategy="fixed",
        distribution_range_phase1=(1.0, 2.0),
        distribution_range_phase2=(1.0, 2.0),
    )

    seed_manager = SeedManager()
    seed_manager.set_seed(1234)
    manager = Phase1Manager([], None, None, seed_manager=seed_manager)
    manager._build_participant_rngs(config)
    rngs = manager._participant_rngs
    saved_states = {name: rng.getstate() for name, rng in rngs.items()}
    return config, rngs, saved_states


def _simulate_interleaving(
    config: ExperimentConfiguration,
    rngs: Dict[str, object],
    saved_states: Dict[str, object],
    order: Iterable[str],
) -> Dict[str, List[float]]:
    for name, rng in rngs.items():
        rng.setstate(saved_states[name])
    outputs: Dict[str, List[float]] = {name: [] for name in rngs}
    for participant_name in order:
        dist = DistributionGenerator.generate_dynamic_distribution(
            config.distribution_range_phase1,
            random_gen=rngs[participant_name],
        )
        outputs[participant_name].append(dist.multiplier)
    return outputs


def test_participant_rngs_are_order_independent():
    config, rngs, saved_states = _build_rng_fixture()

    sequential_order = ["Sophie"] * 4 + ["Alice"] * 4
    interleaved_order = [name for _ in range(4) for name in ("Sophie", "Alice")]

    sequential_outputs = _simulate_interleaving(config, rngs, saved_states, sequential_order)
    interleaved_outputs = _simulate_interleaving(config, rngs, saved_states, interleaved_order)

    assert sequential_outputs["Sophie"] == interleaved_outputs["Sophie"]
    assert sequential_outputs["Alice"] == interleaved_outputs["Alice"]
