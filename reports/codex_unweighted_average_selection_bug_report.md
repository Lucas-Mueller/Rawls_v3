Title: Average Calculation Should Be Unweighted – Diagnosis and Fix Plan

Summary
- Expected rule: When applying “Maximizing Average Income” and the two constraint variants, the average across the five income classes must be unweighted (each class counts 20%). The income-class probabilities are used only to assign an income class to an agent for payoff, not to weight the notion of “average income” in selection.
- Current behavior: The selection code optionally uses weighted averages when probabilities are provided, and the callers in both Phase 1 and Phase 2 pass probabilities into selection. This causes the chosen distribution to depend on the probability configuration, which violates the intended rule and creates confusing divergences between selection and display.

What We Observed
- Phase 2 payoff path passes `config.income_class_probabilities` into selection. If probabilities are skewed (e.g., `low = 1.0`), “maximizing average” effectively becomes “maximize the low income.”
- Phase 1 application rounds also pass probabilities into selection, so distribution choice depends on the configured probabilities there as well.
- The comprehensive outcomes display in Phase 2 does not pass probabilities and thus uses unweighted averages, which can disagree with the actual selection if probabilities are skewed.

Spec vs. Implementation
- Spec: “Average income” for principle selection is the simple, unweighted mean of the five incomes: (high + medium_high + medium + medium_low + low) / 5. Probabilities are only for random class assignment when computing an agent’s payoff under the selected distribution.
- Implementation:
  - core/distribution_generator.py
    - _apply_maximizing_average(...) uses `d.get_average_income(probabilities)` when probabilities are passed.
    - _apply_maximizing_average_floor_constraint(...) and _apply_maximizing_average_range_constraint(...) use `get_average_income(probabilities)` when probabilities are passed.
  - core/services/counterfactuals_service.py
    - apply_group_principle_and_calculate_payoffs(...) passes `config.income_class_probabilities` into `DistributionGenerator.apply_principle_to_distributions(...)` during Phase 2 selection.
  - core/phase1_manager.py
    - Also passes `probabilities` (either situation-specific or global) into `apply_principle_to_distributions(...)` during Phase 1 application rounds.
  - Displays:
    - Phase 2 comprehensive outcomes call `calculate_comprehensive_constraint_outcomes(...)` without probabilities (unweighted), while Phase 1 calls it with probabilities (weighted), creating an additional inconsistency.

Impact
- Distribution selection depends on probability configuration, contrary to the intended rule. This can:
  - Cause Phase 2 to select a different distribution than what the unweighted display suggests.
  - Make Phase 1 distribution choices differ across configs even when distributions are identical.
  - Confuse users who expect “maximizing average” to be independent of population distribution assumptions.

Root Cause
- The selection code is designed to optionally accept probabilities for “weighted average”, and both Phase 1 and Phase 2 call sites supply probabilities. This makes selection weighted-by-probabilities in practice, contrary to the experiment’s intended semantics.

Fix Plan (Precise)
1) Enforce unweighted averages in selection logic.
   - In core/distribution_generator.py
     - _apply_maximizing_average(...): compute `d.get_average_income(None)` (or use a dedicated unweighted helper), ignoring probabilities.
     - _apply_maximizing_average_floor_constraint(...): among valid distributions, choose by unweighted average (ignore probabilities).
     - _apply_maximizing_average_range_constraint(...): among valid distributions, choose by unweighted average (ignore probabilities).
     - Keep probabilities only for `calculate_payoff(...)` (class assignment), not for selection.

2) Stop passing probabilities into selection at call sites.
   - core/services/counterfactuals_service.py
     - apply_group_principle_and_calculate_payoffs(...): call `apply_principle_to_distributions(distributions, agreed_principle, probabilities=None, ...)`.
   - core/phase1_manager.py
     - When applying the participant’s chosen principle, pass `probabilities=None` to `apply_principle_to_distributions(...)`.

3) Make Phase 1 and Phase 2 displays consistent with the selection rule.
   - Phase 2: `_build_comprehensive_earnings_display()` already calls `calculate_comprehensive_constraint_outcomes(...)` without probabilities; keep it that way.
   - Phase 1: When calling `calculate_comprehensive_constraint_outcomes(...)`, pass `probabilities=None` to ensure unweighted outcomes in the display.
   - Ensure explanation strings do not say “weighted” (language keys already handle this conditional; they won’t add the “weighted” prefix once probabilities are not passed).

4) Add validation and tests.
   - Unit test: With a fixed 4-distribution set (the one from your example), force `probabilities` in the environment to `low=1.0`, and verify that selection under “maximizing average (floor non-binding)” still chooses Distribution 1 when probabilities are NOT passed to selection.
   - Unit test (Phase 1 context): Verify `phase1_manager` selects the same distribution regardless of the provided `income_class_probabilities`.
   - Unit test: `calculate_payoff(...)` still respects probabilities for random class assignment.

5) Diagnostics (optional but useful).
   - Before computing payoffs in Phase 2, log (info/debug): per-distribution floors, ranges, unweighted averages, and the final selected distribution index. This helps quickly verify correctness.
a
Minimal Change Set (surgical)
- core/distribution_generator.py
  - In `_apply_maximizing_average`, replace `d.get_average_income(probabilities)` with `d.get_average_income(None)`.
  - In `_apply_maximizing_average_floor_constraint` and `_apply_maximizing_average_range_constraint`, ensure the `key` for choosing best distribution ignores probabilities (use unweighted average).
- core/services/counterfactuals_service.py
  - apply_group_principle_and_calculate_payoffs: pass `probabilities=None` to `apply_principle_to_distributions`.
- core/phase1_manager.py
  - In principle application, pass `probabilities=None` to `apply_principle_to_distributions`.
  - In `calculate_comprehensive_constraint_outcomes` call, pass `probabilities=None` for unweighted display.
- tests/
  - Add the three tests described above.

Risks and Mitigations
- Risk: If any downstream logic relied on weighted average selection semantics, this will change outcomes. Mitigation: The stated experiment spec requires unweighted; selection must reflect that. If weighted variants are ever needed, introduce an explicit config flag (default false) and make displays match selection.
- Risk: Language strings show “weighted” terms in explanations. Mitigation: With probabilities not passed, the conditional “weighted” prefix won’t be used; no string changes are necessary.

Acceptance Criteria
- Phase 1 and Phase 2 always choose distributions based on unweighted averages for the “average” principles (with constraints applied to eligibility only).
- Changing `income_class_probabilities` does not change which distribution is selected under average-based principles; it only changes class assignment and thus the agent’s payoff.
- Phase 1 and Phase 2 displays match the selection results.

