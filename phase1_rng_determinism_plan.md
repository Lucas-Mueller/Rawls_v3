# Phase 1 RNG Determinism Plan (Parallel-Friendly)

## Goal
Keep Phase 1 participant runs fully parallel while guaranteeing identical demonstration distributions for a fixed experiment seed.

## Determinism Strategy
- **Derive one RNG per participant** from the experiment seed using a stable formula (e.g., `base_seed + participant_index`).
- **Use that participant-specific RNG** for every call to `DistributionGenerator.generate_dynamic_distribution()` and related payoff helpers during Phase 1.
- Leave the shared `SeedManager` untouched for the rest of the system.

## Implementation Steps
1. **Extend Phase1Manager initialization**
   - Precompute a `Dict[str, random.Random]` mapping participant name → `random.Random(base_seed + stable_offset)` once `SeedManager` has been seeded.
2. **Thread RNG through Phase 1 helpers**
   - When calling `generate_dynamic_distribution`, `calculate_payoff`, and the alternative-earnings helpers inside `_step_1_3_principle_application`, pass the participant’s RNG via `random_gen=...`.
   - Ensure retries and memory updates reuse the same RNG instance (no new Random objects per call).
3. **Guard against drift**
   - Document the per-participant seeding logic and assert via tests that multipliers match across parallel runs with the same experiment seed.

## Validation
- Add/adjust a regression test in `tests/` that runs Phase 1 twice with identical seeds and compares the recorded demonstration multipliers.
- Update `seed_randomness_review.md` to record the per-participant RNG scheme.
