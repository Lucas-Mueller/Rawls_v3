# Logging System Migration Plan

## Overview
This document outlines the plan to align the current logging system with the target schema found in `xperiment_data/experiment_results_20250822_151659.json`.

## Current vs Target Schema Analysis

### Missing Fields in Current System

The current `GeneralExperimentInfo` class is missing the following fields that exist in the target schema:

1. **`max_rounds_phase_2`** - Maximum number of rounds allowed in Phase 2
2. **`rounds_conducted_phase_2`** - Actual number of rounds conducted in Phase 2  
3. **`seed_randomness`** - The random seed value used (currently has `seed_used` instead)

### Field Name Inconsistencies

1. Current: `seed_used` → Target: `seed_randomness`
2. Current: `seed_source` → Not present in target (may need to remove or keep for backward compatibility)

### Agent-Level Schema Alignment

The agent-level schema appears to be properly aligned with the target format through the `AgentExperimentLog.to_target_format()` method, which includes:

- Agent metadata (name, model, temperature, personality, reasoning_enabled)
- Phase 1 structure with all required fields
- Phase 2 structure with all required fields
- Memory character limit field (present in current but not in target - may need evaluation)

## Implementation Plan

### Phase 1: Update GeneralExperimentInfo Model

**File:** `models/logging_types.py`

1. **Add missing fields:**
   ```python
   class GeneralExperimentInfo(BaseModel):
       consensus_reached: bool
       consensus_principle: Optional[str] = None
       max_rounds_phase_2: int  # NEW FIELD
       rounds_conducted_phase_2: int  # NEW FIELD
       public_conversation_phase_2: str
       final_vote_results: Dict[str, str]
       config_file_used: str
       seed_randomness: Optional[int] = None  # RENAMED from seed_used
       income_class_probabilities: Optional[Dict[str, float]] = None
       original_values_mode_enabled: Optional[bool] = None
       # Consider keeping seed_source for backward compatibility or remove if not needed
   ```

2. **Update TargetStateStructure.to_dict() method** to use the new field names:
   ```python
   def to_dict(self) -> Dict[str, Any]:
       return {
           "general_information": {
               "consensus_reached": self.general_information.consensus_reached,
               "consensus_principle": self.general_information.consensus_principle,
               "max_rounds_phase_2": self.general_information.max_rounds_phase_2,  # NEW
               "rounds_conducted_phase_2": self.general_information.rounds_conducted_phase_2,  # NEW
               "public_conversation_phase_2": self.general_information.public_conversation_phase_2,
               "final_vote_results": self.general_information.final_vote_results,
               "config_file_used": self.general_information.config_file_used,
               "seed_randomness": self.general_information.seed_randomness,  # RENAMED
               "income_class_probabilities": self.general_information.income_class_probabilities,
               "original_values_mode_enabled": self.general_information.original_values_mode_enabled
           },
           "agents": self.agents
       }
   ```

### Phase 2: Update Data Population Logic

**Files to modify:**
- `utils/agent_centric_logger.py`
- `core/experiment_manager.py` 
- Any other files that create `GeneralExperimentInfo` instances

**Changes needed:**

1. **In agent_centric_logger.py:**
   ```python
   def save_to_file(self, output_path: str, results: ExperimentResults):
       # Extract max_rounds and rounds_conducted from Phase 2 results
       phase2_results = results.phase2_results
       max_rounds = phase2_results.discussion_result.max_rounds if hasattr(phase2_results.discussion_result, 'max_rounds') else None
       rounds_conducted = phase2_results.discussion_result.final_round
       
       general_info = GeneralExperimentInfo(
           consensus_reached=phase2_results.discussion_result.consensus_reached,
           consensus_principle=phase2_results.discussion_result.agreed_principle.principle.value if phase2_results.discussion_result.consensus_reached else None,
           max_rounds_phase_2=max_rounds,  # NEW
           rounds_conducted_phase_2=rounds_conducted,  # NEW
           public_conversation_phase_2=phase2_results.discussion_result.full_conversation,
           final_vote_results=phase2_results.discussion_result.vote_results,
           config_file_used=self.config_file_used,
           seed_randomness=self.seed_used,  # RENAMED
           income_class_probabilities=self.income_class_probabilities,
           original_values_mode_enabled=self.original_values_mode_enabled
       )
   ```

2. **Verify Phase2 result structures contain the needed data:**
   - Check `models/experiment_types.py` for `DiscussionResult` class
   - Ensure `max_rounds` and `final_round` fields are properly tracked

### Phase 3: Update Configuration and Initialization

**Files to check/update:**
- Configuration loading logic to ensure `max_rounds_phase_2` is captured
- Experiment initialization to track round limits
- Phase 2 execution logic to properly record rounds conducted

### Phase 4: Backward Compatibility Considerations

1. **Migration strategy:**
   - Keep old field names as deprecated aliases temporarily
   - Add validation to ensure both old and new field names work
   - Provide migration utility if needed

2. **Testing strategy:**
   - Create test cases comparing output with target schema
   - Validate all existing tests still pass
   - Add integration tests for new fields

### Phase 5: Agent Schema Verification

**Current agent schema appears complete, but verify:**

1. **Check if `memory_character_limit` field should be included in output**
   - Present in current system but not in target
   - Decide whether to include or exclude from final output

2. **Validate all nested structures match target exactly:**
   - Phase 1 ranking structures
   - Phase 2 discussion round structures
   - Memory and bank balance tracking

## Risk Assessment

### Low Risk
- Adding new fields to existing models
- Renaming fields with backward compatibility

### Medium Risk  
- Ensuring Phase 2 execution properly tracks max_rounds and rounds_conducted
- Coordination between multiple files that create logging structures

### High Risk
- Breaking existing experiments or analysis scripts
- Data loss during migration if not handled carefully

## Testing Strategy

1. **Unit Tests:**
   - Test new GeneralExperimentInfo model creation
   - Test TargetStateStructure.to_dict() output format
   - Validate field renaming and backward compatibility

2. **Integration Tests:**
   - Run complete experiment and compare output schema with target
   - Test with various experiment configurations
   - Validate all existing functionality still works

3. **Schema Validation:**
   - Create JSON schema validator comparing output with target
   - Add automated testing to ensure schema compliance

## Implementation Priority

1. **High Priority (Phase 1-2):** Core model updates and data population
2. **Medium Priority (Phase 3-4):** Configuration updates and backward compatibility  
3. **Low Priority (Phase 5):** Agent schema optimization and cleanup

## Success Criteria

1. Generated JSON exactly matches target schema structure
2. All existing tests pass
3. New integration tests validate schema compliance
4. No breaking changes to existing analysis workflows
5. Performance impact is minimal

## Files Requiring Changes

### Primary Changes
- `models/logging_types.py` - Model definitions
- `utils/agent_centric_logger.py` - Data population logic

### Secondary Changes  
- `core/experiment_manager.py` - Experiment coordination
- `models/experiment_types.py` - Phase 2 result structures (if needed)
- Test files - Update for new schema

### Verification
- `tests/integration/test_logging_integration.py` - Schema compliance tests
- `tests/unit/test_agent_centric_logger.py` - Unit test updates