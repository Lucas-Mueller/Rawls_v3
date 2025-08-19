# Weighted Income Class Assignment Implementation Plan

## Overview

This document outlines the implementation plan for changing from equal probability income class assignment to weighted probability assignment in the Frohlich Experiment system.

## Current System Analysis

### Current Implementation
- **Assignment Method**: Equal probability (20% each) using `random.choice(income_classes)`
- **Average Calculation**: Simple arithmetic mean `(high + medium_high + medium + medium_low + low) / 5`
- **Location**: `core/distribution_generator.py:135` and `models/experiment_types.py:44`

### Proposed Changes
- **Assignment Method**: Weighted probability with configurable weights
- **Default Probabilities**:
  - High: 5%
  - Medium High: 10%
  - Medium: 50%
  - Medium Low: 25%
  - Low: 10%

## Critical Impact Analysis

### 1. **Distribution Selection Changes** ⚠️ **HIGH IMPACT**
The `get_average_income()` method is used by principles to compare distributions:
- `_apply_maximizing_average()` - Uses `d.get_average_income()` to select best distribution
- `_apply_maximizing_average_floor_constraint()` - Uses weighted average for fallback selection
- `_apply_maximizing_average_range_constraint()` - Uses weighted average for final selection

**Impact**: Which distributions get selected for each principle will change, potentially affecting experimental outcomes significantly.

### 2. **Expected Earnings Calculations**
Multiple functions calculate expected earnings assuming equal probabilities:
- `calculate_alternative_earnings()` - Used for counterfactual analysis
- `calculate_alternative_earnings_by_principle()` - Used for agent feedback

**Impact**: Agent feedback about alternative earnings will change, affecting agent decision-making.

### 3. **Backward Compatibility**
Existing experiment results and analysis assume equal probabilities.

**Impact**: Need migration strategy for existing configurations and results comparison.

## Implementation Plan

### Phase 1: Configuration System Updates

#### 1.1 Update Configuration Schema
**File**: `config/default_config.yaml`

Add new section:
```yaml
# Income class assignment probabilities (must sum to 1.0)
income_class_probabilities:
  high: 0.05          # 5%
  medium_high: 0.10   # 10%
  medium: 0.50        # 50%
  medium_low: 0.25    # 25%
  low: 0.10           # 10%
```

#### 1.2 Create Configuration Model
**File**: `models/experiment_types.py`

Add new Pydantic model:
```python
class IncomeClassProbabilities(BaseModel):
    """Probabilities for income class assignment."""
    high: float = Field(default=0.05, ge=0, le=1)
    medium_high: float = Field(default=0.10, ge=0, le=1)
    medium: float = Field(default=0.50, ge=0, le=1)
    medium_low: float = Field(default=0.25, ge=0, le=1)
    low: float = Field(default=0.10, ge=0, le=1)
    
    @validator('high', 'medium_high', 'medium', 'medium_low', 'low', each_item=True)
    def validate_probability_range(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Probabilities must be between 0 and 1')
        return v
    
    @root_validator
    def validate_probabilities_sum_to_one(cls, values):
        total = sum(values.values())
        if not math.isclose(total, 1.0, rel_tol=1e-9):
            raise ValueError(f'Probabilities must sum to 1.0, got {total}')
        return values
```

### Phase 2: Logging System Updates

#### 2.1 Update GeneralExperimentInfo Model
**File**: `models/logging_types.py`

Add income class probabilities to the general experiment information:
```python
class GeneralExperimentInfo(BaseModel):
    """General experiment information for target state."""
    consensus_reached: bool
    consensus_principle: Optional[str] = None
    public_conversation_phase_2: str
    final_vote_results: Dict[str, str]
    config_file_used: str
    income_class_probabilities: Optional[Dict[str, float]] = None  # NEW FIELD
```

#### 2.2 Update Agent-Centric Logger
**File**: `utils/agent_centric_logger.py`

Update `set_general_information()` method to accept and store probabilities:
```python
def set_general_information(
    self,
    consensus_reached: bool,
    consensus_principle: Optional[str],
    public_conversation: str,
    final_vote_results: Dict[str, str],
    config_file: str,
    income_class_probabilities: Optional[Dict[str, float]] = None  # NEW PARAMETER
):
    """Set general experiment information."""
    self.general_info = GeneralExperimentInfo(
        consensus_reached=consensus_reached,
        consensus_principle=consensus_principle,
        public_conversation_phase_2=public_conversation,
        final_vote_results=final_vote_results,
        config_file_used=config_file,
        income_class_probabilities=income_class_probabilities  # NEW FIELD
    )
```

