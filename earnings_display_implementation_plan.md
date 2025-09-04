# Earnings Display Implementation Plan

## Problem Analysis

**Core Issues Identified:**

1. **Missing Actual Earnings Prominence**: Agents see counterfactual alternatives but their own actual earnings under the chosen principle lack clear "actual vs alternative" distinction
2. **Missing Decision Landscape Context**: Agents don't see the complete mapping of how each principle and constraint combination would select distributions
3. **Incomplete Counterfactual Information**: Current system only shows earnings under different principles but doesn't show which distribution each principle would have selected

**Impact**: Agents cannot understand the full decision landscape or easily distinguish their actual choice from alternatives, making it difficult to evaluate their decision-making process.

## Current System Analysis

### Existing Architecture Strengths
- **Services-first architecture**: `CounterfactualsServic11e` handles all results display
- **Template-based results**: Uses localized templates through `phase2_results_delivery_prompt`
- **Translation infrastructure**: Multi-language support already in place
- **Memory integration**: Results are properly integrated with agent memory

### Root Cause Assessment

**Issue 1: Missing Decision Context**
- **Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`
- **Problem**: Results don't show the principle-to-distribution mapping table that agents need to understand their decision landscape
- **Current pattern**: Shows only final earnings without showing which distribution each principle selected

**Issue 2: Results Display Structure**
- **Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`
- **Problem**: No clear visual distinction between actual vs alternative earnings
- **Current pattern**: Shows consensus result followed by alternative earnings without emphasizing the actual earnings

## Implementation Strategy

### Phase 1: Add Decision Landscape Context (90 minutes)

**Target**: Create comprehensive principle-to-distribution mapping display

**Changes Required:**

1. **Add new method** in `CounterfactualsService` to generate principle mapping:
```python
def _generate_principle_distribution_mapping(self, distributions: List[IncomeDistribution]) -> dict:
    """Generate mapping showing which distribution each principle/constraint combination selects."""
    from models.principle_types import JusticePrinciple, PrincipleChoice, CertaintyLevel
    
    mapping = {}
    
    # Test each principle
    principles_to_test = [
        (JusticePrinciple.MAXIMIZING_FLOOR, None, "Maximizing the floor"),
        (JusticePrinciple.MAXIMIZING_AVERAGE, None, "Maximizing average"),
    ]
    
    # Add constraint variations dynamically based on distributions
    constraint_amounts = self._generate_constraint_test_amounts(distributions)
    
    for floor_constraint in constraint_amounts['floor']:
        principles_to_test.append((
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 
            floor_constraint,
            f"Floor constraint ≤ ${floor_constraint:,}"
        ))
    
    for range_constraint in constraint_amounts['range']:
        principles_to_test.append((
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            range_constraint, 
            f"Range constraint ≤ ${range_constraint:,}"
        ))
    
    # Test each principle combination
    for principle, constraint, display_name in principles_to_test:
        try:
            choice = PrincipleChoice(
                principle=principle,
                constraint_amount=constraint,
                certainty=CertaintyLevel.SURE
            )
            chosen_distribution, chosen_index = DistributionGenerator.apply_principle_to_distributions(
                distributions, choice
            )
            mapping[display_name] = f"Distribution {chosen_index + 1}"
        except Exception as e:
            mapping[display_name] = "Unable to determine"
    
    return mapping

def _generate_constraint_test_amounts(self, distributions: List[IncomeDistribution]) -> dict:
    """Generate meaningful constraint amounts to test based on actual distribution values."""
    floor_amounts = []
    range_amounts = []
    
    # Floor constraints: test at each distribution's low income level
    for dist in distributions:
        floor_amounts.append(dist.low)
    
    # Range constraints: test at different range levels
    for dist in distributions:
        range_amount = dist.high - dist.low
        range_amounts.append(range_amount)
    
    return {
        'floor': sorted(set(floor_amounts)),
        'range': sorted(set(range_amounts))
    }
```

### Phase 2: Enhance Results Display Prominence (90 minutes)

**Target**: Add clear visual distinction between actual and alternative earnings

**Changes Required:**

1. **Add new translation keys** to emphasize actual vs alternative:

**English** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`):
```json
"results": {
  "your_actual_earnings_header": "YOUR ACTUAL EARNINGS",
  "your_actual_earnings_detail": "${earnings:.2f} under {principle_name}",
  "alternative_earnings_header": "ALTERNATIVE EARNINGS ANALYSIS",
  "alternative_earnings_note": "What you would have earned under different principles:"
}
```

**Spanish** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`):
```json
"results": {
  "your_actual_earnings_header": "SUS GANANCIAS REALES",
  "your_actual_earnings_detail": "${earnings:.2f} bajo {principle_name}",
  "alternative_earnings_header": "ANÁLISIS DE GANANCIAS ALTERNATIVAS", 
  "alternative_earnings_note": "Lo que habría ganado bajo diferentes principios:"
}
```

**Mandarin** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`):
```json
"results": {
  "your_actual_earnings_header": "您的实际收入",
  "your_actual_earnings_detail": "{principle_name}原则下的${earnings:.2f}",
  "alternative_earnings_header": "替代收入分析",
  "alternative_earnings_note": "在不同原则下您可能获得的收入："
}
```

2. **Modify results display logic** in `CounterfactualsService.deliver_results_and_update_memory()`:

**Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`

**Enhancement approach**:
- Add actual earnings section with prominent header before alternative earnings
- Use clear headers and formatting to distinguish sections
- Maintain existing template structure while adding prominence

**Specific change**: Modify the results template formatting to include:
```python
# Add after consensus_info building, before alternative earnings display:
actual_earnings_header = participant_lang_manager.get("results.your_actual_earnings_header")
actual_earnings_detail = participant_lang_manager.get("results.your_actual_earnings_detail").format(
    earnings=final_earnings,
    principle_name=chosen_principle_name
)

alternative_header = participant_lang_manager.get("results.alternative_earnings_header") 
alternative_note = participant_lang_manager.get("results.alternative_earnings_note")
```

### Phase 3: Integration and Validation (30 minutes)

**Target**: Ensure changes work correctly across languages and scenarios

**Validation Steps:**
1. Test constraint logic produces reasonable values for different distributions
2. Verify actual vs alternative earnings display clearly in all languages
3. Check memory integration maintains existing behavior
4. Validate both consensus and non-consensus scenarios

## Expected Outcome

**Before Fix:**
```
Group consensus: YES (Agreed: Maximizing Average with Floor Constraint with $13,000)

Alternative earnings analysis:
- Under Maximizing Floor Income: $15,000 ($1.50) 
- Under Maximizing Average Income: $24,000 ($2.40)
- Under Floor Constraint: $20,000 ($2.00)
- Under Range Constraint: $18,000 ($1.80)
```

**After Fix:**
```
Group consensus: YES (Agreed: Maximizing Average with Floor Constraint with $13,000)

YOUR ACTUAL EARNINGS
$20,000 under Maximizing Average with Floor Constraint ($13,000)

ALTERNATIVE EARNINGS ANALYSIS
What you would have earned under different principles:
- Under Maximizing Floor Income: $15,000 ($1.50)
- Under Maximizing Average Income: $24,000 ($2.40)
- Under Floor Constraint (with calculated constraint): $18,000 ($1.80) 
- Under Range Constraint (with calculated constraint): $22,000 ($2.20)
```

## Technical Benefits

1. **Clear Information Hierarchy**: Actual earnings prominently displayed before alternatives
2. **Dynamic Constraint Logic**: Each principle uses appropriate constraint amounts for counterfactuals
3. **Visual Distinction**: Clear headers separate actual from alternative earnings
4. **Maintained Architecture**: Works within existing services-first approach
5. **Multilingual Support**: Consistent display across all supported languages

## Risk Mitigation

**Low Risk Changes**: 
- Constraint calculation helper is isolated and testable
- Display changes work within existing template system
- Translation additions don't modify existing keys

**Fallback Protection**:
- Constraint helper includes fallback to 15000 for unexpected cases
- Existing error handling in CounterfactualsService remains unchanged

## Implementation Timeline

- **Phase 1 (Constraint Fix)**: 45 minutes
- **Phase 2 (Display Enhancement)**: 90 minutes  
- **Phase 3 (Integration/Validation)**: 30 minutes

**Total Estimated Time**: 2 hours 45 minutes

## Files Modified

1. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/distribution_generator.py` - Fix constraint logic
2. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py` - Enhanced results display
3. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json` - New display keys
4. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json` - New display keys  
5. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json` - New display keys

## Testing Requirements

1. **Unit Tests**: Validate constraint calculation logic
2. **Integration Tests**: Check results display in different consensus scenarios
3. **Language Tests**: Verify all three languages display correctly
4. **End-to-End**: Run complete experiment to validate user experience

This plan addresses both core issues with minimal architectural changes while providing maximum clarity for experimental participants.