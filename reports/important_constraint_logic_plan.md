# Constraint Logic and Actual Earnings Display Fix - Implementation Plan

## Executive Summary

This implementation plan addresses two critical issues in the counterfactual system:

1. **Missing Actual Earnings**: Agents are not shown how much they personally earned through their chosen principle
2. **Incomplete Constraint Logic**: The system doesn't properly calculate which distribution would be chosen based on specific constraint amounts

The current implementation uses a fixed constraint amount for all counterfactual calculations, rather than dynamically evaluating which distribution each constraint amount would choose.

## Critical Issue Analysis

### Issue 1: Missing Actual Earnings Display

**Problem**: Agents currently see counterfactual alternatives but NOT their own actual earnings from their chosen principle.

**Current Behavior**: 
```
Two-Stage Voting Complete | Your vote: 3 (Maximizing Average with Floor Constraint) with $13,000 constraint
Group consensus: YES (Agreed: Maximizing Average with Floor Constraint with $13,000)

Alternative earnings analysis:
- Under Maximizing Floor Income: $15,000 ($1.50) 
- Under Maximizing Average Income: $24,000 ($2.40)
- Under Floor Constraint: $20,000 ($2.00)
- Under Range Constraint: $18,000 ($1.80)
```

**Missing Information**: The agent's own actual earnings under the chosen principle are never displayed.

### Issue 2: Incomplete Constraint Logic

**Problem**: The system uses a static constraint amount (either provided or default 15000) for counterfactuals rather than calculating which distribution each specific constraint amount would choose.

**Current Logic Flow**:
1. Group reaches consensus on "Maximizing Average with Floor Constraint of $13,000"
2. System applies $13,000 constraint → selects Distribution X
3. For counterfactuals, system uses same $13,000 for other constraint calculations
4. This is wrong - different constraint amounts should select different distributions

**Expected Constraint Logic**:
- **Floor constraint ≤ $12,000**: Should choose Distribution 1 (highest average among those meeting constraint)  
- **Floor constraint ≤ $13,000**: Should choose Distribution 2
- **Floor constraint ≤ $14,000**: Should choose Distribution 3
- **Floor constraint ≤ $15,000**: Should choose Distribution 4

- **Range constraint ≤ $20,000**: Should choose Distribution 1 (highest average among those meeting constraint)
- **Range constraint ≤ $17,000**: Should choose Distribution 3  
- **Range constraint ≤ $15,000**: Should choose Distribution 2

## Root Cause Analysis

### Constraint Logic Gap in DistributionGenerator

**Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/distribution_generator.py:307-361`

**Current Implementation**: `calculate_alternative_earnings_by_principle_fixed_class()` method:

```python
# Line 329-332 - PROBLEM: Uses provided constraint_amount or default 15000
if principle in [JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, 
               JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT]:
    # Use provided constraint or a reasonable default
    constraint = constraint_amount if constraint_amount is not None else 15000
```

**Issue**: This uses the SAME constraint amount for ALL constraint principles, rather than calculating what each specific constraint amount would choose.

### Missing Actual Earnings in CounterfactualsService

**Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py:440-483`

**Current Implementation**: The `deliver_results_and_update_memory()` method builds results but doesn't clearly show the participant's actual earnings under their chosen principle.

**Missing Logic**: 
1. No clear identification of "Your actual earnings under chosen principle: $X"
2. Counterfactuals don't distinguish between actual and alternative earnings
3. Memory updates mix consensus info with alternatives without highlighting actual results

### Memory Content Display Issues

**Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/memory_content.py:543-655`

**Current Issues**:
1. `build_two_stage_voting_complete_delta()` doesn't prominently display actual earnings
2. Counterfactual table shows alternatives but not highlighted actual earnings
3. No clear separation between "what you earned" vs "what you could have earned"

## Affected Components

### Core Files Requiring Changes

1. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/distribution_generator.py`**
   - `calculate_alternative_earnings_by_principle_fixed_class()` method
   - Add new method: `calculate_constraint_specific_earnings_by_principle_fixed_class()`

2. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`**  
   - `calculate_phase2_counterfactuals()` method
   - `build_detailed_results()` method
   - `deliver_results_and_update_memory()` method

3. **`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/memory_content.py`**
   - `build_two_stage_voting_complete_delta()` method
   - `_build_counterfactual_table()` method

4. **Translation Files** (for multi-language support):
   - `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`
   - `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`  
   - `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`

5. **Language Support Infrastructure**:
   - `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/language_manager.py` - Language-specific formatting
   - `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/cultural_adaptation.py` - Currency and number formatting

### Data Flow Integration Points

1. **Two-Stage Voting** → **Constraint Amount Storage** → **Counterfactuals Calculation**
2. **Distribution Application** → **Actual Earnings Calculation** → **Results Display**
3. **Memory Updates** → **Voting Results** → **Final Rankings**

## Implementation Strategy

### Step 1: Enhanced Constraint Logic in DistributionGenerator

**Target**: Create dynamic constraint evaluation that considers different constraint amounts

**New Method**: `calculate_constraint_specific_earnings_by_principle_fixed_class()`

```python
@staticmethod
def calculate_constraint_specific_earnings_by_principle_fixed_class(
    distributions: List[IncomeDistribution], 
    assigned_class: IncomeClass,
    actual_constraint_amount: Optional[int] = None,
    alternative_constraint_amounts: Optional[Dict[str, int]] = None
) -> dict:
    """
    Calculate earnings under each principle with constraint-specific distribution selection.
    
    For constraint principles, evaluates which distribution each constraint amount would choose
    rather than using a fixed constraint across all principles.
    
    Args:
        distributions: List of distributions to evaluate
        assigned_class: Fixed income class for participant
        actual_constraint_amount: The constraint amount actually chosen by group
        alternative_constraint_amounts: Dict of principle_key -> constraint_amount for alternatives
        
    Returns:
        Dict[principle_key, earnings] with constraint-specific distribution selection
    """
```

**Algorithm**:
1. For non-constraint principles (floor, average): Use existing logic
2. For constraint principles with actual consensus: Use actual constraint amount to select distribution
3. For constraint principles as alternatives: Use reasonable default constraints (12k, 13k, 14k, 15k, etc.) to show range of possibilities
4. Calculate earnings based on constraint-specific distribution selection

### Step 2: Actual Earnings Identification in CounterfactualsService

**Target**: Clearly identify and display participant's actual earnings

**Enhanced Method**: `calculate_phase2_counterfactuals()`

**New Logic**:
1. Identify which principle was actually chosen by the group
2. Calculate participant's actual earnings under that specific principle + constraint
3. Calculate true alternatives under other principles with appropriate constraint amounts
4. Return structure: `{actual_earnings: float, alternatives: Dict[str, float]}`

**Enhanced Method**: `build_detailed_results()`

**New Structure**:
```
Phase 2 Results: Income Class Assignment and Earnings

This assigns you to the following income class: MEDIUM  
Your actual earnings under the chosen principle: $20,000 (Payoff: $2.00)

Alternative earnings analysis:
- Under Maximizing Floor Income: $15,000 ($1.50) [would choose Distribution 4]
- Under Maximizing Average Income: $24,000 ($2.40) [would choose Distribution 1]
- Under Floor Constraint $12,000: $24,000 ($2.40) [would choose Distribution 1]  
- Under Floor Constraint $14,000: $21,000 ($2.10) [would choose Distribution 3]
- Under Range Constraint $20,000: $24,000 ($2.40) [would choose Distribution 1]
- Under Range Constraint $15,000: $20,000 ($2.00) [would choose Distribution 2]
```

### Step 3: Memory Content Enhancement 

**Target**: Improve memory content to clearly separate actual vs alternative earnings

**Enhanced Method**: `build_two_stage_voting_complete_delta()`

**New Structure**:
1. **Voting Summary**: Your vote + group consensus
2. **Actual Results**: Your class assignment + actual earnings (highlighted)
3. **Alternative Analysis**: What you would have earned under other principles (clearly labeled as alternatives)

**Enhanced Method**: `_build_counterfactual_table()`

**New Format**:
```
Your Actual Earnings: $20,000 ($2.00) under Maximizing Average with Floor Constraint ($13,000)

