# Phase Results i18n Alignment Plan

## Objective
Bring Phase 1 round summaries in line with the existing internationalized Phase 2 presentation so that all participant-facing tables and captions draw from translation keys instead of hard-coded English literals.

## Current Gaps
- `core/phase1_manager.py` builds the distributions table inline with English headers (`"| Income Class | Dist. 1 | ..."`) and static averages copy, bypassing the localized helpers already used elsewhere.
- Phase 1 still stitches constraint markers directly in the grouped counterfactual block; translations exist but the helper does not yet mirror the Phase 2 implementation for marker selection.

## Implementation Steps
1. **Adopt shared formatter for tables**
   - Swap the inline Markdown builder in `_build_phase1_round_results` for the `DistributionGenerator.calculate_comprehensive_constraint_outcomes(...)` output so we reuse the same localized table and class label returned there.
   - Pass Phase 1 probability weights into the helper to keep the averaged row aligned with localized Phase 2 displays.

2. **Align counterfactual markers**
   - Review `_build_grouped_counterfactual_outcomes` and ensure marker tokens (`assigned_principle`, etc.) match the keys used by Phase 2 for consistency across locales.
   - If required, add any missing translation keys to the locale JSON files; keep naming parallel to the `comprehensive_earnings.markers.*` namespace.

3. **Audit translation coverage**
   - Confirm `comprehensive_earnings.*`, `distributions.*`, and `constraint_formatting.*` entries exist for English, Spanish, and Mandarin.
   - Add or adjust YAML/JSON entries only where Phase 1 now references new keys.

4. **Regression checks**
   - Run `python run_tests.py unit` to cover formatting helpers.
   - Spot-check a Phase 1 simulation via `python main.py` in at least two languages (e.g., English, Spanish) to ensure tables and markers render correctly.

## Notes
- No fallbacks required; rely on version control for safety.
- Keep business logic unchanged—only swap display assembly to use localized utilities.
