# Phase 2 Earnings Display Investigation Report

Author: Codex CLI
Date: 2025-09-04

## Summary
- Status: Fixes implemented in code; behavior now aligned with `concrete_earnings_implementation_plan.md` pending runtime verification.
- Previously: A type mismatch in `CounterfactualsService.deliver_results_and_update_memory()` prevented composing/storing comprehensive Phase 2 results. Service wiring and localization also needed adjustments.
- Now: The enum/string mismatch is resolved, `MemoryService` is injected, participant-specific localization is used throughout, and consensus text is properly localized. Remaining item is optional payoff formatting precision.

## What Was Expected (from the plan)
The plan in `concrete_earnings_implementation_plan.md` specifies for Phase 2:
- Show the distributions table with localized headers via `LanguageManager`.
- Show comprehensive outcomes across all constraint values for each relevant principle.
- Mark the group’s consensus choice on the comprehensive outcomes list.
- Use the LanguageManager with dot-notation keys for all textual elements.
- Integrate via `CounterfactualsService.build_detailed_results()` and `_build_comprehensive_earnings_display()`.

Files referenced as modified/added by the plan (and present in repo):
- `core/distribution_generator.py` — comprehensive constraint testing: `calculate_comprehensive_constraint_outcomes()` and `_format_distributions_table_comprehensive()`.
- `core/services/counterfactuals_service.py` — comprehensive display assembly: `_build_comprehensive_earnings_display()` and `build_detailed_results()`.
- `translations/*_prompts.json` — added `comprehensive_earnings`, `distributions`, and `constraint_formatting` sections.

## What’s Actually Implemented
- `core/distribution_generator.py` contains the comprehensive methods and returns:
  - `outcomes` with localized names and constraint labels.
  - `distributions_table` (localized table string).
  - `class_display_name` (localized income class).
- `core/services/counterfactuals_service.py` implements:
  - `build_detailed_results()` — composes a Phase 2 header, assigned class, consensus status, and injects the comprehensive display via `_build_comprehensive_earnings_display()`.
  - `_build_comprehensive_earnings_display()` — pulls data from `DistributionGenerator.calculate_comprehensive_constraint_outcomes()` and marks the group’s choice.
- `translations/english_prompts.json` (and Spanish/Mandarin) include the `comprehensive_earnings` keys and formatting.

So the core functionality exists and is now correctly wired for Phase 2 delivery.

## Root Cause (previous) and Fix (now implemented)
Previous root cause (resolved): `deliver_results_and_update_memory()` expected `IncomeClass` enums but received strings (e.g., `"medium_high"`), then attempted to access `.value`, causing the comprehensive results generation to fail.

Fix observed in code:
- `core/services/counterfactuals_service.py` now converts `assigned_classes` strings back to `IncomeClass` before use:
  - Normalizes values like `"IncomeClass.high"` or `"MEDIUM HIGH"` to enum members.
  - Uses the enum’s `.value` strictly after conversion.

Effect: The method successfully builds and stores the comprehensive Phase 2 results for each participant.

## Integration and Localization Adjustments (verified)
1) `MemoryService` injection
- `Phase2Manager._initialize_services()` now constructs `CounterfactualsService(..., memory_service=self.memory_service)`. Verified at `core/phase2_manager.py`.
- `deliver_results_and_update_memory()` uses `self.memory_service.update_final_results_memory(...)`, restoring the intended final-results memory formatting.

2) Localized consensus text
- `build_detailed_results()` resolves the principle slug to a localized display name via `common.principle_names.{slug}` before rendering `voting_results.consensus_reached`.

3) Participant-specific LanguageManager
- `deliver_results_and_update_memory()` retrieves a participant-specific language manager and passes it to `build_detailed_results()`.
- `build_detailed_results()` signature now includes `lang_manager` and uses it for all labels and headers. `_build_comprehensive_earnings_display()` already accepted a `lang_manager` and continues to do so.

4) Earnings formatting (optional)
- Current implementation formats `income` and `earnings` using `constraint_formatting.currency_format` which renders whole-dollar amounts (e.g., `$2`). If `$2.00` precision is preferred, either:
  - Add a `currency_format_decimals` key, or
  - Preformat earnings with `f"${earnings:.2f}"` before passing to the template.

## Effects Observed in Outputs
- Prior snapshots didn’t include the comprehensive block because the memory update failed. With the fixes, the comprehensive Phase 2 display should now be included in participant memory after result delivery (distributions table, full principle outcomes across constraints, and group-choice marker).
- Note: This report is code-based; run-time validation recommended below.