#### 2.3 Update Experiment Manager
**File**: `core/experiment_manager.py`

Pass probabilities to logging system:
```python
# Extract probabilities from config for logging
probabilities_dict = None
if hasattr(config, 'income_class_probabilities'):
    probabilities_dict = {
        "high": config.income_class_probabilities.high,
        "medium_high": config.income_class_probabilities.medium_high,
        "medium": config.income_class_probabilities.medium,
        "medium_low": config.income_class_probabilities.medium_low,
        "low": config.income_class_probabilities.low
    }

self.agent_logger.set_general_information(
    consensus_reached=phase2_results.discussion_result.consensus_reached,
    consensus_principle=(
        phase2_results.discussion_result.agreed_principle.principle.value
        if phase2_results.discussion_result.agreed_principle
        else None
    ),
    public_conversation=public_conversation,
    final_vote_results=final_vote_results,
    config_file="default_config.yaml",
    income_class_probabilities=probabilities_dict  # NEW PARAMETER
)
```

### Phase 3: Core Logic Updates

#### 3.1 Update IncomeDistribution Model
**File**: `models/experiment_types.py`

Replace current `get_average_income()` method:
```python
def get_average_income(self, probabilities: Optional[IncomeClassProbabilities] = None) -> float:
    """Get the average income across all classes with optional weighting."""
    if probabilities is None:
        # Backward compatibility: equal weights
        return (self.high + self.medium_high + self.medium + self.medium_low + self.low) / 5
    
    # Weighted average calculation
    return (
        self.high * probabilities.high +
        self.medium_high * probabilities.medium_high +
        self.medium * probabilities.medium +
        self.medium_low * probabilities.medium_low +
        self.low * probabilities.low
    )
```

#### 3.2 Update Distribution Generator
**File**: `core/distribution_generator.py`

##### 3.2.1 Update Assignment Method
Replace `calculate_payoff()` method:
```python
@staticmethod
def calculate_payoff(
    distribution: IncomeDistribution, 
    probabilities: Optional[IncomeClassProbabilities] = None
) -> Tuple[IncomeClass, float]:
    """Assign participant to income class using weighted probabilities."""
    income_classes = list(IncomeClass)
    
    if probabilities is None:
        # Backward compatibility: equal probabilities
        assigned_class = random.choice(income_classes)
    else:
        # Weighted random selection
        weights = [
            probabilities.high,
            probabilities.medium_high,
            probabilities.medium,
            probabilities.medium_low,
            probabilities.low
        ]
        assigned_class = random.choices(income_classes, weights=weights, k=1)[0]
    
    # Get income and calculate payoff
    income = distribution.get_income_by_class(assigned_class)
    payoff = income / 10000.0
    
    return assigned_class, payoff
```

##### 3.2.2 Update Principle Application Methods
Update all `_apply_maximizing_*` methods to use weighted averages:
```python
@staticmethod
def _apply_maximizing_average(
    distributions: List[IncomeDistribution], 
    probabilities: Optional[IncomeClassProbabilities] = None
) -> Tuple[IncomeDistribution, str]:
    """Apply maximizing average principle with weighted calculation."""
    best_dist = max(distributions, key=lambda d: d.get_average_income(probabilities))
    avg_income = best_dist.get_average_income(probabilities)
    explanation = f"Chose distribution with highest weighted average income: ${avg_income:.0f}"
    return best_dist, explanation
```

#### 3.3 Update Phase Managers
**Files**: `core/phase1_manager.py`, `core/phase2_manager.py`

Pass probability configuration to all distribution calculation methods.

### Phase 4: Prompt Updates

#### 4.1 Update Explanation Prompts
**File**: `translations/english_prompts.json`

Update `phase1_rounds1_4_principle_application`:
```json
"Your choice will determine which distribution is selected, and you'll be assigned to an income class within that distribution based on realistic population probabilities (middle class being most common). Your earnings will be $1 for every $10,000 of income you receive."
```

#### 4.2 Add Probability Information
Add new prompt section explaining the assignment probabilities:
```json
"income_class_assignment_explanation": "Income class assignment reflects realistic population distribution:\n- Middle class (50% probability)\n- Lower middle class (25% probability)\n- Upper middle class (10% probability)\n- Lower class (10% probability)\n- Upper class (5% probability)"
```

### Phase 5: Testing Updates

#### 5.1 Update Unit Tests
**File**: `tests/unit/test_distribution_generator.py`

- Add tests for weighted assignment
- Add tests for probability validation
- Update existing tests to handle both weighted and equal probability modes

