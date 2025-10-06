import unittest

from config.models import AgentConfiguration, ExperimentConfiguration
from core.distribution_generator import DistributionGenerator
from core.phase1_manager import Phase1Manager
from utils.seed_manager import SeedManager


class Phase1DeterministicRNGTest(unittest.TestCase):
    def setUp(self) -> None:
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
        self.config = ExperimentConfiguration(
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
        self.manager = Phase1Manager([], None, None, seed_manager=seed_manager)
        self.manager._build_participant_rngs(self.config)
        self.rngs = self.manager._participant_rngs
        self.saved_states = {name: rng.getstate() for name, rng in self.rngs.items()}

    def _simulate_interleaving(self, order):
        for name, rng in self.rngs.items():
            rng.setstate(self.saved_states[name])
        outputs = {name: [] for name in self.rngs}
        for participant_name in order:
            dist = DistributionGenerator.generate_dynamic_distribution(
                self.config.distribution_range_phase1,
                random_gen=self.rngs[participant_name],
            )
            outputs[participant_name].append(dist.multiplier)
        return outputs

    def test_participant_rngs_are_order_independent(self):
        sequential_order = ["Sophie"] * 4 + ["Alice"] * 4
        interleaved_order = [name for _ in range(4) for name in ("Sophie", "Alice")]

        sequential_outputs = self._simulate_interleaving(sequential_order)
        interleaved_outputs = self._simulate_interleaving(interleaved_order)

        self.assertEqual(sequential_outputs["Sophie"], interleaved_outputs["Sophie"])
        self.assertEqual(sequential_outputs["Alice"], interleaved_outputs["Alice"])


if __name__ == "__main__":
    unittest.main()