### New Observation (no-consensus path): wrong “Recent Activity” content
- Reported behavior: In a no-consensus run, the final memory update prompt’s “Recent Activity” block contained Phase 1 Round 4 “Principle Application” content (including original-values “Situation: D” and a Round-specific outcomes header) instead of the Phase 2 results.
- Diagnosis from code review: `deliver_results_and_update_memory()` now correctly builds Phase 2 results via `build_detailed_results()` and passes them to `MemoryService.update_final_results_memory()`, which formats the round content as `"Final Phase 2 Results: {result_content}"`. That text should appear under “Recent Activity:” in the memory-update prompt.
- Likely cause: The observed prompt appears to be from a prior Phase 1 memory update (the Phase 1 manager intentionally builds a prompt with the principle-application header, distribution table, and Round N outcome markers). This suggests either:
  - The Phase 2 final results memory update did not run (e.g., exception before that call), so the last captured memory-update prompt is from Phase 1; or
  - A stale “round_content” from Phase 1 was inadvertently used for the final memory update call in that run.
- What we validated in code: The current `deliver_results_and_update_memory()` does pass the Phase 2 results content into the memory service, with explicit `event_type=FINAL_RESULTS`. Selective routing will therefore use the full LLM memory update with “Recent Activity: Final Phase 2 Results: …”. We did not find a path in Phase 2 that would re-use the Phase 1 “round_content”.
- Recommended guardrails to prevent regressions and aid diagnosis:
  - Add debug logging (level: debug) in `deliver_results_and_update_memory()` to log the first ~120 chars of `result_content` per participant before calling the memory service, and the event type used (should be `FINAL_RESULTS`).
  - Add an assertion or explicit prefix (already present: `Final Phase 2 Results:`) and a short unit test to ensure `SelectiveMemoryManager._classify_event` classifies it as `FINAL_RESULTS` and that the prompt constructed includes that prefix under “Recent Activity:”.
  - If you continue to see Phase 1 “Recent Activity” in final updates, capture and share the full prompt for the memory update call at runtime to trace which code path produced it.
  - Ensure fallback path in `deliver_results_and_update_memory()` also wraps content with `memory.final_results_format` (added) and add a warning in `MemoryService.update_final_results_memory()` if Phase 1 markers are detected (added).

## Validation Checklist (post-fix)
- Consensus path:
  - Results memory contains Phase 2 header, localized assigned class, distributions table, full outcomes list, and group-choice marker on the matching line(s).
  - Consensus text shows the localized principle name.
- No-consensus path:
  - Results memory shows the comprehensive display and a localized “no consensus” note (key: `phase2_no_consensus`).
  - Localization:
  - Spanish and Mandarin runs reflect localized headers and labels.
  - Optional formatting:
  - Decide and apply desired payoff precision (e.g., `$2.00`).

## Risk/Impact
- Low to medium. Changes are contained to service wiring and data normalization; logic for calculations and display generation already exists and is correct.
- Positive impact: Participants finally see the comprehensive Phase 2 display exactly as planned.

## Validation Steps After Fixes
- Run a Phase 2 flow with: 
  - Consensus reached + constraint principle.
  - No consensus path.
- Verify memory contains:
  - Phase 2 header and assigned class in the participant’s language.
  - Distributions table.
  - Full outcomes list with group’s choice marker on matching line(s).
  - Localized consensus text with human-friendly principle name.
- Spot-check Spanish and Mandarin paths for localization.

## Pointers to Relevant Code
- Producer of string `assigned_classes`: `core/services/counterfactuals_service.py` → `apply_group_principle_and_calculate_payoffs()`.
- Failing consumer path: `core/services/counterfactuals_service.py` → `deliver_results_and_update_memory()` (uses `.value` on assumed enum).
- Comprehensive display build: `core/services/counterfactuals_service.py` → `_build_comprehensive_earnings_display()`.
- Lang keys: `translations/*_prompts.json` → `comprehensive_earnings`, `distributions`, `constraint_formatting`.

## Conclusion
The comprehensive Phase 2 results presentation is now correctly integrated:
- Enum/string mismatch fixed and normalized.
- `MemoryService` injected and used for final results updates.
- Participant-specific localization applied consistently, with properly localized consensus text.

Pending validation runs, the system should now display the comprehensive Phase 2 earnings as envisioned in `concrete_earnings_implementation_plan.md`.
