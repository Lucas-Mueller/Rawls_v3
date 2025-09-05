Title: Phase 2 Principle Selection Bug – Diagnosis and Fix Plan

Summary
- Issue: After consensus on “Maximizing Average with Floor Constraint ($13,000)”, the payoff distribution used matched Distribution 4 (max floor) instead of the correct Distribution 1 (max weighted average subject to a non‑binding floor).
- Evidence: Final payoff shown was $10.33 for the Low class, which corresponds to Distribution 4’s low income ($103,262 → $10.33). However, with the same distribution set, the weighted average (using config probabilities) is highest for Distribution 1, and the $13,000 floor is not binding for any distribution.
- Scope: Phase 2 payoff selection path and the consensus message formatting.

Observed Anomaly (from your transcript)
- Consensus reached: Maximizing Average with Floor Constraint.
- Table (EXPERIMENT DISTRIBUTIONS AND SELECTION MAPPING) showed:
  - Dist 1 low: $82,610; Dist 2 low: $89,494; Dist 3 low: $96,378; Dist 4 low: $103,262
- “Final Phase 2 Results” used Low class income $103,262 → $10.33 (i.e., Distribution 4).
- Comprehensive outcomes list correctly showed:
  - Maximizing Average Income → Distribution 1 (for the same set, also consistent with weighted averages)
  - Floor constraint lines at each distribution’s floor (≤ $82,610, ≤ $89,494, ≤ $96,378, ≤ $103,262) selected distributions as expected.

What Should Have Happened
- With floor = $13,000, all four distributions satisfy the floor (since all lows ≥ $82,610). Therefore selection should reduce to “Maximizing Average Income” among all 4, which this distribution set clearly indicates is Distribution 1 (also for the weighted case).

Key Implementation Flow (Phase 2 payoff)
- Voting/consensus:
  - core/services/voting_service.py → TwoStage voting via core/two_stage_voting_manager.py
  - The agreed principle is a models.PrincipleChoice with fields: `principle` (JusticePrinciple) and `constraint_amount` (int).
- Apply consensus and compute payoffs:
  - core/services/counterfactuals_service.py: apply_group_principle_and_calculate_payoffs()
    - Generates dynamic distribution set.
    - Calls DistributionGenerator.apply_principle_to_distributions(distributions, agreed_principle, income_class_probabilities, language_manager)
    - Assigns income classes and computes payoffs from the chosen distribution.
- Distribution selection logic:
  - core/distribution_generator.py:
    - _apply_maximizing_average_floor_constraint(): filters by `d.low >= floor_constraint`, then chooses highest weighted average via get_average_income(probabilities).
    - get_average_income() uses IncomeClassProbabilities (default_config.yaml: High 5%, Medium High 10%, Medium 50%, Medium Low 25%, Low 10%).

Reproduction Check Against the Provided Numbers
- Weighted average (High 5%, MH 10%, M 50%, ML 25%, Low 10%):
  - Dist 1: ≈ $142,847
  - Dist 2: ≈ $131,832
  - Dist 3: ≈ $136,651
  - Dist 4: ≈ $124,948
- Floor = $13,000 does not bind (all lows well above).
- Correct choice: Distribution 1. Actual payoff used: Distribution 4.

Most Likely Root Causes
1) Wrong principle applied in payoff path (maximizing floor instead of maximizing average with floor constraint).
   - Symptom match: Distribution 4 has the highest floor ($103,262). Selecting Dist 4 is exactly what “Maximizing Floor Income” would do in this set.
   - Where it could happen: In CounterfactualsService.apply_group_principle_and_calculate_payoffs() when passing the agreed principle to DistributionGenerator.apply_principle_to_distributions(). If the `principle` enum on the PrincipleChoice were incorrect at this point (e.g., mis‑serialized earlier, or replaced via fallback), payoff would follow the wrong branch.

2) Constraint amount misapplied in the payoff path (e.g., compared against the wrong unit or substituted with the maximum observed floor).
   - If the code inadvertently used the distribution’s maximum floor as the constraint, only Dist 4 (low = $103,262) would qualify, which reproduces the observed outcome.
   - If the captured constraint was lost (None) and a fallback path silently defaulted to the highest floor selection, results match Dist 4. Note: passing None into floor filter would raise a type error, so a silent fallback would need to be happening earlier (e.g., an incorrect PrincipleChoice constructed on a fallback path).

