# Phase 2 Results Communication Clarity Proposal

## Executive Summary

This document proposes improvements to how final earnings and counterfactual information are communicated to **LLM agents** at the end of Phase 2. The focus is on semantic clarity, explicit relationships, and logical information flow - optimized for language model comprehension rather than human visual processing.

**Status**: User-validated format included. See "Recommended Format" section for the approved approach.

---

## Core Insight: Agents Process Semantics, Not Visuals

**Key Principle**: LLM agents need:
- Explicit cause-effect statements (not implied relationships)
- Progressive information layering (simple → complex)
- Clear purpose statements for each information section
- Unambiguous referents and comparative statements
- Meta-information about WHY they're receiving data
- Concise but complete explanations

**They do NOT need**:
- ASCII art, tables, or visual formatting (though tables for data are fine)
- Emoji or symbolic markers for navigation
- Redundant repetition (state once clearly, not three times)
- Excessive verbosity

---

## Current Format - Critical Analysis

### What Agents Receive Now

```
Phase 2 Earnings: $13.44
Assigned income class: Medium high
Consensus reached: Maximizing Average with Floor Constraint ($12,000).

Income class probabilities:
High: 5%
Medium high: 10%
Medium: 50%
Medium low: 25%
Low: 10%

Experiment Distributions and Selection Mapping

Income Class    Dist. 1    Dist. 2    Dist. 3    Dist. 4
High    $159,346    $139,427    $154,366    $104,570
Medium high    $134,448    $109,550    $119,509    $99,591
Medium    $119,509    $99,591    $104,570    $94,611
Medium low    $64,734    $84,652    $79,673    $79,673
Low    $59,754    $64,734    $69,713    $74,693
Average    $103,326    $95,358    $98,844    $89,881

Final Phase 2 Results - Principle Outcomes for Medium high Class:

Maximizing Floor Income → Distribution 4 → $99,591 → $9.96
Maximizing Average Income → Distribution 1 → $134,448 → $13.44
Maximizing Average with Floor Constraint Floor constraint ≤ $59,754 → Distribution 1 → $134,448 → $13.44
Maximizing Average with Floor Constraint Floor constraint ≤ $64,734 → Distribution 3 → $119,509 → $11.95
Maximizing Average with Floor Constraint Floor constraint ≤ $69,713 → Distribution 3 → $119,509 → $11.95
Maximizing Average with Floor Constraint Floor constraint ≤ $74,693 → Distribution 4 → $99,591 → $9.96
Maximizing Average with Range Constraint Range constraint ≤ $99,592 → Distribution 1 → $134,448 → $13.44
Maximizing Average with Range Constraint Range constraint ≤ $74,693 → Distribution 2 → $109,550 → $10.96
Maximizing Average with Range Constraint Range constraint ≤ $84,653 → Distribution 3 → $119,509 → $11.95
Maximizing Average with Range Constraint Range constraint ≤ $29,877 → Distribution 4 → $99,591 → $9.96
```

### Semantic Problems for LLM Processing

1. **Earnings-first ordering**: Starts with outcome before explaining process
2. **Implicit causality**: Connection between "consensus" and "earnings" requires inference
3. **Ambiguous markers**: "← Group's choice" is a visual indicator, not an explicit statement
4. **Unstated purpose**: WHY counterfactuals are provided isn't explained
5. **Disconnected data**: Probabilities and distributions appear without contextual framing
6. **Referent ambiguity**: "Distribution 1" requires cross-referencing table
7. **Comparative burden**: Agent must calculate differences to understand relative outcomes
8. **Constraint explosion**: All possible constraint variations shown without grouping
9. **Missing interpretation**: No statement about whether outcome was optimal
10. **No task connection**: Doesn't explain this precedes ranking decision

---

## Recommended Format: Concise Explicit Narrative

### User-Validated Structure

Based on user feedback and testing, this format balances clarity with conciseness:

```
Recent Activity:
Final Phase 2 Results:

Principle applied: Your group reached consensus on Maximizing Average with Floor Constraint ($12,000)

The probabilities for each income class are:
High: 5%
Medium high: 10%
Medium: 50%
Medium low: 25%
Low: 10%

You were assigned to the income class Medium high

This was the Experiment Distribution:

Income Class    Dist. 1    Dist. 2    Dist. 3    Dist. 4
High    $159,346    $139,427    $154,366    $104,570
Medium high    $134,448    $109,550    $119,509    $99,591
Medium    $119,509    $99,591    $104,570    $94,611
Medium low    $64,734    $84,652    $79,673    $79,673
Low    $59,754    $64,734    $69,713    $74,693
Average    $103,326    $95,358    $98,844    $89,881

The principle your group reached consensus on was Maximizing Average with Floor Constraint ($12,000) which resulted in Distribution 1. You were assigned to the income class Medium high, resulting in a yearly income of $134,448 and a payoff of $13.44.

These were the results for all principle choices:

Final Phase 2 Results - Principle Outcomes for Medium high Class:

- Maximizing Floor Income → Distribution 4 → $99,591 → $9.96

- Maximizing Average Income → Distribution 1 → $134,448 → $13.44

- Maximizing Average with Floor Constraint:
  Floor constraint $59,754 → Distribution 1 → $134,448 → $13.44 ← YOUR CHOSEN PRINCIPLE
  Floor constraint $64,734 → Distribution 3 → $119,509 → $11.95
  Floor constraint $69,713 → Distribution 3 → $119,509 → $11.95
  Floor constraint $74,693 → Distribution 4 → $99,591 → $9.96

- Maximizing Average with Range Constraint:
  Range constraint $99,592 → Distribution 1 → $134,448 → $13.44
  Range constraint $74,693 → Distribution 2 → $109,550 → $10.96
  Range constraint $84,653 → Distribution 3 → $119,509 → $11.95
  Range constraint $29,877 → Distribution 4 → $99,591 → $9.96

Return: Your complete updated memory (not incremental changes or prefixes like 'Memory update:')
```

### Key Improvements in This Format

1. **Process-first ordering**: Starts with WHAT happened (principle choice) before showing outcome
2. **Explicit framing**: "The probabilities for each income class are" (not just a header)
3. **Clear assignment statement**: "You were assigned to the income class Medium high"
4. **Distribution table introduction**: "This was the Experiment Distribution"
5. **Single-sentence causal narrative**: Complete cause-effect chain in one clear sentence
6. **Grouped constraint variations**: Indentation shows parent-child relationship
7. **Unambiguous marker**: "← YOUR CHOSEN PRINCIPLE" instead of visual arrow alone
8. **Logical flow**: Decision → Context → Assignment → Distribution → Outcome → Counterfactuals

---

## Detailed Feedback on User's Proposed Format

### What Works Exceptionally Well ✅

**1. Causal Narrative Sentence**
```
"The principle your group reached consensus on was Maximizing Average with Floor
Constraint ($12,000) which resulted in Distribution 1. You were assigned to the
income class Medium high, resulting in a yearly income of $134,448 and a payoff
of $13.44."
```
**Why it works**:
- Complete causal chain in one digestible sentence
- Clear subject-verb-object structure
- Explicit "resulted in" shows causality
- All critical information present without redundancy

**2. Constraint Grouping with Indentation**
```
- Maximizing Average with Floor Constraint:
  Floor constraint $59,754 → Distribution 1 → $134,448 → $13.44 ← YOUR CHOSEN PRINCIPLE
  Floor constraint $64,734 → Distribution 3 → $119,509 → $11.95
  Floor constraint $69,713 → Distribution 3 → $119,509 → $11.95
  Floor constraint $74,693 → Distribution 4 → $99,591 → $9.96
```
**Why it works**:
- Shows relationship between principle and variations
- Reduces cognitive load (agent sees these are related)
- Easier to scan for specific constraint amounts
- Clear hierarchical structure

**3. Progressive Information Flow**
- Decision (what was chosen)
- Context (probabilities)
- Assignment (your class)
- Distributions (available options)
- Outcome (what you received)
- Counterfactuals (alternatives)

**Why it works**: Natural narrative progression from general to specific

**4. Explicit Assignment Statement**
```
"You were assigned to the income class Medium high"
```
**Why it works**:
- Clear subject ("You")
- Active voice
- Unambiguous action ("were assigned")
- No inference required

### Suggested Enhancements 🔧

**1. Add Explicit Comparison to Counterfactuals**

Current:
```
- Maximizing Floor Income → Distribution 4 → $99,591 → $9.96
```

Suggested enhancement:
```
- Maximizing Floor Income → Distribution 4 → $99,591 → $9.96
  (Difference: -$3.48 compared to your actual outcome)
```

**Rationale**: Makes comparative analysis explicit instead of requiring mental calculation.

**2. Add Purpose Statement for Counterfactuals**