#### 5.2 Update Integration Tests
- Verify that weighted probabilities don't break existing experiment flow
- Test configuration validation
- Test backward compatibility mode

#### 5.3 Update Logging Tests
**Files**: `tests/unit/test_agent_centric_logger.py`, `tests/integration/test_logging_integration.py`

- Add tests for income class probability logging
- Verify probabilities appear in general_information section
- Test logging with and without probabilities configured
- Test that logged probabilities match configuration values

### Phase 6: Documentation Updates

#### 6.1 Update CLAUDE.md
Add section about income class probabilities and configuration.

#### 6.2 Update Configuration Examples
Update all example configuration files to include the new probability section.

## Migration Strategy

### Backward Compatibility
1. **Default Behavior**: If no probabilities specified in config, use equal probabilities
2. **Graceful Degradation**: All functions accept optional probability parameters
3. **Configuration Migration**: Provide tool to update existing configs

### Rollout Plan
1. **Phase 1**: Implement with backward compatibility enabled by default
2. **Phase 2**: Update default configurations to use weighted probabilities
3. **Phase 3**: Eventually deprecate equal probability mode (future release)

## Risk Assessment

### High Risk Items
1. **Experimental Validity**: Results will change significantly - need careful validation
2. **Distribution Selection**: Different distributions may be selected, changing agent experience
3. **Statistical Analysis**: All existing statistical analysis assumes equal probabilities

### Mitigation Strategies
1. **A/B Testing**: Run experiments with both equal and weighted probabilities for comparison
2. **Documentation**: Clearly document the change and its implications
3. **Validation**: Extensive testing with known distribution sets

## Implementation Order

1. **Configuration System** (Low risk, foundational)
2. **Logging System Updates** (Low risk, data capture)
3. **Core Models** (Medium risk, enables everything else)
4. **Distribution Generator** (High risk, core logic)
5. **Phase Managers** (Medium risk, integration)
6. **Prompts** (Low risk, user communication)
7. **Testing** (Critical, validation)
8. **Documentation** (Low risk, communication)

## Validation Checklist

- [ ] Probabilities sum to 1.0 validation works
- [ ] Weighted random assignment produces expected frequency distribution
- [ ] Average income calculations match expected weighted averages
- [ ] Principle selection logic works with weighted averages
- [ ] Backward compatibility maintains equal probability behavior
- [ ] All existing tests pass in compatibility mode
- [ ] New tests validate weighted behavior
- [ ] Configuration validation catches invalid probability sets
- [ ] Income class probabilities logged in general_information section
- [ ] Logged probabilities match configuration values exactly
- [ ] Prompts clearly communicate the weighted assignment
- [ ] Documentation reflects the changes

## Files to Modify

### Core Files
- `config/default_config.yaml` - Add probability configuration
- `models/experiment_types.py` - Add probability model and update IncomeDistribution
- `models/logging_types.py` - Add probabilities to GeneralExperimentInfo
- `utils/agent_centric_logger.py` - Update set_general_information method
- `core/experiment_manager.py` - Pass probabilities to logger
- `core/distribution_generator.py` - Update assignment and average calculation logic
- `core/phase1_manager.py` - Pass probabilities to distribution methods
- `core/phase2_manager.py` - Pass probabilities to distribution methods

### Translation Files  
- `translations/english_prompts.json` - Update assignment explanation
- `translations/spanish_prompts.json` - Update assignment explanation
- `translations/mandarin_prompts.json` - Update assignment explanation

### Test Files
- `tests/unit/test_distribution_generator.py` - Add weighted probability tests
- `tests/unit/test_agent_centric_logger.py` - Add probability logging tests
- `tests/integration/test_complete_experiment_flow.py` - Test with weighted config
- `tests/integration/test_logging_integration.py` - Test probability logging integration

### Documentation Files
- `CLAUDE.md` - Document new configuration option
- Example config files in `hypothesis_2_&_4/configs/` - Add probability sections

## Expected Impact on Results

### Immediate Effects
1. **Middle Class Focus**: 50% assignment to medium class will make this the most common experience
2. **Reduced Extreme Outcomes**: Only 15% total assignment to high/low classes vs 40% previously
3. **Different Distribution Selection**: Weighted averages will favor distributions with higher middle-class incomes

### Strategic Implications
1. **Agent Decision-Making**: Agents may adapt strategies knowing middle class assignment is most likely
2. **Principle Preference**: May increase preference for principles that benefit middle class
3. **Group Dynamics**: Discussion may focus more on middle class outcomes

This plan provides a comprehensive roadmap for implementing weighted income class assignment while maintaining system stability and experimental validity.