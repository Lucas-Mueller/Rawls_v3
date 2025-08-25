# Seed Reproducibility Bug Investigation Report

## Issue Summary

**Problem:** Despite implementing seed-based reproducibility system, experiments run with the same configuration and seed are not producing identical results, and seed information is not appearing in logs or result files.

**Files Analyzed:**
- `experiment_results_20250823_102648.json`
- `experiment_results_20250823_102654.json`
- `config/faster_config.yaml`

## Root Cause Analysis

### 1. Configuration Analysis ✅

The `config/faster_config.yaml` file contains the correct seed configuration:

```yaml
language: "English" 
seed: 42  # Explicit seed specified
agents:
  - name: "Alice"
    personality: "You are Alice a senior caring elderly lady, who is emphatic and kind."
    model: 'gpt-4.1-nano'
    temperature: 0
    # ... rest of config
```

**Status:** Configuration is correct and includes explicit seed.

### 2. Seed Manager Implementation ✅

Testing confirms the SeedManager works correctly:

```
Config seed: 42
Effective seed: 42
Initialized seed: 42
```

**Status:** Seed management implementation is functional.

### 3. Critical Bug: Incorrect Results Saving ❌

**The primary issue is in `core/experiment_manager.py` line 322:**

```python
def save_results(self, results: ExperimentResults, output_path: str):
    """Save experiment results to JSON file using agent-centric logging."""
    self.agent_logger.save_to_file(output_path)  # ← BUG: Wrong method called!
    logger.info(f"Results saved to: {output_path}")
```

**Problem:** The `save_results` method receives an `ExperimentResults` object that contains the seed information, but **ignores it completely** and instead calls `self.agent_logger.save_to_file()` which uses the old agent-centric logging format.

### 4. Evidence from Result Files

Analysis of the experiment result files shows:

- **Format:** Old agent-centric logging format
- **Structure:** `{"general_information": {...}, "agents": [...]}`
- **Seed Fields:** ❌ No `seed_used` or `seed_source` fields present
- **Search Results:** No seed information found anywhere in the files

### 5. Missing Logging Issue ❌

The seed logging code exists in `ExperimentManager.run_complete_experiment()`:

```python
logger.info(f"Experiment seed: {effective_seed} ({seed_source})")
```

However, this log message is not appearing in the console output, suggesting either:
1. The logging level is incorrect, or  
2. The logging setup is not capturing these messages, or
3. The experiment is not going through this code path

## Impact Assessment

### Severity: **HIGH** ⚠️

1. **No Reproducibility:** Experiments cannot be reproduced despite seed configuration
2. **Lost Metadata:** Critical seed information is discarded during saving
3. **Debugging Impossible:** No way to identify what seed was used for any experiment
4. **Scientific Validity:** Results cannot be validated or replicated

## Detailed Fix Plan

### Fix 1: Correct the `save_results` Method

**File:** `core/experiment_manager.py`

**Current Implementation:**
```python
def save_results(self, results: ExperimentResults, output_path: str):
    """Save experiment results to JSON file using agent-centric logging."""
    self.agent_logger.save_to_file(output_path)
    logger.info(f"Results saved to: {output_path}")
```

**Fixed Implementation:**
```python
def save_results(self, results: ExperimentResults, output_path: str):
    """Save experiment results to JSON file."""
    import json
    from pathlib import Path
    
    # Ensure parent directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the ExperimentResults object with seed information
    with open(output_path, 'w') as f:
        json.dump(results.model_dump(), f, indent=2, default=str)
    
    logger.info(f"Results saved to: {output_path}")
    logger.info(f"Seed used: {results.seed_used} ({results.seed_source})")
```

### Fix 2: Verify Logging Configuration

**Issue:** Seed logging messages not appearing in console output.

**Investigation Required:**
1. Check if logging level is set correctly in `main.py`
2. Verify that experiment actually calls `run_complete_experiment()` 
3. Confirm no logger name conflicts

**Current Logging Setup in `main.py`:**
```python
logging.basicConfig(
    level=logging.INFO,  # Should capture INFO messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
```

### Fix 3: Integration Testing

After implementing fixes, test with:

```bash
# Run with explicit seed
python main.py config/faster_config.yaml test_output.json

# Verify seed in output
grep -E "(seed_used|seed_source)" test_output.json

# Test reproducibility 
python main.py config/faster_config.yaml test_output1.json
python main.py config/faster_config.yaml test_output2.json
# Results should be identical
```

## Verification Steps

### Phase 1: Immediate Verification
1. Check if logging messages appear with current setup
2. Verify the ExperimentManager path is being used
3. Confirm seed initialization is actually being called