Suggested addition before "These were the results for all principle choices:":
```
The section below shows what you would have earned under each principle, assuming
you had the same income class assignment (Medium high). This helps you evaluate
how different principles would have affected your specific outcome.
```

**Rationale**: Explains WHY counterfactuals matter and WHAT is held constant.

**3. Add Veil of Ignorance Reminder**

Suggested addition at the end:
```
Important: Your income class was assigned randomly AFTER the group chose the
principle. When evaluating which principle is most just, consider what you would
have preferred BEFORE knowing your class assignment.
```

**Rationale**: Connects to experimental design and philosophical concept.

**4. Add Interpretation Summary**

Suggested addition after counterfactuals:
```
Summary for your income class (Medium high):
- Best outcome: Maximizing Average Income ($13.44) or Max Avg with Floor Constraint
  $59,754 ($13.44) [TIE]
- Your actual outcome: $13.44 (optimal for your class)
- Worst outcome: Maximizing Floor Income ($9.96)
```

**Rationale**: Provides explicit interpretation instead of requiring agent to calculate rankings.

**5. Minor Wording Improvements**

Current: "This was the Experiment Distribution"
Suggested: "These were the Experiment Distributions available:"

Current: "resulting in a yearly income of $134,448"
Suggested: "resulting in a yearly income of $134,448 (which converts to a payoff of $13.44)"

**Rationale**:
- Plural "distributions" (there are 4)
- Explicit conversion explanation reinforces the income→earnings relationship

---

## Enhanced Recommended Format

Incorporating user's format + suggested enhancements:

```
Recent Activity:
Final Phase 2 Results:

Principle applied: Your group reached consensus on Maximizing Average with Floor Constraint ($12,000)

The probabilities for each income class are:
High: 5%
Medium high: 10%
Medium: 50%
Medium low: 25%
Low: 10%

You were assigned to the income class Medium high

These were the Experiment Distributions:

Income Class    Dist. 1    Dist. 2    Dist. 3    Dist. 4
High    $159,346    $139,427    $154,366    $104,570
Medium high    $134,448    $109,550    $119,509    $99,591
Medium    $119,509    $99,591    $104,570    $94,611
Medium low    $64,734    $84,652    $79,673    $79,673
Low    $59,754    $64,734    $69,713    $74,693
Average    $103,326    $95,358    $98,844    $89,881

The principle your group reached consensus on was Maximizing Average with Floor Constraint ($12,000) which resulted in Distribution 1. You were assigned to the income class Medium high, resulting in a yearly income of $134,448 (which converts to a payoff of $13.44 at the rate of $1 per $10,000 income).

COUNTERFACTUAL ANALYSIS:
The section below shows what you would have earned under each principle, assuming you had the same income class assignment (Medium high). 

Final Phase 2 Results - Principle Outcomes for Medium high Class:

- Maximizing Floor Income → Distribution 4 → $99,591 → $9.96
  (Difference: -$3.48 compared to your actual outcome)

- Maximizing Average Income → Distribution 1 → $134,448 → $13.44
  (Difference: same as your actual outcome)

- Maximizing Average with Floor Constraint:
  Floor constraint $59,754 → Distribution 1 → $134,448 → $13.44 ← YOUR CHOSEN PRINCIPLE
  Floor constraint $64,734 → Distribution 3 → $119,509 → $11.95 (Difference: -$1.49)
  Floor constraint $69,713 → Distribution 3 → $119,509 → $11.95 (Difference: -$1.49)
  Floor constraint $74,693 → Distribution 4 → $99,591 → $9.96 (Difference: -$3.48)

- Maximizing Average with Range Constraint:
  Range constraint $99,592 → Distribution 1 → $134,448 → $13.44 (Difference: same)
  Range constraint $74,693 → Distribution 2 → $109,550 → $10.96 (Difference: -$2.48)
  Range constraint $84,653 → Distribution 3 → $119,509 → $11.95 (Difference: -$1.49)
  Range constraint $29,877 → Distribution 4 → $99,591 → $9.96 (Difference: -$3.48)


IMPORTANT FOR RANKING:
Your income class was assigned randomly AFTER the group chose the principle. When evaluating which principle is most just, consider what you would have preferred BEFORE knowing your class assignment (from behind the "veil of ignorance").

Return: Your complete updated memory (not incremental changes or prefixes like 'Memory update:')
```

---

## Comparison: User Format vs. Original Verbose Proposal