Alternative Earnings Under Other Principles:
• Maximizing Floor Income: $15,000 ($1.50)
• Maximizing Average Income: $24,000 ($2.40)  
• Floor Constraint $12,000: $24,000 ($2.40)
• Range Constraint $20,000: $24,000 ($2.40)
```

### Step 4: Comprehensive Multi-Language Translation Updates

**Target**: Add translation keys for new actual earnings display format across all supported languages

#### New Translation Keys for English (`english_prompts.json`):
```json
{
  "results": {
    "actual_earnings_header": "Your actual earnings under the chosen principle:",
    "actual_earnings_display": "${earnings} (Payoff: ${payoff})",
    "alternative_earnings_header": "Alternative earnings analysis:",
    "alternative_with_distribution": "Under {principle}: ${earnings} (${payoff}) [would choose Distribution {dist_num}]",
    "income_class_assignment": "This assigns you to the following income class: {class_name}",
    "distribution_selection_note": "[would choose Distribution {dist_num}]"
  },
  "memory": {
    "actual_earnings_label": "Your actual earnings: ${earnings} (${payoff}) under {principle}",
    "alternatives_header": "Alternative Earnings Under Other Principles:",
    "constraint_specific_note": "with ${constraint_amount} constraint"
  }
}
```

#### New Translation Keys for Spanish (`spanish_prompts.json`):
```json
{
  "results": {
    "actual_earnings_header": "Sus ganancias reales bajo el principio elegido:",
    "actual_earnings_display": "${earnings} (Pago: ${payoff})",
    "alternative_earnings_header": "Análisis de ganancias alternativas:",
    "alternative_with_distribution": "Bajo {principle}: ${earnings} (${payoff}) [elegiría Distribución {dist_num}]",
    "income_class_assignment": "Esto te asigna a la siguiente clase de ingresos: {class_name}",
    "distribution_selection_note": "[elegiría Distribución {dist_num}]"
  },
  "memory": {
    "actual_earnings_label": "Sus ganancias reales: ${earnings} (${payoff}) bajo {principle}",
    "alternatives_header": "Ganancias Alternativas Bajo Otros Principios:",
    "constraint_specific_note": "con restricción de ${constraint_amount}"
  }
}
```

#### New Translation Keys for Mandarin (`mandarin_prompts.json`):
```json
{
  "results": {
    "actual_earnings_header": "您在所选原则下的实际收入：",
    "actual_earnings_display": "${earnings}（回报：${payoff}）",
    "alternative_earnings_header": "替代收入分析：",
    "alternative_with_distribution": "在{principle}下：${earnings}（${payoff}）[会选择分配{dist_num}]",
    "income_class_assignment": "这将您分配到以下收入阶层：{class_name}",
    "distribution_selection_note": "[会选择分配{dist_num}]"
  },
  "memory": {
    "actual_earnings_label": "您的实际收入：${earnings}（${payoff}）在{principle}下",
    "alternatives_header": "其他原则下的替代收入：",
    "constraint_specific_note": "约束条件为${constraint_amount}"
  }
}
```



## Technical Implementation Details

### Enhanced Constraint Evaluation Algorithm

**Floor Constraint Logic**:
```python
def evaluate_floor_constraint_distributions(distributions, constraint_amounts):
    """
    For each constraint amount, determine which distribution maximizing average 
    with floor constraint would choose.
    """
    results = {}
    for amount in constraint_amounts:
        # Filter distributions meeting floor constraint
        valid_dists = [d for d in distributions if d.low >= amount]
        if valid_dists:
            # Choose highest average among valid
            chosen = max(valid_dists, key=lambda d: d.get_average_income())
        else:
            # Fallback: highest floor if none meet constraint
            chosen = max(distributions, key=lambda d: d.low)
        results[amount] = chosen
    return results
```

**Range Constraint Logic**:
```python  
def evaluate_range_constraint_distributions(distributions, constraint_amounts):
    """
    For each constraint amount, determine which distribution maximizing average
    with range constraint would choose.
    """
    results = {}
    for amount in constraint_amounts:
        # Filter distributions meeting range constraint  
        valid_dists = [d for d in distributions if d.get_range() <= amount]
        if valid_dists:
            # Choose highest average among valid
            chosen = max(valid_dists, key=lambda d: d.get_average_income())
        else:
            # Fallback: smallest range if none meet constraint
            chosen = min(distributions, key=lambda d: d.get_range())
        results[amount] = chosen
    return results
