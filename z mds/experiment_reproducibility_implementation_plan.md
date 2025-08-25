# Experiment Reproducibility Implementation Plan

## Problem Analysis

### Current Issue
The Frohlich Experiment system currently has multiple sources of randomness that make experiments non-reproducible:

1. **Agent class assignments** - Participants are randomly assigned to income classes
2. **Speaking order** - The order in which agents speak in Phase 2 discussions is randomized
3. **Distribution selection** - When no consensus is reached, random distributions are chosen
4. **Distribution generation** - Random multipliers are applied to base distributions
5. **Configuration generation** - Random model and temperature selection in experiment runner

### User Requirements
- **Mandatory reproducibility**: Every experiment run must be reproducible
- **Automatic seed generation**: Seed generated for every run (not optional)
- **Seed-based control**: Single seed value controls all randomness
- **Result tracking**: Seeds saved with experiment results for future reproduction
- **Deterministic generation**: If no seed specified, generate from configuration parameters

## Current Sources of Randomness Analysis

### 1. Phase 2 Manager (`core/phase2_manager.py`)
- **Line 450**: `random.shuffle(participant_indices)` - Randomizes speaking order
- **Line 775**: `random.choice(distribution_set.distributions)` - Random distribution selection for no-consensus scenarios

### 2. Distribution Generator (`core/distribution_generator.py`)
- **Line 36**: `random.uniform(multiplier_range[0], multiplier_range[1])` - Random distribution scaling
- **Line 205**: `random.choice(income_classes)` - Random class assignment (backward compatibility)
- **Line 215**: `random.choices(income_classes, weights=weights, k=1)[0]` - Weighted random class assignment
- **Lines 230, 277**: Additional random assignments in alternative earnings calculations

### 3. Experiment Runner (`utils/experiment_runner.py`)
- **Line 51**: `random.choice(models)` - Random model selection from list
- **Line 56**: `random.uniform(temperature[0], temperature[1])` - Random temperature selection

## Proposed Solution Design

### Core Concept
Implement a **mandatory** centralized seeding mechanism that:
1. **Always generates a seed** for every experiment run
2. Sets Python's global random seed before any random operations  
3. Allows optional seed specification in YAML files (overrides auto-generation)
4. Auto-generates seeds from configuration when not specified
5. Saves seeds with experiment results for reproducibility
6. Maintains backward compatibility with existing configurations

### Seed Generation Strategy
```python
def generate_seed_from_config(config: ExperimentConfiguration) -> int:
    """Generate deterministic seed from configuration parameters."""
    # Use configuration elements to create reproducible seed
    seed_components = [
        len(config.agents),
        config.phase2_rounds,
        hash(str(config.distribution_range_phase1)),
        hash(str(config.distribution_range_phase2)),
        hash(config.language)
    ]
    return hash(tuple(seed_components)) % (2**31)  # Ensure positive 32-bit integer
```

### Configuration Schema Extension
```yaml
# Seed field - optional specification, always used internally
seed: 12345  # Optional: explicit seed value
# If omitted, seed will be auto-generated from config parameters
# EVERY experiment run will have a seed (either specified or generated)

# Example usage:
language: "English"
agents: [...]
utility_agent_model: "gpt-4.1-mini"
phase2_rounds: 20
seed: 42  # Explicit seed (optional)
# OR no seed field = auto-generated seed

# Both cases result in fully reproducible experiments
```

## Implementation Plan

### Phase 1: Core Seed Management

#### 1.1 Create Seed Manager Module
**File**: `utils/seed_manager.py`
```python
class ExperimentSeedManager:
    """Centralized seed management for experiment reproducibility."""
    
    @staticmethod
    def set_experiment_seed(seed: int) -> None:
        """Set global random seed for all experiment operations."""
    
    @staticmethod
    def generate_seed_from_config(config: ExperimentConfiguration) -> int:
        """Generate deterministic seed from configuration."""
    
    @staticmethod
    def initialize_reproducibility(config: ExperimentConfiguration) -> int:
        """ALWAYS initialize reproducibility and return the seed used."""
```

#### 1.2 Update Configuration Models
**File**: `config/models.py`
- Add optional `seed: Optional[int] = None` field to `ExperimentConfiguration`
- Add `get_effective_seed()` method that ALWAYS returns a seed (generated or specified)
- Add validation for seed value (positive 32-bit integer)

#### 1.3 Update Experiment Manager
**File**: `core/experiment_manager.py`
- **ALWAYS** initialize seed at the start of `run_complete_experiment()`
- Log seed source (specified vs generated)
- Save seed in experiment results for all runs

