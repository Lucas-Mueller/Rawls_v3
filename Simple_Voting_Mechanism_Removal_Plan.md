# Simple Voting Mechanism Removal Plan

## Overview

This document provides a comprehensive plan to remove the simple voting mechanism from the Phase 2 system, maintaining only the complex (two-stage formal voting) mechanism. The simple voting mechanism uses preference-based consensus detection through "My preference is..." statements, while the complex mechanism uses structured formal voting initiated with "Let's vote" triggers.

## Executive Summary

The simple voting mechanism is deeply embedded across multiple subsystems:

- **Configuration System**: `voting_detection_mode` configuration parameter
- **Phase2Manager**: Core voting logic with branching code paths
- **UtilityAgent**: Preference detection and consensus validation
- **Test Suite**: Comprehensive test coverage for simple mode
- **Logging/Tracing**: Voting mode tracking and statistics
- **Translation System**: Simple mode prompts and instructions
- **Experiment Orchestration**: Mode validation and configuration handling

## Impact Analysis

### Systems Affected
1. **Core Logic**: Phase 2 consensus detection and validation
2. **Configuration**: Voting mode settings and validation
3. **User Interface**: Experiment prompts and instructions
4. **Testing**: Unit and integration tests
5. **Logging**: Vote tracking and analysis
6. **Documentation**: User guides and API documentation

### Breaking Changes
- Configuration files using `voting_detection_mode: "simple"` will become invalid
- Experiments relying on preference-based consensus will fail
- All simple mode tests will become obsolete
- Logging schemas will change (voting mode tracking)

## Detailed Removal Plan

### Phase 1: Configuration System Changes

#### 1.1 Update Configuration Models
**File**: `config/models.py`
**Lines**: 76, 111-118

**Changes Required**:
- Remove `voting_detection_mode` field from `ExperimentConfiguration`
- Remove `validate_voting_detection_mode()` validator
- Update class documentation

**Implementation**:
```python
# REMOVE these lines:
voting_detection_mode: str = Field("simple", description="Voting detection mode: 'simple' or 'complex'")

@field_validator('voting_detection_mode')
@classmethod
def validate_voting_detection_mode(cls, v):
    """Validate voting detection mode is supported."""
    valid_modes = ["simple", "complex"]
    if v not in valid_modes:
        raise ValueError(f"Invalid voting detection mode: {v}. Must be one of {valid_modes}")
    return v
```

#### 1.2 Update Default Configuration
**File**: `config/default_config.yaml`
**Line**: 30

**Changes Required**:
- Remove `voting_detection_mode: "complex"` line
- Update comments referencing voting modes

#### 1.3 Update Phase2Settings
**File**: `config/phase2_settings.py` 
**Lines**: 118-133

**Changes Required**:
- Remove two-stage voting settings (now always enabled)
- Clean up voting-related configuration options

### Phase 2: Core Phase2Manager Changes

#### 2.1 Remove Simple Mode Logic
**File**: `core/phase2_manager.py`
**Lines**: 412-414, 550-603, 1225-1238

**Changes Required**:
- Remove `_current_round_preferences` tracking
- Remove simple mode conditional branches
- Remove preference-based consensus checking
- Simplify prompt building logic
- Remove simple mode initialization

**Key Sections to Remove**:
```python
# Remove simple mode initialization (lines 412-414)
if config.voting_detection_mode == "simple":
    self._current_round_preferences = {}

# Remove entire simple mode consensus logic (lines 550-603)
elif config.voting_detection_mode == "simple":
    # ... entire preference detection block

# Remove simple mode prompt logic (lines 1233-1238)
else:
    # For simple mode: use preference-based consensus
    base_prompt = language_manager.get("prompts.phase2_discussion_prompt_simple", ...)
```

#### 2.2 Simplify Voting Logic
**Changes Required**:
- Always use complex voting mode logic
- Remove mode-based conditional statements
- Simplify discussion prompt building

### Phase 3: UtilityAgent Changes

#### 3.1 Remove Preference Detection Methods
**File**: `experiment_agents/utility_agent.py`
**Lines**: 1102, 1708, 1743

**Changes Required**:
- Remove `detect_preference_statement()` method
- Remove `_detect_preference_via_llm()` method  
- Remove `check_preference_consensus_simple_mode()` method
- Remove deprecated `check_preference_consensus()` method

#### 3.2 Clean Up Utility Agent Dependencies
**Changes Required**:
- Remove preference-related imports and utilities
- Remove constraint amount extraction for preferences
- Clean up LLM parsing prompts

### Phase 4: Test Suite Updates

#### 4.1 Remove Simple Mode Tests
**Files to Remove**:
- `tests/unit/test_phase2_preference_detection_simple_mode.py`
- Any test files specifically testing simple mode functionality

#### 4.2 Update Integration Tests
**Files**: `tests/integration/test_*.py`
**Changes Required**:
- Remove simple mode test configurations
- Update test fixtures to use only complex mode
- Remove simple mode validation tests

#### 4.3 Update Test Configurations
**Files**: `tests/fixtures/configs/test_*.yaml`
**Changes Required**:
- Remove `voting_detection_mode: "simple"` from all test configs
- Update test documentation

### Phase 5: Translation System Updates

#### 5.1 Remove Simple Mode Prompts
**File**: `translations/english_prompts.json`
**Lines**: 30, 42, 49

**Changes Required**:
- Remove `phase2_discussion_prompt_simple` prompt
- Remove `utility_preference_detection` prompt
- Remove `utility_llm_parse_preference_statement` prompt
- Update complex mode prompts to be the default