### User Format (Recommended)
**Length**: ~30 lines of content
**Verbosity**: Concise, each fact stated once clearly
**Causality**: Single comprehensive sentence
**Counterfactuals**: Grouped by principle with indentation
**Best for**: Standard experiments, balanced clarity/length

### Original Verbose Proposal (Alternative)
**Length**: ~200 lines of content
**Verbosity**: High, critical facts stated 3 times
**Causality**: 5-step numbered breakdown with explanations
**Counterfactuals**: Full paragraph per scenario with explicit comparisons
**Best for**: Experiments where comprehension is critical, agents struggling with understanding

### Verdict
**The user's format is superior for production use** because:
1. Achieves clarity without excessive verbosity
2. Respects agent token limits and processing capacity
3. Maintains all critical information
4. Uses structural grouping (indentation) effectively
5. Balances explicitness with conciseness

The verbose format should be kept as an optional "maximum clarity mode" for specific use cases.

---

## Implementation Strategy

### Template Structure

```python
def build_phase2_results_explicit(
    consensus_principle: PrincipleChoice,
    probabilities: Dict[str, float],
    assigned_class: IncomeClass,
    distribution_set: DistributionSet,
    selected_distribution: Distribution,
    income: float,
    earnings: float,
    counterfactuals: Dict[str, List[Tuple[str, Distribution, float, float]]]
) -> str:
    """
    Build Phase 2 results using explicit causal narrative format.

    Args:
        consensus_principle: The principle chosen by group
        probabilities: Income class probabilities
        assigned_class: Agent's assigned income class
        distribution_set: All available distributions
        selected_distribution: Distribution selected by consensus principle
        income: Agent's income amount
        earnings: Agent's earnings (income / 10000)
        counterfactuals: Dict mapping principle names to list of
                        (constraint, distribution, income, earnings) tuples

    Returns:
        Formatted results string
    """

    # Section 1: Principle applied
    principle_name = get_localized_principle_name(consensus_principle.principle)
    constraint_text = f" (${consensus_principle.constraint_amount:,})" if consensus_principle.constraint_amount else ""

    result = f"Final Phase 2 Results:\n\n"
    result += f"Principle applied: Your group reached consensus on {principle_name}{constraint_text}\n\n"

    # Section 2: Probabilities with context
    result += "The probabilities for each income class are:\n"
    for class_name, prob in probabilities.items():
        result += f"{class_name}: {prob*100:.0f}%\n"
    result += "\n"

    # Section 3: Assignment statement
    assigned_class_name = get_localized_class_name(assigned_class)
    result += f"You were assigned to the income class {assigned_class_name}\n\n"

    # Section 4: Distribution table with introduction
    result += "These were the Experiment Distributions available:\n\n"
    result += build_distributions_table(distribution_set)
    result += "\n"

    # Section 5: Causal narrative sentence
    distribution_num = distribution_set.distributions.index(selected_distribution) + 1
    result += f"The principle your group reached consensus on was {principle_name}{constraint_text} which resulted in Distribution {distribution_num}. "
    result += f"You were assigned to the income class {assigned_class_name}, resulting in a yearly income of ${income:,.0f} "
    result += f"(which converts to a payoff of ${earnings:.2f} at the rate of $1 per $10,000 income).\n\n"

    # Section 6: Counterfactual purpose statement
    result += "COUNTERFACTUAL ANALYSIS:\n"
    result += f"The section below shows what you would have earned under each principle, assuming you had the same income class assignment ({assigned_class_name}). "
    result += "This helps you evaluate how different principles would have affected your specific outcome.\n\n"

    # Section 7: Counterfactual outcomes
    result += f"Final Phase 2 Results - Principle Outcomes for {assigned_class_name} Class:\n\n"

    for principle_key, variations in counterfactuals.items():
        principle_display = get_localized_principle_name(principle_key)

        if len(variations) == 1:
            # Simple principle (no constraints)
            constraint, dist, inc, earn = variations[0]
            dist_num = distribution_set.distributions.index(dist) + 1
            diff = earn - earnings
            diff_text = format_difference(diff, earnings)

            marker = " ← YOUR CHOSEN PRINCIPLE" if is_chosen(principle_key, consensus_principle) else ""
            result += f"- {principle_display} → Distribution {dist_num} → ${inc:,.0f} → ${earn:.2f}{marker}\n"
            result += f"  ({diff_text})\n\n"
        else:
            # Constraint principle with variations
            result += f"- {principle_display}:\n"
            for constraint, dist, inc, earn in variations:
                dist_num = distribution_set.distributions.index(dist) + 1
                diff = earn - earnings
                diff_text = format_difference(diff, earnings)

                marker = " ← YOUR CHOSEN PRINCIPLE" if is_chosen_with_constraint(principle_key, constraint, consensus_principle) else ""
                constraint_label = format_constraint_label(principle_key, constraint)
                result += f"  {constraint_label} → Distribution {dist_num} → ${inc:,.0f} → ${earn:.2f}{marker}\n"
                if diff != 0:
                    result += f"    ({diff_text})\n"
            result += "\n"

    # Section 8: Interpretation summary
    best_earnings = max(earn for variations in counterfactuals.values() for _, _, _, earn in variations)
    worst_earnings = min(earn for variations in counterfactuals.values() for _, _, _, earn in variations)

    best_principles = [
        get_localized_principle_name(p)
        for p, variations in counterfactuals.items()
        for constraint, dist, inc, earn in variations
        if earn == best_earnings
    ]

    result += f"SUMMARY FOR YOUR INCOME CLASS ({assigned_class_name}):\n"
    result += f"Best outcome(s): {', '.join(best_principles)} (${best_earnings:.2f})\n"
    result += f"Your actual outcome: ${earnings:.2f} "
    if earnings == best_earnings:
        result += "(optimal for your class)\n"
    else:
        result += f"(${best_earnings - earnings:.2f} below optimal)\n"
    result += f"Worst outcome: ${worst_earnings:.2f}\n\n"

    # Section 9: Veil of ignorance reminder
    result += "IMPORTANT FOR RANKING:\n"
    result += "Your income class was assigned randomly AFTER the group chose the principle. "
    result += "When evaluating which principle is most just, consider what you would have preferred "
    result += "BEFORE knowing your class assignment (from behind the \"veil of ignorance\").\n\n"

    return result


def format_difference(diff: float, actual: float) -> str:
    """Format difference from actual outcome."""
    if diff == 0:
        return "Difference: same as your actual outcome"
    elif diff > 0:
        return f"Difference: +${diff:.2f} compared to your actual outcome"
    else:
        return f"Difference: ${diff:.2f} compared to your actual outcome"
```