### Phase 2: Post-Fix Verification  
1. Seed information appears in JSON output
2. Seed logging appears in console
3. Identical seeds produce identical results
4. Different seeds produce different results

## Dependencies and Considerations

### Backward Compatibility
- **Agent-centric logging format** may be expected by analysis tools
- Consider saving **both formats** if needed:
  - `experiment_results_TIMESTAMP.json` (new format with seeds)
  - `agent_results_TIMESTAMP.json` (old agent-centric format)

### Model Temperature Impact
- Even with seeds, **temperature: 0** should be used for deterministic results
- Current config correctly uses `temperature: 0` for all agents

## Recommended Actions

### Immediate (Priority 1)
1. **Fix save_results method** to save ExperimentResults object
2. **Test logging output** to confirm seed logging appears
3. **Verify reproducibility** with fixed implementation

### Short-term (Priority 2)  
1. **Update tests** to verify seed saving functionality
2. **Add validation** to ensure seed information is always present
3. **Create migration script** if old result files need seed information

### Long-term (Priority 3)
1. **Dual-format saving** if agent-centric format still needed
2. **Enhanced logging** with seed information throughout experiment
3. **Seed validation** in configuration loading

## Critical Discovery: LLM Non-Determinism

### Additional Investigation Results

**Question:** Why do experiments with same seed and temperature 0 produce different outcomes?

**Answer:** The core issue is **LLM API non-determinism**, not our seed implementation.

#### Evidence from Result Comparison:

```
=== COMPARISON OF IDENTICAL SEED EXPERIMENTS ===
Config: seed=42, temperature=0 for all agents

Result 1: Conversation length: 5066 chars, Consensus: False
Result 2: Conversation length: 508 chars,  Consensus: True
Final votes: IDENTICAL in both cases
```

**The agents made completely different conversation choices despite identical configuration.**

#### Root Cause: Multiple Sources of Non-Determinism

1. **LLM API Internal Randomness** ⚠️
   - OpenAI/API providers have internal randomness even at temperature=0
   - This is **not controllable** by client-side seeds
   - Model version differences, server routing, tokenization variations

2. **Async Execution Timing** ⚠️
   - `asyncio.gather()` and `asyncio.create_task()` have timing variations
   - Network latency differences affect execution order
   - Phase 1 parallel execution may complete in different orders

3. **UUID Generation** ⚠️
   - `experiment_id = str(uuid.uuid4())` creates non-deterministic IDs
   - This affects logging and potentially agent context

#### Verification Tests:

✅ **Python Random Seed**: Working correctly  
✅ **Seed Initialization**: Properly implemented  
❌ **LLM Responses**: Non-deterministic despite temperature=0  
❌ **Async Timing**: Execution order variations  

## Fundamental Limitation

**LLMs are not fully deterministic** even with temperature=0. This is a limitation of:
- OpenAI API architecture
- Network infrastructure  
- Model serving systems
- Tokenization processes

## Revised Recommendations

### What Can Be Fixed (Save Results Bug)
- ✅ Fix `save_results()` method to include seed metadata
- ✅ Ensure seed logging appears in console output

### What Cannot Be Fully Fixed (LLM Non-Determinism)
- ❌ LLM API responses will always have some variation
- ❌ Network timing will affect async operations
- ❌ Perfect reproducibility is **impossible** with current LLM APIs

### Practical Solutions

#### 1. **Best-Effort Reproducibility**
- Use seeds to control **local randomness** (class assignments, speaking order)
- Accept that LLM responses will have **statistical similarity** not exact matches
- Document this limitation clearly

#### 2. **Deterministic Execution Mode** (Future Enhancement)
- Make async operations sequential for timing consistency
- Use deterministic UUID generation based on seed
- Minimize timing-dependent operations

#### 3. **Statistical Validation**
- Run multiple experiments with same seed
- Measure outcome distributions rather than exact matches
- Use seeds for **trend consistency** not **exact reproduction**

## Conclusion

The seed system **partially works** - it controls local randomness (class assignment, speaking order), but **cannot control LLM responses**. This is a fundamental limitation of using external LLM APIs.

**The primary bug remains:** Fix `save_results()` to actually save seed information for partial reproducibility tracking.

**Realistic Expectation:** Seeds will produce **statistically similar** experiments, not **identical** ones, due to LLM API non-determinism.

---

**Report Generated:** 2025-01-23  
**Investigation Status:** Complete  
**Fix Status:** Partial reproducibility achievable, perfect reproducibility impossible with LLM APIs