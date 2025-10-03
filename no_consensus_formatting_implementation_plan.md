# No-Consensus Formatting Alignment Implementation Plan

## Objective
Align no-consensus prompt formatting to match consensus prompt structure line-for-line, treating consensus format as canonical template.

## Current State Analysis

### Consensus Format (Canonical)
```
PHASE 2 FINAL RESULTS: $X.XX
Assigned income class: {Class}
Consensus reached: {Principle}.

Income class probabilities:
...
```

### No-Consensus Format (Current)
```
PHASE 2 FINAL RESULTS: $X.XX
Assigned income class: {Class}

**NO CONSENSUS REACHED**
Your group could not agree...
Your random assignment: ...

Income class probabilities:
...
```

### Key Differences Identified
1. **Status line format**: Consensus uses prose sentence, no-consensus uses bold header
2. **Spacing**: No-consensus has double blank line before status block
3. **Punctuation**: Random assignment sentence lacks terminal period
4. **Marker**: No group choice marker in outcomes list for no-consensus

## Implementation Changes

### 1. Translation Keys Update (`translations/english_prompts.json`)

**Location**: Lines 397-399 (comprehensive_earnings section)

**Change 1: Replace bold header with sentence format**
```json
// OLD (line 397):
"no_consensus_summary_header": "**NO CONSENSUS REACHED**",

// NEW:
"no_consensus_status": "No consensus reached: Random assignment applied",
```

**Change 2: Add terminal period to random assignment**
```json
// OLD (line 399):
"no_consensus_outcome_line": "Your random assignment: {class_name} class and Distribution {distribution_num} → ${earnings:.2f} earnings",

// NEW:
"no_consensus_outcome_line": "Your random assignment: {class_name} class and Distribution {distribution_num} → ${earnings:.2f} earnings.",
```

**Change 3: Add random assignment marker**
```json
// Location: Line 395 (within markers section)
// ADD after group_choice:
"random_assignment": " ← RANDOM ASSIGNMENT"
```

### 2. Code Changes (`core/services/counterfactuals_service.py`)

**Location 1: Header assembly (lines 374-393)**

**Add no-consensus status line parallel to consensus**
```python
# After line 393 (consensus message with period)
# ADD:
else:
    # No consensus - use parallel status format
    no_consensus_msg = lang_manager.get('comprehensive_earnings.no_consensus_status')
    result_parts.append(no_consensus_msg + ".")
```

**Location 2: Comprehensive display (lines 497-513)**

**Remove bold header and explanatory lines**
```python
# REMOVE lines 498-513:
if not consensus_result.consensus_reached:
    no_consensus_header = lang_manager.get('comprehensive_earnings.no_consensus_summary_header')
    no_consensus_explanation = lang_manager.get(
        'comprehensive_earnings.no_consensus_explanation',
        rounds=consensus_result.final_round
    )
    distribution_num = self._assigned_distributions.get(participant_name, 1)
    no_consensus_outcome = lang_manager.get(
        'comprehensive_earnings.no_consensus_outcome_line',
        class_name=comprehensive_data['class_display_name'],
        distribution_num=distribution_num,
        earnings=final_earnings
    )
    display_parts.extend([no_consensus_header, no_consensus_explanation, no_consensus_outcome, ""])

# No longer needed - status now in header, marker in outcomes list
```

**Location 3: Outcome marker (lines 540-554)**

**Add random assignment marker for no-consensus**
```python
# MODIFY lines 540-554:
# Determine group choice for marking
group_choice_principle = None
group_choice_constraint = None
is_random_assignment = False  # ADD this

if consensus_result.consensus_reached and consensus_result.agreed_principle:
    group_choice_principle = consensus_result.agreed_principle.principle.value
    group_choice_constraint = consensus_result.agreed_principle.constraint_amount
else:  # ADD this block
    # For no-consensus, mark the randomly assigned outcome
    is_random_assignment = True
    distribution_num = self._assigned_distributions.get(participant_name, 1)
    # Find which outcome matches participant's random assignment
    # Will set marker in loop below

# Add all outcomes with proper marking
for outcome in comprehensive_data['outcomes']:
    choice_marker = ""

    if consensus_result.consensus_reached:
        # Consensus: mark group choice
        if group_choice_principle == outcome['principle_key']:
            if outcome['constraint_amount'] is None or outcome['constraint_amount'] == group_choice_constraint:
                choice_marker = lang_manager.get('comprehensive_earnings.markers.group_choice')
    else:  # ADD this block
        # No consensus: mark random assignment
        if is_random_assignment:
            distribution_num = self._assigned_distributions.get(participant_name, 1)
            if outcome['distribution'].endswith(str(distribution_num)):
                choice_marker = lang_manager.get('comprehensive_earnings.markers.random_assignment')
                is_random_assignment = False  # Only mark first match
```

## Implementation Steps

1. **Update translation keys** (3 changes in `english_prompts.json`)
   - Replace no_consensus_summary_header
   - Add period to no_consensus_outcome_line
   - Add random_assignment marker

2. **Update CounterfactualsService** (3 locations in `counterfactuals_service.py`)
   - Add else clause for no-consensus status (line ~394)
   - Remove comprehensive display header block (lines 497-513)
   - Add random assignment marker logic (lines 540-554)

3. **Replicate for Spanish and Mandarin**
   - Apply same translation key changes to `spanish_prompts.json`
   - Apply same translation key changes to `mandarin_prompts.json`

## Testing Validation

### Expected Output (No-Consensus)
```
PHASE 2 FINAL RESULTS: $0.95
Assigned income class: Medium low
No consensus reached: Random assignment applied.

Income class probabilities:
- High: 5%
...

EXPERIMENT DISTRIBUTIONS AND SELECTION MAPPING
...

FINAL PHASE 2 RESULTS - PRINCIPLE OUTCOMES FOR Medium low CLASS:
- Maximizing Floor Income → Distribution 4 → $16,000 → $1.6
- Maximizing Average Income → Distribution 1 → $13,000 → $1.3 ← RANDOM ASSIGNMENT
...
```

### Test Cases
1. Run no-consensus experiment → verify status line format matches consensus
2. Check spacing → single blank line after status, matching consensus
3. Verify marker → random assignment outcome flagged in list
4. Test all languages → English, Spanish, Mandarin formatting identical

## Files Modified
- `translations/english_prompts.json` (lines 395, 397, 399)
- `translations/spanish_prompts.json` (same keys)
- `translations/mandarin_prompts.json` (same keys)
- `core/services/counterfactuals_service.py` (lines ~394, 497-513, 540-554)