### Localization Considerations

Add to translation files:

```json
{
  "results": {
    "principle_applied": "Principle applied: Your group reached consensus on {principle_name}{constraint}",
    "probabilities_header": "The probabilities for each income class are:",
    "assignment_statement": "You were assigned to the income class {class_name}",
    "distributions_intro": "These were the Experiment Distributions available:",
    "causal_narrative": "The principle your group reached consensus on was {principle_name}{constraint} which resulted in Distribution {dist_num}. You were assigned to the income class {class_name}, resulting in a yearly income of ${income} (which converts to a payoff of ${earnings} at the rate of $1 per $10,000 income).",
    "counterfactual_header": "COUNTERFACTUAL ANALYSIS:",
    "counterfactual_purpose": "The section below shows what you would have earned under each principle, assuming you had the same income class assignment ({class_name}). This helps you evaluate how different principles would have affected your specific outcome.",
    "outcomes_header": "Final Phase 2 Results - Principle Outcomes for {class_name} Class:",
    "summary_header": "SUMMARY FOR YOUR INCOME CLASS ({class_name}):",
    "summary_best": "Best outcome(s): {principles} (${earnings})",
    "summary_actual_optimal": "Your actual outcome: ${earnings} (optimal for your class)",
    "summary_actual_suboptimal": "Your actual outcome: ${earnings} (${diff} below optimal)",
    "summary_worst": "Worst outcome: ${earnings}",
    "veil_reminder_header": "IMPORTANT FOR RANKING:",
    "veil_reminder_text": "Your income class was assigned randomly AFTER the group chose the principle. When evaluating which principle is most just, consider what you would have preferred BEFORE knowing your class assignment (from behind the \"veil of ignorance\").",
    "difference_same": "Difference: same as your actual outcome",
    "difference_positive": "Difference: +${diff} compared to your actual outcome",
    "difference_negative": "Difference: ${diff} compared to your actual outcome",
    "chosen_marker": " ← YOUR CHOSEN PRINCIPLE"
  }
}
```

---

## Testing and Validation

### Comprehension Testing

**Test 1: Causal Understanding**
- Prompt: "How were your Phase 2 earnings determined?"
- Expected: Agent references the causal narrative sentence or summarizes the process
- Success criteria: Mentions principle → distribution → assignment → income → earnings chain