### Phase 2: Update Random Operations

#### 2.1 Phase 2 Manager Updates
**File**: `core/phase2_manager.py`
- Ensure speaking order randomization uses seeded random
- Ensure random distribution selection uses seeded random
- Add logging for seed-controlled operations

#### 2.2 Distribution Generator Updates
**File**: `core/distribution_generator.py`
- Ensure all random operations use seeded random
- Add seed logging for distribution generation
- Maintain compatibility with Original Values Mode

#### 2.3 Experiment Runner Updates
**File**: `utils/experiment_runner.py`
- Update `generate_random_config()` to use seeded random
- Add seed parameter to configuration generation functions

### Phase 3: Result Tracking and Validation

#### 3.1 Results Schema Extension
Update experiment results JSON to include:
```json
{
  "experiment_metadata": {
    "experiment_id": "...",
    "seed_used": 12345,
    "seed_source": "explicit|generated",  // How seed was determined
    "configuration_hash": "abc123...",    // For validation
    "reproducibility_info": {
      "python_version": "3.x.x",
      "random_operations_count": 15,      // Debug info
      "seed_generation_method": "config_hash"
    }
  }
}
```

#### 3.2 Validation Utilities
**File**: `utils/reproducibility_validator.py`
```python
class ReproducibilityValidator:
    """Validate experiment reproducibility."""
    
    @staticmethod
    def compare_experiment_results(result1: dict, result2: dict) -> bool:
        """Compare two experiment results for reproducibility."""
    
    @staticmethod
    def extract_deterministic_elements(results: dict) -> dict:
        """Extract elements that should be identical between runs."""
```

### Phase 4: Testing and Documentation

#### 4.1 Reproducibility Tests
**File**: `tests/unit/test_reproducibility.py`
- Test seed generation from configurations
- Test identical results with same seed
- Test different results with different seeds

**File**: `tests/integration/test_experiment_reproducibility.py`
- Full experiment reproducibility test
- Cross-validation of results with same seed
- Performance impact testing

#### 4.2 Configuration Examples
Create example configurations demonstrating reproducibility:
- `config/reproducible_example.yaml`
- `config/seed_generation_example.yaml`

## Code Changes by Module

### 1. Configuration System (`config/models.py`)
```python
@dataclass
class ExperimentConfiguration:
    # ... existing fields ...
    seed: Optional[int] = None
    
    def get_effective_seed(self) -> int:
        """ALWAYS return a seed for this experiment (specified or generated)."""
        if self.seed is not None:
            return self.seed
        # ALWAYS generate a seed when not specified
        return SeedManager.generate_seed_from_config(self)
```

### 2. Experiment Manager (`core/experiment_manager.py`)
```python
async def run_complete_experiment(self) -> dict:
    # ALWAYS initialize reproducibility for every experiment
    effective_seed = self.config.get_effective_seed()
    SeedManager.set_experiment_seed(effective_seed)
    
    # Log seed information (always present)
    seed_source = "explicit" if self.config.seed else "generated"
    self.logger.info(f"Experiment seed: {effective_seed} ({seed_source})")
    
    # ... existing experiment logic ...
    
    # ALWAYS include seed in results (mandatory)
    results["experiment_metadata"]["seed_used"] = effective_seed
    results["experiment_metadata"]["seed_source"] = seed_source
```

### 3. All Random Operations
Replace direct `random` calls with seeded operations:
```python
# Before
random.shuffle(participant_indices)
random.choice(distributions)
random.uniform(0.5, 2.0)

# After (no change needed - Python's random module uses global seed)
# But add logging where appropriate:
self.logger.debug(f"Using seed-controlled random operation: shuffle")
random.shuffle(participant_indices)
```

## Configuration Changes

### YAML Schema Extension
```yaml
# Optional seed specification - if provided, used exactly
seed: 12345

# If seed omitted, ALWAYS auto-generated from config
# Every experiment is reproducible regardless

# Example 1: Explicit seed
language: "English"
seed: 42  # Reproducible with this exact seed
agents:
  - name: "Agent_1"
    personality: "Analytical and methodical"
    model: "gpt-4.1-mini"
    temperature: 0.7
    memory_character_limit: 50000
    reasoning_enabled: true
utility_agent_model: "gpt-4.1-mini"
phase2_rounds: 20
distribution_range_phase1: [0.5, 2.0]
distribution_range_phase2: [0.5, 2.0]

# Example 2: Auto-generated seed (same config = same seed)
language: "English"
# No seed field = deterministic generation from config
agents: [...]  # Same as above
# Results in reproducible experiment with config-generated seed
```

