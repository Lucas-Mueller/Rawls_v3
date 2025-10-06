# Implementation Plan: Phase 2 Results Format Improvement

## Overview

Implement the improved Phase 2 results format that uses explicit causal narrative and grouped constraint variations for better agent comprehension.

**Target files**:
- `core/services/counterfactuals_service.py` - Main implementation
- `translations/english_prompts.json` - English text
- `translations/spanish_prompts.json` - Spanish text
- `translations/mandarin_prompts.json` - Mandarin text
- Tests to update as needed

---

## Templates

### Template 1: Consensus Reached

```
Final Phase 2 Results:

Principle applied: Your group reached consensus on {principle_name}{constraint}

The probabilities for each income class are:
{class_probabilities}

You were assigned to the income class {assigned_class}

These were the Experiment Distributions:

{distributions_table}

The principle your group reached consensus on was {principle_name}{constraint} which resulted in Distribution {dist_num}. You were assigned to the income class {assigned_class}, resulting in a yearly income of ${income} (which converts to a payoff of ${earnings} at the rate of $1 per $10,000 income).

COUNTERFACTUAL ANALYSIS:
The section below shows what you would have earned under each principle, assuming you had the same income class assignment ({assigned_class}).

Final Phase 2 Results - Principle Outcomes for {assigned_class} Class:

{counterfactual_outcomes_with_marker}

IMPORTANT FOR RANKING:
Your income class was assigned randomly AFTER the group chose the principle. When evaluating which principle is most just, consider what you would have preferred BEFORE knowing your class assignment (from behind the "veil of ignorance").
```

### Template 2: No Consensus Reached

```
Final Phase 2 Results:

Principle applied: Your group did not reach consensus on a justice principle

The probabilities for each income class are:
{class_probabilities}

You were assigned to the income class {assigned_class}

These were the Experiment Distributions:

{distributions_table}

Because the group did not reach consensus, you were randomly assigned to Distribution {dist_num}. You were assigned to the income class {assigned_class}, resulting in a yearly income of ${income} (which converts to a payoff of ${earnings} at the rate of $1 per $10,000 income).

COUNTERFACTUAL ANALYSIS:
The section below shows what you would have earned if the group HAD reached consensus on each principle, assuming you had the same income class assignment ({assigned_class}).

Final Phase 2 Results - Principle Outcomes for {assigned_class} Class:

{counterfactual_outcomes_with_marker}

IMPORTANT FOR RANKING:
Your income class was assigned randomly, and since no consensus was reached, your distribution was also randomly assigned. When evaluating which principle is most just, consider which principle you would have preferred the group to choose from behind the "veil of ignorance" (before knowing your position).
```

**Key Differences in No-Consensus Template**:
1. "did not reach consensus" instead of consensus statement
2. "you were randomly assigned to Distribution X" instead of "principle resulted in"
3. Counterfactual framing: "if the group HAD reached consensus"
4. Marker shows "← YOUR RANDOM ASSIGNMENT" instead of "← YOUR CHOSEN PRINCIPLE"
5. Veil reminder acknowledges both class AND distribution were random

---

## Implementation Steps

### Step 1: Update CounterfactualsService

**File**: `core/services/counterfactuals_service.py`

**Changes needed**:

1. Modify `build_detailed_results()` method to use new format
2. Add helper method `_build_consensus_results()`
3. Add helper method `_build_no_consensus_results()`
4. Add helper method `_build_counterfactual_outcomes()`
5. Add helper method `_format_difference()`

**Signature changes**: None - keep existing interface

### Step 2: Update Translation Files

**Files**: `translations/{english,spanish,mandarin}_prompts.json`

**New keys to add** (English examples):

