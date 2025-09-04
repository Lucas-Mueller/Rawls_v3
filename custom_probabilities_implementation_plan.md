# Custom Probabilities Mode Implementation Plan

## Overview

This plan implements a surgical solution to add `custom_probabilities` mode that allows using custom income class probabilities even when `original_values_mode` is enabled (using original distributions).

## Feature Request Summary

**Current System Behavior**:
- `original_values_mode.enabled=true`: Uses both original distributions AND original probabilities
- `original_values_mode.enabled=false`: Uses generated distributions AND custom probabilities

**Desired New Behavior**:
- Add `custom_probabilities.enabled=true` option that allows:
  - Using original distributions (from original_values_mode)  
  - BUT with custom probabilities (from income_class_probabilities config)

## Implementation Tasks

### Task 1: Configuration Model Addition

**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/config/models.py`

**Add after line 35 (after OriginalValuesModeConfig):**
```python
class CustomProbabilitiesConfig(BaseModel):
    """Configuration for custom probabilities mode."""
    enabled: bool = Field(default=False, description="Enable custom probabilities mode (allows using custom probabilities even with original_values_mode enabled)")
```

**Update ExperimentConfiguration class (after line 83):**
```python
custom_probabilities: Optional[CustomProbabilitiesConfig] = Field(None, description="Custom probabilities mode configuration")
```

### Task 2: Core Logic Update

**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase1_manager.py`

**Replace lines 350-355 with:**
```python
# Determine probabilities to use based on custom_probabilities override
if (config.custom_probabilities and config.custom_probabilities.enabled):
    # Override: use custom probabilities even with original_values_mode
    probabilities = config.income_class_probabilities
elif config.original_values_mode and config.original_values_mode.enabled:
    # Use round-specific probabilities (Round 1->A, Round 2->B, etc.)
    probabilities = DistributionGenerator.get_original_values_probabilities(round_num)
else:
    # Use global configuration probabilities
    probabilities = config.income_class_probabilities
```

### Task 3: Phase 2 Consistency Helper Method

**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`

**Add helper method:**
```python
def _get_probabilities_for_round(self, config: ExperimentConfiguration, round_num: int):
    """Get probabilities using the same logic as Phase 1."""
    if (config.custom_probabilities and config.custom_probabilities.enabled):
        return config.income_class_probabilities
    elif config.original_values_mode and config.original_values_mode.enabled:
        from core.distribution_generator import DistributionGenerator
        return DistributionGenerator.get_original_values_probabilities(round_num)
    else:
        return config.income_class_probabilities
```

### Task 4: Update Phase 2 Probability Usage

**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`

**Update probability usage in lines ~157, 162, 172 to use the helper method instead of directly using `config.income_class_probabilities`**

### Task 5: Configuration Validation

**Add validation method to ExperimentConfiguration:**
```python
def validate_probability_configuration(self) -> None:
    """Validate probability configuration consistency."""
    if (self.custom_probabilities and self.custom_probabilities.enabled and 
        not self.income_class_probabilities):
        raise ValueError("custom_probabilities is enabled but income_class_probabilities is not configured")
```

## Configuration Examples

### New Hybrid Mode (Desired Feature)
```yaml
# Use original distributions WITH custom probabilities
income_class_probabilities:
  high: 0.0
  medium_high: 0.0  
  medium: 0.0
  medium_low: 0.0
  low: 1.0          # 100% Low class

original_values_mode:
  enabled: true       # Use original distributions

custom_probabilities:
  enabled: true       # BUT use custom probabilities
```

### Existing Configurations (Unchanged)
```yaml
# Original mode (no change)
original_values_mode:
  enabled: true
# custom_probabilities not specified = disabled by default

# Custom mode (no change)  
original_values_mode:
  enabled: false
income_class_probabilities: {...}
# custom_probabilities not specified = disabled by default
```

## Testing Strategy

### Task 6: Backward Compatibility Tests
1. **Existing configs unchanged**: All current YAML files should produce identical behavior
2. **Default behavior preserved**: When `custom_probabilities` is not specified, system behaves identically
3. **Original mode integrity**: `original_values_mode.enabled=true` alone continues using original probabilities

### Task 7: New Feature Tests  
1. **Hybrid mode validation**: `original_values_mode.enabled=true` + `custom_probabilities.enabled=true` uses original distributions with custom probabilities
2. **Phase consistency**: Both Phase 1 and Phase 2 use the same probability selection logic
3. **Configuration validation**: Invalid combinations are caught with clear error messages

### Task 8: Create Example Configuration
Create a sample configuration file demonstrating the new hybrid mode functionality.

## Timeline Estimation

- **Tasks 1-2 (Core Implementation)**: 30 minutes - Surgical changes to existing code
- **Tasks 3-4 (Phase 2 Consistency)**: 20 minutes - Helper method and updates  
- **Task 5 (Validation)**: 10 minutes - Configuration validation
- **Tasks 6-8 (Testing & Examples)**: 20 minutes - Validate no breaking changes
- **Total**: ~1.5 hours for complete implementation

## Dependencies and Constraints

### Prerequisites
- No external dependencies required
- Existing Pydantic configuration system handles new models automatically

### Constraints
- Must maintain 100% backward compatibility
- Changes must be minimal and surgical
- No modifications to existing configuration files required

## Success Criteria

### Functional Requirements
1. ✅ `custom_probabilities.enabled=true` allows using custom probabilities with original distributions
2. ✅ All existing configurations continue to work without changes
3. ✅ Phase 1 and Phase 2 use consistent probability selection logic
4. ✅ Invalid configurations are caught with clear error messages

### Technical Requirements  
1. ✅ Minimal code changes (surgical approach)
2. ✅ No breaking changes to existing functionality
3. ✅ Proper configuration validation
4. ✅ Comprehensive testing coverage

This implementation provides exactly what was requested: the ability to use original distributions with custom probabilities, implemented in a surgical, non-breaking way that maintains full backward compatibility while adding the precise functionality needed.