**Test 2: Counterfactual Comprehension**
- Prompt: "Would you have earned more under Maximizing Floor Income?"
- Expected: Agent correctly identifies yes/no and the specific amount
- Success criteria: Accurate comparison with reference to counterfactual section

**Test 3: Veil of Ignorance**
- Prompt: "When was your income class assigned relative to the principle choice?"
- Expected: "After the group chose the principle" or similar
- Success criteria: Demonstrates understanding of random assignment timing

### A/B Testing Protocol

**Control Group**: Current format (earnings-first, arrow markers)
**Treatment Group**: Enhanced user format (process-first, explicit narrative)

**Sample Size**: 30 experiments per group (5 agents × 30 = 150 rankings per group)

**Metrics**:
1. **Counterfactual reference rate**: % of agents citing specific counterfactual data in rankings
2. **Veil reasoning**: % of agents distinguishing ex-ante vs. ex-post evaluation
3. **Accuracy**: % of agents correctly stating their earnings when queried
4. **Interpretation**: % of agents correctly identifying whether outcome was optimal for their class

**Analysis**:
- Compare mean scores across groups using t-tests
- Analyze qualitative reasoning quality in ranking justifications
- Identify any confusion points or misinterpretations

---

## Migration Path

### Phase 1: Implementation (Week 1)
- Create `build_phase2_results_explicit()` in `CounterfactualsService`
- Add configuration flag: `results_format: "legacy" | "explicit_narrative"`
- Implement helper functions (difference formatting, constraint labeling)
- Unit tests for template generation

### Phase 2: Localization (Week 1-2)
- Translate all new text elements for English, Spanish, Mandarin
- Verify semantic equivalence across languages
- Test with multilingual configurations
- Validate constraint grouping works in all languages

### Phase 3: Validation (Week 2-3)
- Run A/B experiments (30 per group)
- Analyze comprehension and ranking quality metrics
- Collect agent reasoning examples
- Identify any confusion points

### Phase 4: Refinement (Week 3)
- Address identified issues
- Optimize difference calculations and formatting
- Fine-tune summary section based on results

### Phase 5: Deployment (Week 4)
- Make explicit narrative format the default
- Update test fixtures and golden snapshots
- Document in CLAUDE.md
- Archive legacy format with deprecation notice

---

## Success Criteria

### Must Achieve (Go/No-Go)

1. **No information loss**: All data from current format preserved
2. **No performance regression**: Generation time ≤ current
3. **Localization quality**: Semantic equivalence across languages verified
4. **Backward compatibility**: Legacy format still available via config flag

### Target Improvements

1. **Counterfactual reference rate**: ≥75% (vs. current baseline)
2. **Veil of ignorance reasoning**: ≥40% (vs. current baseline)
3. **Optimal outcome identification**: ≥90% accuracy when queried
4. **Causal chain comprehension**: ≥80% can explain how earnings were determined

### Qualitative Indicators

1. Agents explain counterfactuals relevance (not just citing them)
2. Agents distinguish "best for me" vs. "most just overall"
3. Agents reference specific constraint amounts in reasoning
4. Agents demonstrate understanding of random assignment

---

## Alternative Format: Maximum Clarity Mode

For experiments requiring absolute comprehension (e.g., testing agents with known reasoning limitations), an ultra-verbose variant is available. This format:

- States critical facts multiple times
- Breaks causal chain into 5 numbered steps
- Provides full paragraph explanation for each counterfactual
- Includes explicit "Because X, therefore Y" statements throughout

See appendix in original proposal document for full specification.

**When to use**:
- Pilot experiments with new agent models
- Experiments where ranking quality is more important than brevity
- Troubleshooting comprehension issues
- Research specifically studying information processing

---

## Conclusion

The **Explicit Causal Narrative** format (user-validated version) achieves optimal balance between clarity and conciseness for Phase 2 results communication.

**Core Innovation**:
- Process-first ordering (decision before outcome)
- Single-sentence causal narrative
- Grouped counterfactual variations
- Explicit interpretation summary
- Veil of ignorance framing

**Key Advantage**: Agents receive complete information in a natural narrative flow that supports both immediate comprehension and deep reflection for ranking decisions.

**Implementation Priority**: High - results clarity directly impacts validity of final rankings, which are the primary experimental outcome.

**Recommended Action**: Implement enhanced user format as default, validate with A/B testing, deploy if metrics confirm improvement.