```json
{
  "results_explicit": {
    "principle_applied_consensus": "Principle applied: Your group reached consensus on {principle_name}{constraint}",
    "principle_applied_no_consensus": "Principle applied: Your group did not reach consensus on a justice principle",
    "probabilities_header": "The probabilities for each income class are:",
    "assignment_statement": "You were assigned to the income class {class_name}",
    "distributions_header": "These were the Experiment Distributions:",
    "causal_narrative_consensus": "The principle your group reached consensus on was {principle_name}{constraint} which resulted in Distribution {dist_num}. You were assigned to the income class {class_name}, resulting in a yearly income of ${income} (which converts to a payoff of ${earnings} at the rate of $1 per $10,000 income).",
    "causal_narrative_no_consensus": "Because the group did not reach consensus, you were randomly assigned to Distribution {dist_num}. You were assigned to the income class {class_name}, resulting in a yearly income of ${income} (which converts to a payoff of ${earnings} at the rate of $1 per $10,000 income).",
    "counterfactual_header": "COUNTERFACTUAL ANALYSIS:",
    "counterfactual_purpose_consensus": "The section below shows what you would have earned under each principle, assuming you had the same income class assignment ({class_name}).",
    "counterfactual_purpose_no_consensus": "The section below shows what you would have earned if the group HAD reached consensus on each principle, assuming you had the same income class assignment ({class_name}).",
    "outcomes_header": "Final Phase 2 Results - Principle Outcomes for {class_name} Class:",
    "veil_reminder_header": "IMPORTANT FOR RANKING:",
    "veil_reminder_consensus": "Your income class was assigned randomly AFTER the group chose the principle. When evaluating which principle is most just, consider what you would have preferred BEFORE knowing your class assignment (from behind the \"veil of ignorance\").",
    "veil_reminder_no_consensus": "Your income class was assigned randomly, and since no consensus was reached, your distribution was also randomly assigned. When evaluating which principle is most just, consider which principle you would have preferred the group to choose from behind the \"veil of ignorance\" (before knowing your position).",
    "difference_same": "Difference: same",
    "difference_positive": "Difference: +${diff}",
    "difference_negative": "Difference: ${diff}",
    "marker_chosen": " ← YOUR CHOSEN PRINCIPLE",
    "marker_random": " ← YOUR RANDOM ASSIGNMENT",
    "floor_constraint_label": "Floor constraint ${amount}",
    "range_constraint_label": "Range constraint ${amount}"
  }
}
```

### Step 3: Update Test Fixtures

**Files to check**:
- `tests/contracts/` - Golden snapshots may need updating
- `tests/component/test_phase2_*.py` - Component tests that check results format
- `tests/integration/test_*.py` - Integration tests with result validation

**Strategy**: Run tests, identify failures, update expected outputs to match new format.

### Step 4: Configuration Flag (Optional)

**File**: `config/phase2_settings.py`

Add optional flag:
```python
use_explicit_results_format: bool = True  # New format by default
```

This allows easy rollback if issues are discovered, but default to new format.

---

## Detailed Code Changes

### CounterfactualsService Changes

```python
async def build_detailed_results(
    self,
    participant_name: str,
    final_earnings: float,
    assigned_class: str,
    alternative_earnings: Dict[str, float],
    consensus_result: GroupDiscussionResult,
    distribution_set,
    lang_manager: LanguageProvider
) -> str:
    """Build Phase 2 results using explicit causal narrative format."""

    if consensus_result.consensus_reached and consensus_result.agreed_principle:
        return self._build_consensus_results(
            participant_name,
            final_earnings,
            assigned_class,
            alternative_earnings,
            consensus_result,
            distribution_set,
            lang_manager
        )
    else:
        return self._build_no_consensus_results(
            participant_name,
            final_earnings,
            assigned_class,
            alternative_earnings,
            consensus_result,
            distribution_set,
            lang_manager
        )

def _build_consensus_results(self, ...) -> str:
    """Build results for consensus scenario."""
    # Implementation following Template 1
    pass

def _build_no_consensus_results(self, ...) -> str:
    """Build results for no-consensus scenario."""
    # Implementation following Template 2
    pass

def _build_counterfactual_outcomes(
    self,
    assigned_class_enum: IncomeClass,
    distribution_set,
    alternative_earnings: Dict[str, float],
    consensus_result: GroupDiscussionResult,
    participant_name: str,
    final_earnings: float,
    lang_manager: LanguageProvider
) -> str:
    """
    Build counterfactual outcomes section with grouped constraints.

    Returns formatted string with:
    - Simple principles (1 line each with difference)
    - Constraint principles (parent + indented children with differences)
    - Appropriate marker (chosen principle or random assignment)
    """
    pass

def _format_difference(self, diff: float, lang_manager: LanguageProvider) -> str:
    """Format earnings difference."""
    if abs(diff) < 0.01:  # Account for floating point
        return lang_manager.get("results_explicit.difference_same")
    elif diff > 0:
        return lang_manager.get("results_explicit.difference_positive", diff=f"{diff:.2f}")
    else:
        return lang_manager.get("results_explicit.difference_negative", diff=f"{diff:.2f}")
```

