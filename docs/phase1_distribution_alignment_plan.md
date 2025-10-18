# Phase 1 Distribution-Principle Alignment Plan

## Overview
Phase 1 currently mixes weighted and unweighted logic when applying justice principles to income distributions. The mismatches appear in the alternative earnings calculations used for participant feedback and logging. This document captures the observed behavior, articulates the desired target state, and lays out a concise implementation plan to close the gap.

## Current State
- The live principle application correctly passes round-specific income-class probabilities into `DistributionGenerator.apply_principle_to_distributions` and `calculate_payoff` when available (`core/phase1_manager.py:734-747`).
- Counterfactual helpers that populate participant memory and the agent-centric logger do **not** reuse those probabilities:
  - `calculate_alternative_earnings_by_principle` ignores weighted probabilities and re-runs distribution choice + class assignment with uniform assumptions (`core/distribution_generator.py:291-346`).
  - `calculate_alternative_earnings_by_principle_fixed_class` reuses `apply_principle_to_distributions` without probabilities, so weighted rounds can cite the wrong counterfactual distribution even though the class is fixed (`core/distribution_generator.py:349-420`).
  - `calculate_alternative_earnings` keeps the legacy behavior of uniform class draws for each distribution (`core/distribution_generator.py:274-288`).
- As a result, participants and downstream analytics see counterfactual earnings that can diverge from the weighted rule set used in the actual round, especially in original-values mode where each round defines different probabilities.

## Target State
- All Phase 1 counterfactuals should respect the same probability model that governed the live decision.
- Principle application helpers must produce consistent distribution selections regardless of whether they serve primary or counterfactual paths.
- Legacy structures (return types, random generator injection, logging hooks) should remain stable so no consumers need to change.

## Implementation Plan
1. **Thread Probabilities Through Counterfactual Helpers**
   - Extend `calculate_alternative_earnings`, `calculate_alternative_earnings_by_principle`, and `calculate_alternative_earnings_by_principle_fixed_class` to accept an optional `probabilities` argument.
   - Reuse the existing weighted code paths inside these helpers, only falling back to uniform logic when probabilities are `None`.

2. **Update Phase 1 Manager Calls**
   - Pass the round-specific probabilities already computed in `_step_1_3_principle_application` into all three helper invocations so participants see internally consistent results (`core/phase1_manager.py:749-767`).

3. **Refresh Tests**
   - Add focused unit coverage in `tests/unit/test_distribution_generator.py` that asserts weighted inputs change the chosen distributions/earnings for the counterfactual helpers.
   - Where possible, confirm deterministic behavior by seeding `random.Random` instances.

4. **Regression Validation**
   - Run `pytest tests/unit/test_distribution_generator.py` to verify the updated distribution generator logic.
   - Optionally execute a short Phase 1 dry run (`python main.py`) to inspect log outputs for weighted rounds.

Following this plan keeps the solution lean, leverages existing utilities, and avoids introducing fallback branches that version control already makes unnecessary.
