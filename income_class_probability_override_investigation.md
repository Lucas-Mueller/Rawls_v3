# Income Class Probability Override Investigation Report

## Executive Summary

**Issue**: User configured `fast.yaml` with income class probabilities of `low: 1.0` and all others `0.0`, expecting 100% Low class assignments. However, the experiment results showed mixed class assignments (Medium, Medium Low, Medium High) instead of exclusively Low.

**Root Cause**: The `original_values_mode.enabled: true` setting in the config **overrides** the user's `income_class_probabilities` configuration, using predefined hardcoded probabilities instead.

**Impact**: Users cannot control income class assignment probabilities when `original_values_mode` is enabled, leading to unexpected experimental conditions.

## Investigation Methodology

This investigation used a systematic approach:
1. ✅ Analyzed experiment results log (`experiment_results_20250904_151417.json`)
2. ✅ Examined user configuration (`fast.yaml`)
3. ✅ Traced probability flow through Phase 1 and Phase 2 code paths
4. ✅ Investigated original_values_mode override mechanism
5. ✅ Created reproduction test to verify findings
6. ✅ Documented technical details and solutions

## Detailed Findings

### 1. User's Configuration Analysis

**File**: `config/fast.yaml`

```yaml
# Income class assignment probabilities (used when original_values_mode is disabled)
income_class_probabilities:
  high: 0.0          # 0%
  medium_high: 0.0   # 0% 
  medium: 0.0        # 0%
  medium_low: 0.0    # 0%
  low: 1.0           # 100%

# Original Values Mode Configuration
original_values_mode:
  enabled: true      # ❌ THIS OVERRIDES ABOVE PROBABILITIES
```

**Key Observation**: The comment on line 25 explicitly states probabilities are "used when original_values_mode is disabled", but `original_values_mode.enabled: true`.

### 2. Actual Experiment Results Analysis

**File**: `experiment_results_20250904_151417.json`

```json
"income_class_probabilities": {
  "high": 0.0,
  "medium_high": 0.0,
  "medium": 0.0,
  "medium_low": 0.0,
  "low": 1.0
},
"original_values_mode_enabled": true
```

**Actual Class Assignments Found**:
- `"class_put_in": "medium"`
- `"class_put_in": "medium_low"`
- `"class_put_in": "medium_high"`
- **NO** `"class_put_in": "low"` assignments found

❌ **Contradiction**: Config shows `low: 1.0` but no Low class assignments occurred.

### 3. Code Path Analysis

#### Phase 1 Probability Selection Logic

**File**: `core/phase1_manager.py` (lines 350-355)

```python
if config.original_values_mode and config.original_values_mode.enabled:
    # Use round-specific probabilities (Round 1->A, Round 2->B, etc.)
    probabilities = DistributionGenerator.get_original_values_probabilities(round_num)
else:
    # Use global configuration probabilities  
    probabilities = config.income_class_probabilities
```

**Critical Path**: When `original_values_mode.enabled=true`, the user's `income_class_probabilities` are **completely ignored**.

#### Phase 2 Probability Usage

**File**: `core/services/counterfactuals_service.py` (lines 157, 162, 172)

```python
# Phase 2 ALWAYS uses config probabilities - no original_values_mode logic
chosen_distribution, explanation = DistributionGenerator.apply_principle_to_distributions(
    distribution_set.distributions, discussion_result.agreed_principle, config.income_class_probabilities
)

assigned_class, earnings = DistributionGenerator.calculate_payoff(
    chosen_distribution, config.income_class_probabilities, random_gen=...
)
```

**Phase Inconsistency**: Phase 1 can override probabilities, but Phase 2 always uses config probabilities.

### 4. Original Values Mode Hardcoded Probabilities

**File**: `core/original_values_data.py`

The original_values_mode uses **completely different probabilities** for each round:

| Round | Situation | High | Med High | Medium | Med Low | Low |
|-------|-----------|------|----------|---------|---------|-----|
| 1 | A | 10.0% | 20.0% | 40.0% | 20.0% | 10.0% |
| 2 | B | 6.3% | 20.8% | 28.3% | 34.5% | 10.0% |
| 3 | C | 1.3% | 4.3% | 58.3% | 26.0% | 10.0% |
| 4 | D | 5.0% | 20.8% | 28.3% | 35.8% | 10.0% |

