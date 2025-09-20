# Plan: Integrate Constraint Fallback Explanations with Language Management

## Current Problem
The constraint fallback explanations in `DistributionGenerator` are hardcoded in English and not integrated with the language management system. When agents define unfeasible constraints, fallback messages like:
- `"No distribution met floor constraint of $15000. Chose distribution with highest floor: $12000"`
- `"No distribution met range constraint of $10000. Chose distribution with smallest range: $20000"`

Are always shown in English, even for Spanish/Mandarin participants.

## Implementation Plan

### Phase 1: Add Language Keys to Translation Files
**Files to modify**: `translations/english_prompts.json`, `translations/spanish_prompts.json`, `translations/mandarin_prompts.json`

Add new section `"constraint_explanations"` with keys for:
- `floor_constraint_fallback`: "No distribution met floor constraint of {constraint_amount}. Chose distribution with highest floor: {actual_floor}"
- `range_constraint_fallback`: "No distribution met range constraint of {constraint_amount}. Chose distribution with smallest range: {actual_range}"
- `floor_constraint_success`: "Chose distribution with highest {weighted}average ({avg_income}) meeting floor constraint of {constraint_amount}"
- `range_constraint_success`: "Chose distribution with highest {weighted}average ({avg_income}) meeting range constraint of {constraint_amount}"
- `maximizing_floor_explanation`: "Chose distribution with highest floor income: {floor_amount}"
- `maximizing_average_explanation`: "Chose distribution with highest {weighted}average income: {avg_income}"

Include proper translations for Spanish and Mandarin.

### Phase 2: Modify DistributionGenerator to Require LanguageManager
**File to modify**: `core/distribution_generator.py`

1. Update `apply_principle_to_distributions()` method signature to require `LanguageManager` parameter
2. Pass `LanguageManager` to all private methods `_apply_maximizing_*()` 
3. Replace all hardcoded English strings with localized messages using `language_manager.get()`
4. Update method signatures to make `language_manager` a required parameter

### Phase 3: Update CounterfactualsService Integration
**File to modify**: `core/services/counterfactuals_service.py`

Update the call in `apply_group_principle_and_calculate_payoffs()` (line 156-158):
```python
chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
    distribution_set.distributions, 
    discussion_result.agreed_principle, 
    config.income_class_probabilities,
    language_manager=self.language_manager
)
```

### Phase 4: Update Phase1Manager Integration  
**File to modify**: `core/phase1_manager.py`

Update the call in the payoff calculation method:
```python
chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
    distribution_set.distributions, 
    parsed_choice, 
    probabilities,
    language_manager=self.language_manager
)
```

### Phase 5: Update All Other DistributionGenerator Calls
Search codebase for all other calls to `apply_principle_to_distributions()` and update them to pass the required `language_manager` parameter.

## Expected Outcome
After implementation:
- Spanish participants will see constraint fallbacks in Spanish
- Mandarin participants will see constraint fallbacks in Mandarin  
- English participants continue to see English (no behavior change)
- All unfeasible constraint explanations properly localized in Call 2 memory updates
- Clean, consistent API requiring language manager for all distribution operations

## Files to Modify
1. `translations/english_prompts.json` - Add constraint explanation keys
2. `translations/spanish_prompts.json` - Add Spanish translations
3. `translations/mandarin_prompts.json` - Add Mandarin translations
4. `core/distribution_generator.py` - Update methods to require LanguageManager
5. `core/services/counterfactuals_service.py` - Pass LanguageManager to DistributionGenerator
6. `core/phase1_manager.py` - Pass LanguageManager to DistributionGenerator
7. Any other files calling `DistributionGenerator.apply_principle_to_distributions()`