3) Consensus message omitted the amount (formatting drift), hinting the constraint was not present at build time.
   - The message showed: “Consensus reached: Maximizing Average with Floor Constraint.” (no amount). In VotingService, the constraint is included when `constraint_amount is not None` using `voting_results.consensus_with_constraint`.
   - This suggests the amount may have been lost on the object used for message formatting, which supports (1) or (2) where an alternate PrincipleChoice (lacking amount) was used for either display or payoff.

What Looks Correct (and should not be changed)
- Selection logic in DistributionGenerator for constrained average:
  - Filters by floor, then maximizes weighted average. This matches the intended policy.
- Comprehensive outcomes display:
  - Correctly enumerates outcomes for floor constraints equal to each distribution’s floor, and range constraints equal to each distribution’s range.
  - These lines match the provided numbers and are internally consistent.

Addendum: Deeper Diagnosis and Confirmed Root Cause

- Where the final outcome is calculated
  - Selection and payoff are determined in `core/services/counterfactuals_service.py::apply_group_principle_and_calculate_payoffs()`.
    - It calls `DistributionGenerator.apply_principle_to_distributions(distribution_set.distributions, discussion_result.agreed_principle, config.income_class_probabilities, language_manager=self.language_manager)`.
    - Note the third argument: `config.income_class_probabilities`. This makes selection use weighted averages when the principle involves averages (as intended by design).
  - The comprehensive outcomes shown in Phase 2 are built in `_build_comprehensive_earnings_display()` by calling `DistributionGenerator.calculate_comprehensive_constraint_outcomes(distribution_set.distributions, assigned_class_enum, lang_manager)` — without probabilities. That means unweighted averages in the display.

- Why Distribution 4 was chosen in your run
  - In `experiment_results_20250905_032008.json`, top-level `general_information.income_class_probabilities` are:
    `{ high: 0.0, medium_high: 0.0, medium: 0.0, medium_low: 0.0, low: 1.0 }`.
  - With these probabilities, maximizing (weighted) average depends only on the low income. Among your distributions, Dist 4 has the highest low ($103,262), so both “Maximizing Average” and “Maximizing Average with Floor Constraint” (when the floor is non-binding) select Dist 4.
  - The comprehensive outcomes section, however, computed using unweighted averages, still shows Dist 1 as the “maximizing average” choice — hence the discrepancy.

- Consensus amount display
  - The short consensus message you saw lacked the amount. The voting service includes the amount when available, but the high-level summary you quoted likely came from a path (general information block) that does not record the amount. This did not affect selection; it’s a messaging consistency issue.

- Updated Fix Plan (precise)
  1) Consistency: Use the same weighting in display as in selection for Phase 2.
     - Pass `config.income_class_probabilities` into `calculate_comprehensive_constraint_outcomes()` when called from `_build_comprehensive_earnings_display()`.
     - Ensure explanation strings include the “weighted” qualifier (LanguageManager already supports it).
  2) Diagnostics: Before computing payoffs, log the per-distribution weighted averages, floors, and the valid set after applying the constraint, then the selected index.
  3) Defense-in-depth: If a constrained principle arrives without `constraint_amount`, log and fall back to unconstrained maximizing average (not maximizing floor). This prevents silent semantic drift if any upstream parsing fails.
  4) Settings: Expose and raise the maximum amount for constraints in Phase 2 (≥ 150,000) to reflect scaled distributions (multipliers 4–8), preventing valid amounts from being rejected.
  5) Display clarity: Add an explicit line for the actual group constraint in the comprehensive outcomes (if it’s not already one of the distributions’ floor values), and mark it as the group choice.
  6) Tests: Add unit tests showing Dist 1 vs. Dist 4 selection under default vs. `low=1.0` probabilities, and an integration test asserting Phase 2 selection matches expectations under given probabilities.


Targeted Fix Plan
1) Add explicit selection diagnostics before payoff is computed.
   - In CounterfactualsService.apply_group_principle_and_calculate_payoffs(), log:
     - `principle`: slug and human name
     - `constraint_amount`
     - For each distribution: floor, range, weighted average
     - Valid set after constraint filtering
     - Final selected distribution index
   - Purpose: make misapplication immediately visible (wrong branch or wrong filter).