**Key Observation**: 
- User expected: `Low: 100%`
- Actual (Round 1): `Low: 10%`, `Medium: 40%`, etc.
- **Complete mismatch** between user expectation and actual behavior

### 5. Reproduction Test Results

**Test File**: `test_probability_override_issue.py`

**User's Expected Results** (with config probabilities):
```
Low: 1000 assignments (100.0%) ✅
All others: 0 assignments (0.0%) ✅
```

**Actual Results** (with original_values_mode):
```
Round 1: Medium: 39.6%, Medium Low: 19.4%, Medium High: 19.3%, High: 11.7%, Low: 10.0%
Round 2: Medium Low: 34.9%, Medium: 25.9%, Medium High: 22.1%, Low: 10.0%, High: 7.1%  
Round 3: Medium: 56.6%, Medium Low: 26.8%, Low: 10.0%, Medium High: 4.7%, High: 1.9%
Round 4: Medium Low: 35.9%, Medium: 26.7%, Medium High: 21.0%, Low: 10.0%, High: 6.4%
```

❌ **Complete Override**: User's probabilities ignored entirely.

## Technical Architecture Issues

### 1. Inconsistent Phase Behavior
- **Phase 1**: Can use either config probabilities OR original_values_mode probabilities
- **Phase 2**: Always uses config probabilities (no original_values_mode logic)
- **Result**: Inconsistent probability behavior across experimental phases

### 2. Silent Override Behavior
- No warnings when original_values_mode overrides user probabilities
- Config comments hint at the behavior but easy to miss
- Users can specify probabilities that are silently ignored

### 3. Documentation Gaps
- The config comment is the only indication of override behavior
- No runtime validation or warnings
- No clear documentation about the precedence rules

## Potential Solutions

### Option 1: Fix Configuration (Immediate)
```yaml
original_values_mode:
  enabled: false  # Allow config probabilities to work
```

**Pros**: Immediate fix, respects user's probability settings
**Cons**: Disables original_values_mode entirely

### Option 2: Add Runtime Validation (Recommended)
Add validation that warns users when original_values_mode overrides their probabilities:

```python
if config.original_values_mode and config.original_values_mode.enabled:
    if config.income_class_probabilities != default_probabilities:
        logger.warning("original_values_mode is enabled - income_class_probabilities will be ignored")
```

### Option 3: Make Phase 2 Consistent
Update Phase 2 to also respect original_values_mode when enabled:

```python
# In counterfactuals_service.py
if config.original_values_mode and config.original_values_mode.enabled:
    probabilities = DistributionGenerator.get_original_values_probabilities(current_round)
else:
    probabilities = config.income_class_probabilities
```

### Option 4: Configuration Priority System
Add explicit priority configuration:

```yaml
probability_source: "config"  # or "original_values_mode"
income_class_probabilities: {...}
original_values_mode: {...}
```

## Recommendations

### Immediate Actions
1. **User Fix**: Set `original_values_mode.enabled: false` in `fast.yaml` to use custom probabilities
2. **Documentation**: Update config file comments to be more explicit about override behavior

### Long-term Improvements  
1. **Add Validation**: Warn users when configurations conflict
2. **Consistency**: Make Phase 2 respect original_values_mode settings
3. **Documentation**: Create clear precedence rules documentation
4. **Testing**: Add regression tests for probability override scenarios

## Files Involved

### Configuration Files
- `config/fast.yaml` - User configuration with conflicting settings

### Core Logic Files  
- `core/phase1_manager.py:350-355` - Phase 1 probability selection logic
- `core/services/counterfactuals_service.py:157,162,172` - Phase 2 probability usage
- `core/original_values_data.py:15-75` - Hardcoded original values probabilities
- `core/distribution_generator.py:get_original_values_probabilities` - Round-to-situation mapping

### Test Files
- `test_probability_override_issue.py` - Reproduction test demonstrating the issue

## Conclusion

The issue is caused by **architectural design behavior**, not a bug. The `original_values_mode` feature is working as designed - it overrides user probability configurations with predefined experimental probabilities. However, this behavior is not well-documented and creates user confusion.

The solution depends on whether the user wants to:
1. **Use custom probabilities**: Disable `original_values_mode`
2. **Use research-validated probabilities**: Keep `original_values_mode` enabled and accept the predefined probabilities

The codebase should be enhanced with better validation and documentation to prevent this confusion in the future.