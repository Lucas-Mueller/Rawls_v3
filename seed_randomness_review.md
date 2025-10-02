# Seed Randomness Review

## Overview
This document tracks the randomness and seeding surface of the Frohlich Experiment. It summarises what is now deterministically controlled by the experiment-scoped RNG, notes the fixes applied in this pass, and flags any remaining watchpoints.

## Current Status (✅ deterministic)
- **Dynamic distributions** – Phase 2 continues to pass the experiment `SeedManager.random` into `DistributionGenerator.generate_dynamic_distribution()` (`core/services/counterfactuals_service.py`), keeping multipliers stable for a fixed seed.
- **Phase 1 parallelism** – Each participant uses a dedicated RNG derived from the experiment seed (`core/phase1_manager.py`), so asynchronous scheduling no longer affects demonstration distributions or earnings.
- **Phase 1 alternative earnings** – `DistributionGenerator.calculate_alternative_earnings()` now receives the seeded RNG, keeping the "fresh draw" what-if earnings aligned with the run seed.
- **Counterfactual transparency** – Because the distribution set is deterministic, all Phase 2 counterfactual tables, explanations, and payoff assignments are reproducible.
- **Configuration hash** – `SeedManager.generate_seed_from_config()` incorporates speaking-order flags, selective memory knobs, retry settings, Phase 2 settings, and logging options so distinct experiment configurations map to distinct seeds.
- **Notebook helper** – `utils/experiment_runner.generate_random_config()` accepts an optional `seed` argument so ad-hoc experiments can be regenerated.
- **Tests** – Unit and integration suites exercise the instance-based RNG path and verify deterministic behaviour for distributions and alternative earnings.

## Previously Identified Gaps (now resolved)
1. **Dynamic distributions ignored the seed** – Calls lacked a `random_gen`. Fix: thread `self.seed_manager.random` through both phase managers.
2. **Phase 1 alternative earnings used the global RNG** – Added the seeded generator when invoking `calculate_alternative_earnings()`.
3. **Counterfactual pipeline relied on unseeded distributions** – Eliminated by the distribution fix above.
4. **Tests only covered deprecated global seeding** – Integration tests now rely on the instance RNG and include a dedicated regression for `SeedManager.random`.
5. **Config hash omitted behaviour toggles** – Hash now serialises additional configuration fields (speaking order, memory, retries, logging, Phase 2 settings).
6. **Notebook helper produced non-replayable configs** – Optional seed parameter added.

## Deterministic Spot Check
```python
from utils.seed_manager import SeedManager
from config.models import ExperimentConfiguration
from core.distribution_generator import DistributionGenerator

config = ExperimentConfiguration(
    language="English",
    agents=[
        {"name": "A", "personality": "", "model": "m", "temperature": 0,
         "memory_character_limit": 1, "reasoning_enabled": False, "language": "english"},
        {"name": "B", "personality": "", "model": "m", "temperature": 0,
         "memory_character_limit": 1, "reasoning_enabled": False, "language": "english"}
    ],
    utility_agent_model="m",
    utility_agent_temperature=0,
    phase2_rounds=1,
    distribution_range_phase1=(0.5, 2.0),
    distribution_range_phase2=(0.5, 2.0)
)

seed_manager = SeedManager()
seed_manager.initialize_from_config(config)
first = DistributionGenerator.generate_dynamic_distribution(
    (0.5, 2.0), random_gen=seed_manager.random
)
seed_manager.set_seed(seed_manager.current_seed)
second = DistributionGenerator.generate_dynamic_distribution(
    (0.5, 2.0), random_gen=seed_manager.random
)
assert first.multiplier == second.multiplier
```

## Remaining Watchpoints
- The deprecated global seeding helpers (`SeedManager.set_experiment_seed`, `SeedManager.initialize_reproducibility`) remain for backwards compatibility. Avoid relying on them for new code.
- Any future randomness entry points should accept an optional `random_gen` argument so the experiment RNG can be propagated without modification.