2) Guard against constraint loss and wrong-branch fallbacks.
   - Before calling apply_principle_to_distributions():
     - Assert: if principle is a constraint variant, `constraint_amount is not None`.
     - If missing, log an error with the last VoteResult and return a safe fallback: maximizing average (not maximizing floor), since a missing constraint for a “constrained average” principle should not convert semantics to “maximize floor”.
   - Ensure the exact PrincipleChoice that determined consensus is the one passing through to payoff (no reconstruction that could drop the amount).

3) Verify and extend amount validation bounds for scaled Phase 2 incomes.
   - Current amount_max_reasonable default is 100,000 (TwoStageVotingManager._validate_amount_specification). With multipliers [4,8], floors can reach ~120,000. If any agent proposes, say, $130,000, it would be rejected and the constraint could be lost.
   - Action: make amount bounds configurable and set Phase 2 max to ≥ 150,000 by default. This avoids silent losses in high‑scale rounds.

4) Display clarity: show the actual group constraint line in the comprehensive outcomes.
   - calculate_comprehensive_constraint_outcomes() currently tests floors equal to each distribution’s floor. Add one entry for the actual group constraint amount (if it’s not already one of those values). This will render and mark the precise group choice line, reducing confusion.

5) Unit safety checks.
   - Confirm end‑to‑end that constraint amounts are interpreted as income dollars (not payoff dollars) across parsing, logging, selection, and display. If any participant‑language adaptation ever yields amounts like “13” for “$13,000”, normalize at parse time.

Proposed Code Changes (high level)
- core/services/counterfactuals_service.py
  - In apply_group_principle_and_calculate_payoffs():
    - Add pre‑selection diagnostics and assertions for constrained principles.
    - If constrained principle but missing `constraint_amount`, log error and use maximizing average (not maximizing floor) as a deliberate fallback.
  - In _build_comprehensive_earnings_display(): pass the consensus (principle + amount) into DistributionGenerator.calculate_comprehensive_constraint_outcomes() and merge an extra outcome for the exact group constraint if needed; ensure the marker always appears on the line for the group’s actual constraint.

- core/two_stage_voting_manager.py
  - Expose amount range via settings and bump defaults (e.g., `amount_max_reasonable = 200_000`).
  - Add explicit logging when an amount is rejected by range validation (so we can correlate constraint loss with observed outcomes/messages).

- tests/
  - Add a unit test for DistributionGenerator._apply_maximizing_average_floor_constraint() with a fixed distribution set and probabilities, asserting that a non‑binding floor (e.g., $13,000) selects Distribution 1 for the provided table.
  - Add an integration test simulating Phase 2 with a fixed seed and forcing consensus on “Maximizing Average with Floor Constraint ($13,000)”, then assert that the payoff distribution index equals the expected one.

Acceptance Criteria
- For the distribution set matching the provided numbers, with floor = $13,000 and default probabilities, the selected distribution is Distribution 1.
- Consensus messages include the constraint amount (e.g., “[CONSENSUS] Consensus reached: Maximizing Average with Floor Constraint ($13,000)”).
- Comprehensive outcomes display includes a marked line for the exact group constraint, not just the per‑distribution floors.
- Selection diagnostics appear in logs for verification.

Appendix: Key Code References
- Selection logic:
  - core/distribution_generator.py
    - _apply_maximizing_average_floor_constraint() – filter by floor then maximize weighted average
    - IncomeDistribution.get_average_income()
- Payoff path:
  - core/services/counterfactuals_service.py
    - apply_group_principle_and_calculate_payoffs()
    - calculate_phase2_counterfactuals()
    - build_detailed_results() and _build_comprehensive_earnings_display()
- Voting/consensus construction:
  - core/services/voting_service.py (conduct_voting_process(), conduct_secret_ballot())
  - core/two_stage_voting_manager.py (_convert_to_principle_choice(), _validate_amount_specification())

Notes
- The correctness of the comprehensive outcomes section in your transcript strongly suggests the pure selection logic in DistributionGenerator is fine. The failure likely occurs in how the agreed principle (and/or its amount) flows into the payoff selection. The proposed diagnostics and guards aim to catch exactly that.
