# Archive: Medium Intelligence Tier Data

**Date Archived:** October 13, 2025
**Reason:** Hypothesis 3 refactored to 2-tier design (low/high intelligence only)

## Contents

This archive contains all data from the medium intelligence manipulator tier, which was removed during the Hypothesis 3 refactoring.

### Archived Directories:
- `configs/medium/` - 34 configuration files for medium intelligence manipulator experiments
- `results/medium/` - Experiment results from medium intelligence runs
- `terminal_outputs/medium/` - Terminal logs from medium intelligence runs

## Original Design (3-tier)

The original Hypothesis 3 design used three manipulator intelligence levels:
- **Low:** `google/gemma-3-27b-it` (legacy) → `gemini-2.0-flash-lite` (updated)
- **Medium:** `gemini-2.0-flash-exp-1206` (REMOVED)
- **High:** `gemini-2.5-pro` (retained)

## Updated Design (2-tier)

The refactored design uses two manipulator intelligence levels:
- **Low:** `gemini-2.0-flash-lite`
- **High:** `gemini-2.5-pro`

All base agents use `gemini-2.0-flash-lite`.

## Key Changes

1. **Model Configuration:** Switched base model from `google/gemma-3-27b-it` to `gemini-2.0-flash-lite`
2. **Tier Reduction:** Removed medium intelligence tier (gemini-2.0-flash-exp-1206)
3. **Surgical Aggregation:** Replaced prompt-based target detection with code-based Borda count aggregation of Phase 1 final rankings
4. **Statistical Analysis:** Changed from 2×3 to 2×2 contingency tables

## Restoration

If needed, this data can be restored by moving the directories back:
```bash
mv archive_medium_intelligence/configs/medium configs/
mv archive_medium_intelligence/results/medium results/
mv archive_medium_intelligence/terminal_outputs/medium terminal_outputs/
```

## Reference

See `HYPOTHESIS_3_REFACTORING_PLAN.md` for complete refactoring details.
