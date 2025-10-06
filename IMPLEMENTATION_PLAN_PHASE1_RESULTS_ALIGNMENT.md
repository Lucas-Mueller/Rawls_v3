# Implementation Plan: Align Phase 1 Results Format with Phase 2 Explicit Structure

## Overview

Align Phase 1 round results presentation with the new Phase 2 explicit causal narrative format. Currently Phase 1 uses a simple header-value format with flat listing of all constraint variations, while Phase 2 now uses explicit causality, grouped constraints, and comprehensive context.

**Target file:**
- `core/phase1_manager.py` (lines 779-892: `_handle_application_round` method)

**Translation files:**
- `translations/english_prompts.json`
- `translations/spanish_prompts.json`
- `translations/mandarin_prompts.json`

---

## Current Phase 1 Format (Problems)

```
=== Payoff Notification ===

Chosen principle: Maximizing Average with Floor Constraint ($59,754)
Assigned class: Medium high
Distribution multiplier: 1.5
Your payoff: $13.44

Outcome for each principle for class Medium high:
- Maximizing Floor Income → Distribution 4 → $99,591 → $9.96
- Maximizing Average Income → Distribution 1 → $134,448 → $13.44
- Maximizing Average with Floor Constraint Floor constraint ≤ $59,754 → Distribution 1 → $134,448 → $13.44 ← Your assigned principle
- Maximizing Average with Floor Constraint Floor constraint ≤ $64,734 → Distribution 3 → $119,509 → $11.95
- Maximizing Average with Floor Constraint Floor constraint ≤ $71,123 → Distribution 2 → $105,321 → $10.53
- Maximizing Average with Range Constraint Range constraint ≤ $45,000 → Distribution 2 → $110,234 → $11.02
- Maximizing Average with Range Constraint Range constraint ≤ $52,000 → Distribution 4 → $98,432 → $9.84
```

### Issues:
1. ❌ No distributions table reminder in results
2. ❌ No class probabilities shown
3. ❌ No explicit causal narrative
4. ❌ No counterfactual purpose statement
5. ❌ Constraint variations in flat list (not grouped)
6. ❌ No explicit difference calculations
7. ❌ Less clear for LLM comprehension

---

## New Phase 1 Format (Target)

```
=== Round X Payoff Notification ===

Principle chosen: Maximizing Average with Floor Constraint Floor constraint $59,754

The probabilities for each income class are:
- High: 10%
- Medium high: 20%
- Medium: 40%
- Medium low: 20%
- Low: 10%

You were assigned to the income class Medium high

These were the Round X Distributions:

| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |
|--------------|---------|---------|---------|---------|
| High         | $180,000| $160,000| $170,000| $140,000|
| Medium high  | $134,448| $120,000| $119,509| $99,591 |
| Medium       | $100,000| $95,000 | $98,000 | $90,000 |
| Medium low   | $70,000 | $75,000 | $72,000 | $80,000 |
| Low          | $59,754 | $64,734 | $71,123 | $85,000 |

Your chosen principle was Maximizing Average with Floor Constraint Floor constraint $59,754 which resulted in Distribution 1. You were assigned to the income class Medium high, resulting in a yearly income of $134,448 (which converts to a payoff of $13.44 at the rate of $1 per $10,000 income).

COUNTERFACTUAL ANALYSIS:
The section below shows what you would have earned under each principle, assuming you had the same income class assignment (Medium high).

Round X Principle Outcomes for Medium high Class:

- Maximizing Floor Income → Distribution 4 → $99,591 → $9.96
  (Difference: -$3.48)

- Maximizing Average Income → Distribution 1 → $134,448 → $13.44
  (Difference: same)

- Maximizing Average with Floor Constraint:
  Floor constraint $59,754 → Distribution 1 → $134,448 → $13.44 ← YOUR CHOSEN PRINCIPLE
  Floor constraint $64,734 → Distribution 3 → $119,509 → $11.95
    (Difference: -$1.49)
  Floor constraint $71,123 → Distribution 2 → $105,321 → $10.53
    (Difference: -$2.91)

- Maximizing Average with Range Constraint:
  Range constraint $45,000 → Distribution 2 → $110,234 → $11.02
    (Difference: -$2.42)
  Range constraint $52,000 → Distribution 4 → $98,432 → $9.84
    (Difference: -$3.60)
```

### Benefits:
1. ✅ Shows distributions table for context
2. ✅ Shows class probabilities for understanding
3. ✅ Explicit causal narrative connects choice → distribution → class → income → earnings
4. ✅ Clear counterfactual purpose statement
5. ✅ Grouped constraint variations for better comprehension
6. ✅ Explicit difference calculations for easy comparison
7. ✅ Consistent with Phase 2 format for better learning transfer

---

## Implementation Strategy

### Approach: Reuse Phase 2 Logic with Adaptations

Instead of duplicating code, **extract and adapt the Phase 2 helpers** for use in Phase 1:

1. Create shared helper in `CounterfactualsService` or new `ResultsFormattingService`
2. Adapt for Phase 1 context (different headers, no veil reminder)
3. Update Phase 1 to call the shared helper
4. Add minimal Phase 1-specific translation keys

### Alternative: Phase 1-Specific Implementation

If extraction proves complex, implement Phase 1-specific version directly in `Phase1Manager` following Phase 2 pattern.

**Recommendation:** Start with **Phase 1-specific implementation** to avoid over-abstracting, then refactor if duplication becomes problematic.

---

## Implementation Steps

### Step 1: Add Helper Method to Phase1Manager

Add new method `_build_phase1_round_results()` that mirrors Phase 2 structure:

```python
def _build_phase1_round_results(
    self,
    round_num: int,
    parsed_choice: PrincipleChoice,
    assigned_class: IncomeClass,
    earnings: float,
    distribution_set,
    comprehensive_data: Dict[str, Any],
    probabilities
) -> str:
    """
    Build Phase 1 round results using explicit causal narrative format.

    Similar to Phase 2 format but adapted for single-round context.
    """
    # Implementation following new format
    pass
```

**Key sections:**
1. Round header
2. Principle chosen statement
3. Class probabilities
4. Class assignment
5. Distributions table
6. Causal narrative
7. Counterfactual analysis header
8. Counterfactual purpose
9. Outcomes header
10. Grouped outcomes (reuse grouping logic from Phase 2)

### Step 2: Add Shared Outcome Grouping Helper

Extract outcome grouping logic into reusable method:

```python
def _build_grouped_counterfactual_outcomes(
    self,
    comprehensive_data: Dict[str, Any],
    chosen_principle: str,
    chosen_constraint: Optional[int],
    final_earnings: float,
    marker_key: str  # 'assigned_principle' for Phase 1, 'marker_chosen' for Phase 2
) -> str:
    """
    Build grouped counterfactual outcomes with indentation.

    Reusable across Phase 1 and Phase 2.
    """
    # Implementation from Phase 2 _build_counterfactual_outcomes
    pass
```

### Step 3: Update Translation Keys

Add new keys in `results_phase1` namespace (minimal additions):

**English:**
```json
{
  "results_phase1": {
    "round_header": "=== Round {round_num} Payoff Notification ===",
    "principle_chosen": "Principle chosen: {principle_name}{constraint}",
    "probabilities_header": "The probabilities for each income class are:",
    "assignment_statement": "You were assigned to the income class {class_name}",
    "distributions_header": "These were the Round {round_num} Distributions:",
    "causal_narrative": "Your chosen principle was {principle_name}{constraint} which resulted in Distribution {dist_num}. You were assigned to the income class {class_name}, resulting in a yearly income of ${income} (which converts to a payoff of ${earnings} at the rate of $1 per $10,000 income).",
    "counterfactual_header": "COUNTERFACTUAL ANALYSIS:",
    "counterfactual_purpose": "The section below shows what you would have earned under each principle, assuming you had the same income class assignment ({class_name}).",
    "outcomes_header": "Round {round_num} Principle Outcomes for {class_name} Class:"
  }
}
```

**Note:** Reuse existing `results_explicit` keys for:
- `difference_same`
- `difference_positive`
- `difference_negative`
- `floor_constraint_label`
- `range_constraint_label`

### Step 4: Update phase1_manager.py

Replace lines 787-882 in `_handle_application_round()`:

**Before:**
```python
# Build simplified earnings display with basic info followed by outcomes
earnings_display_parts = []
# ... 95 lines of custom formatting
earnings_display = "\n".join(earnings_display_parts)
```

**After:**
```python
# Build Phase 1 round results using explicit format
earnings_display = self._build_phase1_round_results(
    round_num=round_num,
    parsed_choice=parsed_choice,
    assigned_class=assigned_class,
    earnings=earnings,
    distribution_set=distribution_set,
    comprehensive_data=comprehensive_data,
    probabilities=probabilities
)
```

### Step 5: Handle Original Values Mode

Preserve original values mode compatibility:

```python
# In _build_phase1_round_results
if is_original_values:
    situation_map = {1: "A", 2: "B", 3: "C", 4: "D"}
    situation = situation_map.get(round_num)
    # Include situation in distributions header or causal narrative
```

### Step 6: Localization

Add Spanish and Mandarin translations following same pattern as `results_explicit`.

---

## Testing Strategy

### Unit Tests

**Create:** `tests/unit/test_phase1_results_formatting.py`

Test cases:
1. `test_build_phase1_round_results_format()` - Verify structure
2. `test_grouped_outcomes()` - Verify constraint grouping
3. `test_difference_calculations()` - Verify differences
4. `test_marker_placement()` - Verify chosen principle marked
5. `test_causal_narrative()` - Verify narrative correctness
6. `test_original_values_mode()` - Verify compatibility
7. `test_multilingual()` - Verify all 3 languages

### Integration Tests