#### 5.2 Update Other Language Files
**Files**: `translations/spanish_prompts.json`, `translations/mandarin_prompts.json`
**Changes Required**:
- Remove simple mode prompts from all language files
- Ensure consistency across translations

### Phase 6: Logging and Tracing Updates

#### 6.1 Update Logging Types
**File**: `models/logging_types.py`
**Lines**: 92, 120, 129

**Changes Required**:
- Remove voting mode tracking from log structures
- Update vote type documentation
- Remove preference-related logging fields

#### 6.2 Update Agent-Centric Logger
**File**: `utils/agent_centric_logger.py`
**Line**: 276-279

**Changes Required**:
- Remove `initialize_voting_history()` voting mode parameter
- Remove voting mode from log initialization
- Update logging documentation

### Phase 7: Experiment Orchestration Updates

#### 7.1 Update Main Entry Point
**File**: `main.py`
**Lines**: 90, 92-94, 99-100

**Changes Required**:
- Remove voting mode validation
- Remove simple mode logging messages
- Remove mode-specific configuration checks

#### 7.2 Update Experiment Manager
**File**: `core/experiment_manager.py`
**Line**: 158

**Changes Required**:
- Remove voting detection mode from experiment metadata
- Update experiment configuration building

### Phase 8: Documentation Updates

#### 8.1 Update CLAUDE.md
**File**: `CLAUDE.md`
**Lines**: References to simple/complex modes

**Changes Required**:
- Update voting system documentation
- Remove simple mode descriptions
- Update configuration examples

#### 8.2 Update README and Guides
**Changes Required**:
- Update user documentation
- Remove simple mode configuration examples
- Update API documentation

### Phase 9: Configuration Migration

#### 9.1 Update Hypothesis Testing Configs
**Files**: `hypothesis_testing/**/*.yaml`
**Changes Required**:
- Remove `voting_detection_mode` from all hypothesis testing configurations
- Validate all configurations still work

#### 9.2 Update Example Configurations
**Changes Required**:
- Update all example configurations
- Remove references to simple mode
- Provide migration guidance for users

## Implementation Strategy

### Recommended Implementation Order

1. **Configuration System** (Phase 1) - Foundation changes
2. **Core Logic** (Phase 2) - Remove simple voting logic
3. **Utility Agent** (Phase 3) - Remove preference detection
4. **Translation System** (Phase 5) - Update prompts
5. **Test Suite** (Phase 4) - Update/remove tests
6. **Logging** (Phase 6) - Update tracking systems
7. **Orchestration** (Phase 7) - Update experiment management
8. **Documentation** (Phase 8) - Update all documentation
9. **Configuration Migration** (Phase 9) - Migrate existing configs

### Risk Mitigation

#### Backup Strategy
- Create feature branch: `remove-simple-voting`
- Tag current state before beginning: `v3-with-simple-voting`
- Maintain rollback capability during implementation

#### Testing Strategy
1. Run full test suite before starting
2. Implement changes incrementally with testing at each step
3. Focus on complex mode functionality validation
4. Test configuration loading and validation
5. Verify experiment end-to-end functionality

#### Validation Checklist
- [ ] All tests pass with only complex mode
- [ ] Configuration validation works correctly
- [ ] Experiment orchestration functions properly
- [ ] Logging and tracing capture voting events
- [ ] Translation system provides correct prompts
- [ ] Documentation reflects current functionality

## Breaking Changes Documentation

### Configuration Changes
```yaml
# OLD - No longer supported
voting_detection_mode: "simple"  # INVALID

# NEW - Implicit complex mode (no configuration needed)
# Complex voting mode is now the only supported mode
```

### API Changes
- Remove `UtilityAgent.detect_preference_statement()`
- Remove `UtilityAgent.check_preference_consensus_simple_mode()`
- Remove `Phase2Manager._current_round_preferences` attribute
- Remove simple mode prompts from translation system

### Behavioral Changes
- Phase 2 will only support formal two-stage voting
- Preference statements like "My preference is..." will not trigger consensus
- All experiments will use structured voting with "Let's vote" triggers

## Post-Removal Cleanup

### Code Quality Improvements
1. Remove unused imports related to preference detection
2. Simplify Phase2Manager logic flow
3. Consolidate voting-related utility methods
4. Update type hints and documentation

### Performance Optimizations
1. Remove unused preference tracking overhead
2. Simplify consensus detection logic
3. Reduce conditional branching in hot paths

## Testing and Validation Plan

### Pre-Removal Testing
1. Document current simple mode behavior
2. Create test cases for complex mode equivalency
3. Validate all hypothesis testing configurations

### During Removal Testing
1. Test each phase independently
2. Maintain integration test coverage
3. Validate configuration loading at each step

### Post-Removal Testing
1. Full regression test suite
2. End-to-end experiment validation
3. Performance benchmarking
4. Configuration migration testing

## Migration Guide for Users

### Configuration Updates Required
1. Remove `voting_detection_mode` from all YAML files
2. Update experiment documentation
3. Retrain on complex voting procedures

### Behavioral Changes Expected
1. Experiments will require explicit voting initiation
2. Consensus through preferences no longer supported  
3. All voting will follow two-stage formal process

## Conclusion

This comprehensive removal plan ensures systematic elimination of the simple voting mechanism while maintaining system stability and functionality. The complex voting system will become the sole consensus mechanism, simplifying the codebase and user experience while maintaining robust voting capabilities.

Implementation should follow the phased approach outlined above, with careful testing and validation at each step to ensure system reliability throughout the transition.