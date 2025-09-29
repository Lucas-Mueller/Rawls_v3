# Phase 2 Results Presentation Improvement Plan

## Executive Summary

Following the successful surgical improvement to Phase 1 results presentation, this plan extends the same approach to Phase 2 final results. The goal is to address the identical user experience problem: **agents' group choice gets buried in a long comprehensive list**, making it difficult to quickly understand what the group decided and what they personally received.

## Current Phase 2 Problem Analysis

### **Identified Issues** (Same as Phase 1)
- ❌ **Group's choice buried in long list**: Hard to find "← YOUR GROUP'S CHOICE" marker
- ❌ **No summary at top**: Agents don't immediately see "what we decided → what I got"
- ❌ **No consensus context**: Missing information about how the group reached this decision
- ❌ **Poor visual hierarchy**: Everything looks the same, hard to scan quickly

### **Current Phase 2 Results Structure**
```
Consensus reached: Maximizing Average with Floor Constraint ($18,000).

Income class probabilities:
- High: 10%
- Medium high: 20%
...

EXPERIMENT DISTRIBUTIONS AND SELECTION MAPPING
| Income Class | Dist. 1 | Dist. 2 | Dist. 3 | Dist. 4 |
|--------------|---------|---------|---------|---------|
...

FINAL PHASE 2 RESULTS - PRINCIPLE OUTCOMES FOR Medium CLASS:
- Maximizing Floor Income → Distribution 4 → $46,650 → $4.66
- Maximizing Average Income → Distribution 1 → $58,840 → $5.88
- Floor constraint ≤ $29,420 → Distribution 1 → $58,840 → $5.88
- Floor constraint ≤ $34,323 → Distribution 3 → $44,250 → $4.42
- Floor constraint ≤ $18,000 → Distribution 1 → $58,840 → $5.88 ← YOUR GROUP'S CHOICE
[... more outcomes ...]
```

## Proposed Surgical Solution

### **Strategy: Prepend Group Choice Summary**
Same approach as Phase 1 - add a clear summary section BEFORE the comprehensive display while preserving all existing functionality.

### **Enhanced Phase 2 Summary Structure**
```
**GROUP CONSENSUS SUMMARY**
Your group chose: Maximizing Average with Floor Constraint ($18,000)
Your outcome: Distribution 1 → Medium class → $58,840 → $5.88
Consensus status: Unanimous agreement reached in Round 3

**HOW YOUR GROUP'S CHOICE WORKED**
Your group's floor constraint of $18,000 required all income classes to earn at least $18,000.
All distributions qualified, so Distribution 1 was selected for having the highest average income.
You were randomly assigned to the Medium class in this distribution.

**COMPLETE COMPARISON - ALL POSSIBLE OUTCOMES FOR MEDIUM CLASS**
[... existing comprehensive display unchanged ...]
```

## Implementation Architecture

### **Key Insight: Reuse Phase 1 Infrastructure**
The Phase 2 comprehensive display already uses the same:
- ✅ `DistributionGenerator.calculate_comprehensive_constraint_outcomes()`
- ✅ Same translation template structure
- ✅ Same outcome data format
- ✅ Same marker system (just uses `group_choice` instead of `assigned_principle`)

### **Target Location: CounterfactualsService**
**File**: `core/services/counterfactuals_service.py`
**Method**: `_build_comprehensive_earnings_display()` (lines 414-472)
**Strategy**: Apply identical surgical prepend approach

## Detailed Implementation Plan

### **Phase 1: Translation Templates** (Est: 20 mins)

Add 4 new Phase 2-specific summary templates to all languages:

**English (`translations/english_prompts.json`)**
```json
"group_consensus_summary_header": "**GROUP CONSENSUS SUMMARY**",
"group_consensus_summary_line": "Your group chose: {principle_name}{constraint_display}",
"group_consensus_outcome_line": "Your outcome: {distribution} → {class_name} → {income} → {earnings}",
"group_consensus_status_line": "Consensus status: {consensus_status}"
```

**Spanish & Mandarin**: Direct translations maintaining exact structure.

### **Phase 2: Surgical Code Addition** (Est: 30 mins)

**File**: `core/services/counterfactuals_service.py`
**Method**: `_build_comprehensive_earnings_display()`
**Lines**: 414-445 (before existing comprehensive display)

Add summary section logic identical to Phase 1:

```python
# SURGICAL ADDITION: Build group consensus summary BEFORE comprehensive display
summary_parts = []

# Find group's choice in outcomes
group_choice_outcome = None
for outcome in comprehensive_data['outcomes']:
    if (group_choice_principle == outcome['principle_key'] and
        outcome.get('constraint_amount') == group_choice_constraint):
        group_choice_outcome = outcome
        break

if group_choice_outcome:
    # Group consensus header
    summary_parts.append(lang_manager.get('comprehensive_earnings.group_consensus_summary_header'))

    # Group choice summary line
    constraint_display = f" (${group_choice_constraint:,})" if group_choice_constraint else ""
    choice_summary = lang_manager.get(
        'comprehensive_earnings.group_consensus_summary_line',
        principle_name=group_choice_outcome['principle_name'],
        constraint_display=constraint_display
    )
    summary_parts.append(choice_summary)

    # Group outcome line
    group_outcome = lang_manager.get(
        'comprehensive_earnings.group_consensus_outcome_line',
        distribution=lang_manager.get('distributions.distribution_label',
                                     number=group_choice_outcome['distribution_index'] + 1),
        class_name=comprehensive_data['class_display_name'],
        income=lang_manager.get('constraint_formatting.currency_format',
                               amount=group_choice_outcome['agent_income']),
        earnings=lang_manager.get('constraint_formatting.currency_format',
                                 amount=group_choice_outcome['agent_earnings'])
    )
    summary_parts.append(group_outcome)

    # Consensus status (needs to be passed from consensus_result)
    consensus_status = "Unanimous agreement reached" if consensus_result.consensus_reached else "No consensus reached"
    status_line = lang_manager.get(
        'comprehensive_earnings.group_consensus_status_line',
        consensus_status=consensus_status
    )
    summary_parts.append(status_line)

    # Add empty line separator
    summary_parts.append("")

# Prepend summary to display_parts (BEFORE existing comprehensive display)
display_parts = summary_parts + display_parts
```

### **Phase 3: Testing & Validation** (Est: 30 mins)

**Test Cases:**
- ✅ Consensus reached with constraint principle
- ✅ Consensus reached with non-constraint principle
- ✅ No consensus reached (fallback gracefully)
- ✅ All 3 languages display correctly
- ✅ Summary appears before comprehensive list
- ✅ No data loss from existing functionality

## Risk Assessment & Mitigation

### **Low Risk Factors**
- ✅ **Same successful approach**: Identical surgical prepend strategy as Phase 1
- ✅ **Existing infrastructure**: Reuses proven comprehensive display system
- ✅ **Minimal changes**: Only adding content, not changing existing logic
- ✅ **Proven translation pattern**: Same template structure across languages

### **Technical Considerations**
- **Consensus result access**: Need to ensure `consensus_result` parameter provides status info
- **Group choice variables**: Use existing `group_choice_principle` and `group_choice_constraint`
- **Error handling**: Graceful fallback if group choice outcome not found

### **Success Criteria**
1. **Summary appears first**: Group choice prominently displayed at top
2. **Information preservation**: All existing comprehensive data intact
3. **No conflicts**: New summary doesn't interfere with existing display
4. **Language consistency**: All 3 languages work identically
5. **Consensus context**: Clear indication of how group reached decision

## Expected Benefits

### **For Agents**
- **Immediate clarity**: See group decision and personal outcome first
- **Better comprehension**: Understand group choice mechanism quickly
- **Consensus awareness**: Clear context about group decision process

### **For Researchers**
- **Maintained analysis**: All existing comprehensive data preserved
- **Enhanced engagement**: Agents better understand group outcomes
- **Clearer results**: Improved agent comprehension of group dynamics

## Comparison: Phase 1 vs Phase 2 Approaches

| Aspect | Phase 1 Solution | Phase 2 Solution |
|--------|------------------|------------------|
| **Target** | Individual choice | Group choice |
| **Context** | "What I chose → What I got" | "What we decided → What I got" |
| **Marker** | "YOUR ASSIGNED PRINCIPLE" | "YOUR GROUP'S CHOICE" |
| **Additional Info** | Agent's certainty level | Consensus status & process |
| **Implementation** | Phase1Manager surgery | CounterfactualsService surgery |
| **Templates** | 4 choice-focused templates | 4 group-focused templates |
| **Risk Level** | ✅ COMPLETED successfully | 🟡 LOW (same proven approach) |

## Implementation Timeline

**Total Estimated Effort**: **1.5 hours** (same efficiency as Phase 1)

### **Phase 1**: Translation Templates (20 mins)
- [ ] Add 4 group consensus templates to English
- [ ] Translate to Spanish maintaining exact structure
- [ ] Translate to Mandarin maintaining exact structure
- [ ] Validate JSON syntax across all files

### **Phase 2**: Surgical Code Addition (30 mins)
- [ ] Add group summary logic to CounterfactualsService
- [ ] Test group choice outcome finding works correctly
- [ ] Verify prepend approach doesn't break existing display

### **Phase 3**: Testing & Validation (40 mins)
- [ ] Test with consensus vs no-consensus scenarios
- [ ] Validate summary appears before comprehensive list
- [ ] Verify all 3 languages display correctly
- [ ] Confirm no data loss from existing functionality

## Key Success Factors

1. **Proven Approach**: Same surgical prepend strategy that succeeded in Phase 1
2. **Minimal Scope**: Only 4 new templates + 30 lines of code
3. **Infrastructure Reuse**: Leverages existing robust comprehensive display system
4. **Risk Mitigation**: Low-risk additive changes with proven patterns

## Next Steps

1. **Review and approve** this focused surgical plan
2. **Implement templates** for group consensus summaries
3. **Add summary logic** to CounterfactualsService using proven prepend approach
4. **Test systematically** with consensus and no-consensus scenarios
5. **Validate** across all languages and edge cases

This surgical approach ensures Phase 2 agents get the same improved user experience as Phase 1 agents: **immediate clarity about group decisions and personal outcomes** while preserving all existing comprehensive analysis capabilities.