**Update:** `tests/integration/test_phase1_integration.py`

Test cases:
1. Run full Phase 1 → verify results format
2. Verify agents can parse and use counterfactual info
3. Test all 4 rounds with different principles
4. Verify memory updates include new format

### Manual Validation

1. Run experiment with `config/fast.yaml`
2. Review Phase 1 round results output
3. Verify no parsing errors
4. Check consistency with Phase 2 format
5. Verify agents reference counterfactuals in subsequent rounds

---

## Edge Cases

1. **Original values mode:** Preserve situation/multiplier display
2. **Duplicate constraint values:** Handle multiple distributions with same constraint
3. **Floating point:** Use epsilon for earnings comparison
4. **Missing data:** Graceful degradation if comprehensive_data incomplete
5. **Long principle names:** Ensure proper wrapping
6. **Distribution indexing:** Consistent 1-indexed display

---

## Rollout Plan

### Day 1: Core Implementation
- [ ] Add `_build_phase1_round_results()` method
- [ ] Add `_build_grouped_counterfactual_outcomes()` helper
- [ ] Update `_handle_application_round()` to use new method
- [ ] Preserve original values mode compatibility

### Day 2: Localization
- [ ] Add English translation keys (`results_phase1`)
- [ ] Add Spanish translation keys
- [ ] Add Mandarin translation keys
- [ ] Verify semantic equivalence

### Day 3: Testing
- [ ] Write unit tests for new methods
- [ ] Run unit tests, fix issues
- [ ] Update integration tests
- [ ] Run integration tests, fix issues
- [ ] Update contract test snapshots if needed

### Day 4: Validation
- [ ] Run fast experiment, verify Phase 1 output
- [ ] Run multilingual experiment, verify all languages
- [ ] Test all 4 rounds
- [ ] Verify agents process results correctly
- [ ] Compare Phase 1 and Phase 2 format consistency

### Day 5: Cleanup & Documentation
- [ ] Remove old formatting code
- [ ] Update CLAUDE.md if needed
- [ ] Update docstrings
- [ ] Git commit with clear description

---

## Success Criteria

### Must Have
- ✅ Distributions table shown in Phase 1 results
- ✅ Class probabilities shown
- ✅ Explicit causal narrative
- ✅ Grouped constraint variations
- ✅ Explicit difference calculations
- ✅ All 3 languages supported
- ✅ No test failures
- ✅ Original values mode still works

### Should Have
- ✅ Consistent formatting with Phase 2
- ✅ Agents reference counterfactuals in learning
- ✅ Causal narrative grammatically correct in all languages
- ✅ Clear visual hierarchy with indentation

### Nice to Have
- ✅ Performance same or better
- ✅ Code maintainability improved
- ✅ Shared helpers reduce duplication

---

## Key Differences from Phase 2

While aligning formats, preserve Phase 1-specific elements:

| Element | Phase 1 | Phase 2 |
|---------|---------|---------|
| **Context** | Individual round choice | Group consensus |
| **Header** | "Round X Payoff Notification" | "Final Phase 2 Results" |
| **Choice language** | "Your chosen principle was..." | "The principle your group reached consensus on was..." |
| **Marker** | "← YOUR CHOSEN PRINCIPLE" | "← YOUR CHOSEN PRINCIPLE" or "← YOUR RANDOM ASSIGNMENT" |
| **Veil reminder** | ❌ Not included | ✅ Included |
| **Outcomes header** | "Round X Principle Outcomes..." | "Final Phase 2 Results - Principle Outcomes..." |
| **Purpose statement** | Single sentence | Different for consensus vs no-consensus |

---

## Dependencies

**None** - Self-contained within Phase1Manager and translations.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Contract tests fail | High | Low | Update golden snapshots |
| Translation errors | Medium | Medium | Native speaker review |
| Original values mode breaks | Medium | High | Comprehensive testing of both modes |
| Agent confusion | Low | Medium | A/B test if possible |
| Performance regression | Low | Low | Profile before/after |

---

## Rollback Plan

If critical issues discovered:
1. Git revert commit
2. Re-run experiments with old format
3. Debug issue offline, re-deploy when fixed

Version control handles rollback - no complex fallback needed.

---

## Post-Implementation

### Metrics to Track
1. Agent learning quality (subjective - review examples)
2. References to counterfactuals in later rounds
3. Understanding of principle-outcome relationships
4. Any parsing errors in agent responses

### Follow-up Tasks
- Consider extracting shared formatting logic if duplication becomes issue
- Collect agent reasoning examples for qualitative analysis
- Iterate on format based on observed agent behavior

---

## Timeline Estimate

**Total: 3-4 days**

- Day 1: Implementation (4-6 hours)
- Day 2: Localization (2-3 hours)
- Day 3: Testing (3-4 hours)
- Day 4: Validation (2-3 hours)
- Day 5: Cleanup (1-2 hours)

Can be compressed if working full-time, or spread over 1-2 weeks if working part-time.
