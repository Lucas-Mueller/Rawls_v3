# Payoff Notification Simplification Plan

## Goal
Simplify the Phase 1 demonstration round payoff notification by removing duplication and consolidating information into a cleaner format.

## Current vs Target Format

**Current:**
```
Your Response: I choose maximizing the floor income. I am sure about this choice.
Chosen Principle: maximizing_floor
Assigned Class: Medium high
Situation: A
Your Payoff (already in your bank account): 2.20

=== PAYOFF NOTIFICATION ===
YOUR CHOICE SUMMARY
You chose: Maximizing Floor Income
Your outcome: Distribution 4 → Medium high → $22,000 → $2.2

ROUND 1 CHOICE RESULTS - PRINCIPLE OUTCOMES FOR Medium high CLASS:
...
```

**Target:**
```
Your Response: I choose maximizing the floor income. I am sure about this choice.

=== PAYOFF NOTIFICATION ===
Chosen Principle: Maximizing Floor Income
Assigned Class: Medium High
Situation: A
Your Payoff (already in your bank account): 2.20

Outcome for each principle for class Medium High:
...
```

## Key Changes
1. Keep only "Prompt" and "Your Response" before payoff notification
2. Move basic info (Chosen Principle, Assigned Class, Situation, Payoff) inside the payoff notification block
3. Remove the "YOUR CHOICE SUMMARY" section entirely
4. Simplify the principle outcomes header

## Implementation Tasks

### Task 1: Modify `core/phase1_manager.py`
**Location:** `_step_1_3_principle_application` method (lines 709-735)

**Changes:**
1. Restructure `round_content` assembly:
   - Keep only prompt and response before payoff notification
   - Move chosen principle, assigned class, situation/multiplier, and payoff lines INTO the earnings_display

2. Modify earnings_display building logic (lines 624-697):
   - Remove summary section (lines 627-667)
   - Add basic info at the start of earnings_display instead
   - Simplify principle outcomes header

**Pseudo-code for new structure:**
```python
# Build round_content with only prompt and response
round_content = f"""Prompt: {application_prompt}
Your Response: {text_response}

{earnings_display}"""  # earnings_display now contains everything else

# Build earnings_display with:
# 1. Payoff notification header
# 2. Basic info (principle, class, situation, payoff)
# 3. Simplified outcomes header
# 4. Outcome lines
earnings_display = f"""{payoff_notification_header}
Chosen Principle: {principle_name_localized}
Assigned Class: {class_name_localized}
{situation_or_multiplier_line}
Your Payoff (already in your bank account): {earnings:.2f}

{simplified_outcomes_header}
{outcome_lines}"""
```

### Task 2: Update Translation Files
**Files:**
- `translations/english_prompts.json`
- `translations/spanish_prompts.json`
- `translations/mandarin_prompts.json`

**Changes:**
1. Add new key for simplified outcomes header:
   - English: `"principle_outcomes_simple_header": "Outcome for each principle for class {class_name}:"`
   - Spanish: `"principle_outcomes_simple_header": "Resultado para cada principio para la clase {class_name}:"`
   - Mandarin: `"principle_outcomes_simple_header": "每个原则对{class_name}类的结果："`

2. Keep existing labels (no removal needed for backward compatibility):
   - `memory_field_labels.payoff_notification_header`
   - `memory_field_labels.chosen_principle`
   - `memory_field_labels.assigned_class`
   - `memory_field_labels.original_values_situation`
   - `memory_field_labels.distribution_multiplier`
   - `memory_field_labels.your_payoff`

### Task 3: Testing
**Test files to update:**
- Review any golden/contract tests that capture payoff notification format
- Update expected outputs in test fixtures if needed
- Run component tests to verify multilingual support

**Manual verification:**
- Run `python main.py config/fast.yaml` and inspect demonstration round memory updates
- Verify format in English, Spanish, and Mandarin

## Technical Notes

### Location of Key Logic
- **Round content assembly**: `core/phase1_manager.py:709-735`
- **Earnings display building**: `core/phase1_manager.py:624-697`
- **Summary section to remove**: `core/phase1_manager.py:627-667`
- **Principle outcomes header**: `core/phase1_manager.py:670-675`

### Why This is Simple
- Single file modification (`core/phase1_manager.py`)
- Minimal translation updates (add one new key)
- No data model changes
- No service architecture changes
- Purely presentational/formatting change

### Edge Cases to Handle
- Constraint amount display (for principles 3 & 4)
- Original values mode vs dynamic distributions
- Multilingual number formatting (already handled by existing code)

## Risk Assessment
**Low Risk** - This is a presentational change only:
- No logic changes to payoff calculation
- No changes to memory update mechanism
- No changes to agent behavior
- Existing translation keys remain for backward compatibility