---

## Testing Strategy

### Unit Tests

**File**: Create `tests/unit/test_counterfactuals_service_explicit_format.py`

Test cases:
1. `test_build_consensus_results_format()` - Verify template structure
2. `test_build_no_consensus_results_format()` - Verify no-consensus variant
3. `test_counterfactual_grouping()` - Verify constraint indentation
4. `test_difference_formatting()` - Verify difference calculations
5. `test_marker_placement_consensus()` - Verify chosen principle marker
6. `test_marker_placement_no_consensus()` - Verify random assignment marker
7. `test_multilingual_support()` - Verify all 3 languages

### Integration Tests

**File**: Update `tests/integration/test_phase2_integration.py`

Test cases:
1. Run full Phase 2 with consensus → verify results format
2. Run full Phase 2 without consensus → verify no-consensus format
3. Verify agent can parse and reference results in ranking task

### Manual Validation

1. Run experiment with `config/fast.yaml`
2. Check output results for proper formatting
3. Verify no parsing errors
4. Check that agents reference counterfactuals in rankings

---

## Rollout Plan

### Day 1: Core Implementation
- [ ] Implement `_build_consensus_results()`
- [ ] Implement `_build_no_consensus_results()`
- [ ] Implement `_build_counterfactual_outcomes()`
- [ ] Implement `_format_difference()`
- [ ] Update `build_detailed_results()` to route to new methods

### Day 2: Localization
- [ ] Add English translation keys
- [ ] Add Spanish translation keys
- [ ] Add Mandarin translation keys
- [ ] Verify semantic equivalence across languages

### Day 3: Testing
- [ ] Write unit tests
- [ ] Run unit tests, fix any issues
- [ ] Update integration tests
- [ ] Run integration tests, fix any issues
- [ ] Update contract test snapshots if needed

### Day 4: Validation
- [ ] Run fast experiment, verify output
- [ ] Run multilingual experiment, verify all languages
- [ ] Test both consensus and no-consensus paths
- [ ] Verify agents can process results correctly

### Day 5: Cleanup & Documentation
- [ ] Remove any dead code from old format
- [ ] Update CLAUDE.md with new format
- [ ] Update docstrings
- [ ] Git commit with clear description

---

## Edge Cases to Handle

1. **Constraint amount formatting**: Different locales format currency differently
2. **Tied outcomes**: Multiple principles yielding same earnings
3. **Very long principle names**: Ensure they wrap properly
4. **Missing translation keys**: Graceful fallback to English
5. **Floating point comparison**: Use epsilon for earnings comparison
6. **Distribution indexing**: Ensure 1-indexed for display (not 0-indexed)

---

## Success Criteria

### Must Have
- ✅ No information loss compared to current format
- ✅ Both consensus and no-consensus cases work
- ✅ All 3 languages supported (English, Spanish, Mandarin)
- ✅ No test failures
- ✅ Constraint grouping with proper indentation
- ✅ Difference calculations accurate

### Should Have
- ✅ Agents reference counterfactuals in rankings (validate manually)
- ✅ Causal narrative is grammatically correct in all languages
- ✅ Markers clearly distinguish chosen vs. random assignment

### Nice to Have
- ✅ Performance same or better than current implementation
- ✅ Code is more maintainable than current format

---

## Dependencies

**None** - This change is self-contained within CounterfactualsService and translations.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Contract tests fail | High | Low | Update golden snapshots |
| Translation errors | Medium | Medium | Native speaker review |
| Agent confusion | Low | High | A/B test before full rollout |
| Performance regression | Low | Low | Profile before/after |
| Edge case bugs | Medium | Medium | Comprehensive unit tests |

---

## Rollback Plan

If critical issues discovered:
1. Set `use_explicit_results_format: false` in config (if flag added)
2. Git revert commit
3. Re-run experiments with old format
4. Debug issue offline, re-deploy when fixed

Since we have version control, no complex fallback needed.

---

## Post-Implementation

### Metrics to Track
1. Agent ranking quality (subjective - review examples)
2. References to counterfactuals in ranking justifications
3. Understanding of veil of ignorance concept
4. Any parsing errors in agent responses

### Follow-up Tasks
- Consider A/B testing if resources allow (30 experiments per group)
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