```

### Integration with Existing Architecture

**Services Integration**: 
- CounterfactualsService continues to be the single source of truth for payoff calculations
- Enhanced methods maintain existing interface contracts
- Memory service integration preserved for multilingual support
- Language Manager integration for consistent multilingual display

**Multilingual Architecture Integration**:
- CounterfactualsService uses LanguageManager for all display text
- Cultural adaptation applied to currency and number formatting
- Translation keys properly routed through existing translation infrastructure
- Maintains consistency with existing multilingual memory updates

**Backward Compatibility**:
- Existing `calculate_alternative_earnings_by_principle_fixed_class()` method maintained
- New enhanced method added alongside for gradual migration
- Existing parsing and display logic preserved where functional

## Testing Strategy

### Unit Tests

1. **Constraint Logic Validation**:
   ```python
   def test_constraint_specific_distribution_selection():
       # Test that different constraint amounts select different distributions
       # Verify floor constraint $12k vs $14k select different distributions
       # Verify range constraint $15k vs $20k select different distributions
   ```

2. **Actual Earnings Display**:
   ```python
   def test_actual_earnings_identification():
       # Test that actual earnings are correctly identified and displayed
       # Test separation between actual and alternative earnings
   ```

3. **Multi-Language Support**:
   ```python
   def test_multilingual_earnings_display():
       # Test earnings display in English, Spanish, Mandarin
       # Verify translation key usage and formatting
       # Test cultural adaptation for currency formatting
       # Verify constraint amount formatting in each language
   
   def test_cultural_number_formatting():
       # Test US format: $20,000 for English
       # Test European format: $20.000 for Spanish  
       # Test Asian format: $20,000 or ￥20,000 for Mandarin
       # Verify decimal separators for payoff values
   ```

### Integration Tests

1. **End-to-End Constraint Flow**:
   - Test complete flow from voting → constraint amount → distribution selection → earnings calculation → display

2. **Memory Content Consistency**:
   - Test that memory updates contain consistent actual vs alternative earnings information
   - Verify multilingual memory updates maintain formatting consistency
   - Test that cultural adaptations are preserved in memory content

3. **Phase2 Results Delivery**:
   - Test that `deliver_results_and_update_memory()` properly displays actual earnings
   - Verify multilingual results delivery uses correct translation keys
   - Test that currency formatting matches language preferences

4. **Cross-Language Consistency**:
   - Test that identical experiments produce equivalent results across all languages
   - Verify that constraint amounts are interpreted consistently regardless of language
   - Test that principle names and earnings displays maintain semantic equivalence

### Example Response Validation

**Expected Output Format**:
```
Two-Stage Voting Complete | Your vote: 3 (Maximizing Average with Floor Constraint) with $13,000 constraint
Group consensus: YES (Agreed: Maximizing Average with Floor Constraint with $13,000)

This assigns you to the following income class: MEDIUM
Your actual earnings under the chosen principle: $20,000 (Payoff: $2.00)