### Command Line Interface Updates
```bash
# Run with explicit seed (overrides config)
python main.py config/my_config.yaml --seed 12345

# Run with config seed (or auto-generated if none specified)
python main.py config/my_config.yaml
# ^ ALWAYS reproducible - every run has a seed

# All experiments now include seed in results for reproduction
```

## Testing Strategy

### Unit Tests
1. **Seed Generation Tests**
   - Same configuration generates same seed
   - Different configurations generate different seeds
   - Explicit seeds are preserved

2. **Randomness Control Tests**
   - Same seed produces identical sequences
   - Different seeds produce different sequences
   - All random operations are seeded

### Integration Tests
1. **Full Experiment Reproducibility**
   - Run same configuration twice with same seed
   - Verify identical results (excluding timestamps)
   - Test with multiple seed values

2. **Cross-Validation Tests**
   - Run experiments with known seeds
   - Validate deterministic behavior
   - Test Original Values Mode compatibility

### Performance Tests
1. **Seed Impact Assessment**
   - Measure overhead of seed management
   - Ensure no performance degradation
   - Validate memory usage unchanged

## Expected Benefits

### 1. Complete Reproducibility
- **Identical runs**: Same configuration + same seed = identical results
- **Debugging capability**: Reproduce specific experiment conditions
- **Research validation**: Peers can reproduce exact experimental conditions

### 2. Controlled Variability
- **Systematic exploration**: Use different seeds to explore parameter space
- **Statistical analysis**: Generate multiple reproducible runs for robust statistics
- **Baseline establishment**: Create reference experiments with known seeds

### 3. Enhanced Experimental Design
- **A/B testing**: Compare different configurations with controlled randomness
- **Sensitivity analysis**: Test impact of randomness on conclusions
- **Publication support**: Provide seeds for academic reproducibility

### 4. Backward Compatibility
- **Existing configs work**: No modification required for current configurations
- **Mandatory reproducibility**: All experiments are now reproducible (not optional)
- **Seamless transition**: Users get reproducibility automatically
- **Gradual adoption**: Can be implemented incrementally while maintaining compatibility

## Implementation Priority

### High Priority (Week 1)
1. Create `SeedManager` utility class
2. Update `ExperimentConfiguration` with seed field
3. Integrate seed initialization in `ExperimentManager`

### Medium Priority (Week 2)
1. Update all modules using random operations
2. Add seed tracking to experiment results
3. Create basic reproducibility tests

### Low Priority (Week 3)
1. Add command-line seed support
2. Create reproducibility validation utilities
3. Write comprehensive documentation

## Risk Mitigation

### Potential Issues
1. **Third-party randomness**: Some libraries may not use Python's random module
2. **Async timing effects**: Race conditions could affect reproducibility
3. **Platform differences**: Different OS/Python versions might behave differently

### Mitigation Strategies
1. **Audit dependencies**: Identify and control all randomness sources
2. **Sequential execution**: Ensure deterministic order in async operations
3. **Version pinning**: Document Python and library version requirements

## Success Metrics

### Technical Metrics
- **100% reproducibility**: Identical results with same seed across runs
- **Zero performance impact**: No measurable overhead from seed management
- **Complete coverage**: All random operations under seed control

### Usability Metrics
- **Simple configuration**: Single `seed` field enables reproducibility
- **Clear documentation**: Users can easily understand and use feature
- **Backward compatibility**: Existing experiments continue to work unchanged

---

## Implementation Checklist

- [ ] Create `utils/seed_manager.py` with `SeedManager` class
- [ ] Update `config/models.py` with optional seed field
- [ ] Modify `core/experiment_manager.py` for seed initialization
- [ ] Update `core/phase2_manager.py` random operations
- [ ] Update `core/distribution_generator.py` random operations
- [ ] Update `utils/experiment_runner.py` random operations
- [ ] Extend experiment results schema with seed metadata
- [ ] Create reproducibility unit tests
- [ ] Create reproducibility integration tests
- [ ] Update documentation with reproducibility examples
- [ ] Create example configurations with seeds
- [ ] Add command-line seed support to `main.py`
- [ ] Validate Original Values Mode compatibility
- [ ] Performance testing and validation

This implementation will provide complete experimental reproducibility while maintaining the system's existing functionality and performance characteristics.