Alternative earnings analysis:
- Under Maximizing Floor Income: $15,000 ($1.50) [would choose Distribution 4]
- Under Maximizing Average Income: $24,000 ($2.40) [would choose Distribution 1] 
- Under Floor Constraint $12,000: $24,000 ($2.40) [would choose Distribution 1]
- Under Range Constraint $20,000: $24,000 ($2.40) [would choose Distribution 1]
```

## Risk Assessment

### Low Risk Areas
- **Existing Non-Constraint Principles**: Floor and Average principle calculations remain unchanged
- **Existing Interface Contracts**: CounterfactualsService maintains same method signatures
- **Translation System**: Existing translation infrastructure supports new keys

### Medium Risk Areas  
- **Constraint Evaluation Complexity**: New logic for evaluating constraint-specific distributions
- **Memory Content Changes**: Updates to memory formatting may affect parsing
- **Multi-Language Consistency**: Must ensure consistent implementation across all languages

### High Risk Areas
- **Integration with Two-Stage Voting**: Must correctly capture and use actual constraint amounts from voting
- **Backward Compatibility**: Changes to counterfactuals calculation may affect existing experiments

## Mitigation Strategies

1. **Incremental Implementation**: 
   - Add enhanced methods alongside existing ones
   - Test thoroughly before switching over
   - Maintain fallback to existing logic

2. **Comprehensive Testing**:
   - Unit test constraint evaluation logic with known distribution sets
   - Integration test with various constraint amounts and principles
   - Validate multi-language display formatting

3. **Data Validation**:
   - Add logging to verify constraint amounts are correctly captured from voting
   - Validate distribution selection logic with different constraint values  
   - Confirm actual earnings calculation matches expected results

## Timeline Estimation

### Phase 1: Enhanced Constraint Logic (2-3 hours)
- Implement new constraint evaluation methods in DistributionGenerator
- Add constraint-specific distribution selection algorithms
- Unit test constraint evaluation logic

### Phase 2: Actual Earnings Display (2-3 hours)  
- Enhance CounterfactualsService to identify actual earnings
- Update build_detailed_results() to prominently display actual earnings
- Modify memory content builders for clear actual vs alternative separation

### Phase 3: Multi-Language Support (2-3 hours)
- Add new translation keys to all three language files (English, Spanish, Mandarin)
- Implement cultural adaptation for currency and number formatting
- Test formatting and display consistency across languages
- Verify semantic equivalence of earnings displays across languages
- Test constraint amount parsing and display in each language
- Validate memory content updates maintain multilingual consistency

### Phase 4: Integration and Testing (2-3 hours)
- Integration testing with two-stage voting system
- End-to-end testing with various constraint amounts
- Regression testing to ensure existing functionality preserved

### Total Estimated Time: 8-12 hours

## Dependencies

### Prerequisites
- Understanding of existing constraint evaluation logic in DistributionGenerator  
- Knowledge of CounterfactualsService architecture and memory integration
- Access to test distributions and expected constraint evaluation results

### External Dependencies
- Two-stage voting system must correctly capture and pass constraint amounts
- Translation system must support new localization keys
- Memory service integration for multilingual updates
- Cultural adaptation utilities must handle all supported currency formats
- Language Manager must properly route translation keys for all supported languages

## Success Criteria

### Functional Requirements Met
1. **Actual Earnings Displayed**: Agents see their personal earnings under chosen principle prominently displayed
2. **Constraint-Specific Logic**: Different constraint amounts result in different distribution selections and earnings
3. **Clear Separation**: Actual earnings clearly distinguished from alternative earnings
4. **Comprehensive Multi-Language Support**: All three languages (English, Spanish, Mandarin) display actual and alternative earnings correctly
5. **Cultural Adaptation**: Currency and number formatting respects cultural conventions for each language
6. **Semantic Consistency**: Earnings displays maintain equivalent meaning across all supported languages

### Technical Requirements Met  
1. **Backward Compatibility**: Existing counterfactual calculations continue to work
2. **Integration Preserved**: CounterfactualsService continues to work with Phase2Manager and voting system
3. **Performance**: Enhanced constraint evaluation doesn't significantly slow down experiments
4. **Maintainability**: New code follows existing patterns and architecture

### User Experience Improved
1. **Clarity**: Agents understand their actual results vs hypothetical alternatives
2. **Transparency**: Clear explanation of which distributions constraint amounts would choose
3. **Consistency**: Results display format matches user expectations and experimental design
4. **Cultural Relevance**: Displays respect cultural formatting conventions for international participants
5. **Linguistic Accessibility**: All earnings information equally accessible across supported languages

## Implementation Notes

### Key Algorithm Changes
- Replace fixed constraint amount usage with dynamic constraint evaluation
- Add distribution selection logic for different constraint values
- Enhance results formatting to highlight actual vs alternative earnings

### Preserved Elements
- Existing CounterfactualsService interface and protocols
- Multi-language support architecture  
- Memory service integration patterns
- Phase2Manager orchestration flow

### New Elements
- Constraint-specific distribution evaluation methods
- Enhanced actual earnings identification and display
- Improved memory content formatting for clarity
- Extended translation keys for earnings display across all languages
- Cultural adaptation integration for currency and number formatting
- Multilingual semantic consistency validation
- Language-specific constraint amount parsing and display

This implementation plan provides a systematic approach to fixing both the constraint logic and actual earnings display issues while maintaining the robust architecture and multi-language support of the existing framework.