# Missing Counterfactual Earnings Information in Voting Memory Updates - Implementation Plan

## Executive Summary

**Problem**: Currently, when agents complete voting in Phase 2, their memory updates only include their own vote and outcome. They are missing crucial counterfactual earnings information showing what they would have earned under each of the other 3 principles they didn't choose. This counterfactual information is properly provided in Phase 1 but is absent from Phase 2 voting memory updates.

**Impact**: Agents lack critical information for making informed final rankings, reducing the quality of their decision-making process.

**Solution**: Enhance the two-stage voting memory update process to include counterfactual earnings information, following the proven Phase 1 pattern for consistency and multi-language support.

## Deep Issue Analysis

### Root Cause Analysis

1. **Phase 1 vs Phase 2 Information Gap**
   - **Phase 1**: Provides rich counterfactual information in `round_content` (lines 457-458 in `phase1_manager.py`)
   - **Phase 2**: Only provides basic vote information without counterfactual earnings

2. **Current Voting Memory Structure**
   - `build_two_stage_voting_complete_delta()` in `utils/memory_content.py` only includes:
     - Personal vote: "Your vote: 3 (Maximizing Average with Floor Constraint) with $13,000 constraint"
     - Process efficiency: "Two-stage process (principle + amount)"
     - Consensus status: "Group consensus: YES/NO"
   - **Missing**: What earnings would have been under principles 1, 2, 4

3. **Architectural Disconnect**
   - CounterfactualsService has proper calculation methods (`calculate_phase2_counterfactuals()`)
   - But TwoStageVotingManager memory updates don't leverage this data
   - Results are calculated later but not included in voting memory updates

### Current Implementation Context

**File: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/two_stage_voting_manager.py`**
- Lines 945-1015: `_update_participant_memory_for_voting_with_consensus()`
- Currently calls `build_two_stage_voting_complete_delta()` without counterfactual data

**File: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/memory_content.py`**
- Lines ~580-680: `build_two_stage_voting_complete_delta()` structure
- Currently includes basic voting info but no earnings analysis

**File: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/counterfactuals_service.py`**
- Lines 188-238: `calculate_phase2_counterfactuals()` - exists but unused in voting
- Lines 224-229: Uses `DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class()`

## Affected Components Analysis

### Primary Files Requiring Changes

1. **`core/two_stage_voting_manager.py`**
   - **Change Required**: Enhance `_update_participant_memory_for_voting_with_consensus()`
   - **Integration Point**: Add counterfactual calculation before memory update
   - **Dependencies**: CounterfactualsService integration

2. **`utils/memory_content.py`**
   - **Change Required**: Extend `build_two_stage_voting_complete_delta()`
   - **New Parameters**: Add counterfactual earnings data
   - **Multilingual**: Ensure proper localization support

3. **`core/distribution_generator.py`**
   - **Status**: Already has required methods - no changes needed
   - **Key Method**: `calculate_alternative_earnings_by_principle_fixed_class()`

### Secondary Files for Reference

4. **`core/phase1_manager.py`**
   - **Reference**: Lines 405-460 show proper counterfactual formatting
   - **Pattern**: Demonstrates multilingual counterfactual table generation

5. **`translations/*.json`**
   - **Assessment**: May need new keys for voting counterfactual formatting
   - **Languages**: English, Spanish, Mandarin support required

## Implementation Strategy

### Phase 1: Data Collection Enhancement

**Objective**: Modify TwoStageVotingManager to calculate and collect counterfactual data during voting.

**Key Changes**:

1. **Enhance TwoStageVotingManager Constructor**
   - Add CounterfactualsService dependency injection
   - Wire counterfactuals service for voting memory updates

2. **Modify `_update_participant_memory_for_voting_with_consensus()`**
   - Calculate counterfactual earnings before memory update
   - Pass counterfactual data to memory content builder
   - Handle both consensus and non-consensus scenarios

**Implementation Details**:

```python
# In TwoStageVotingManager.__init__()
def __init__(self, participants, language_manager, logger, settings, error_handler, utility_agent, memory_service, counterfactuals_service=None):
    # ... existing initialization
    self.counterfactuals_service = counterfactuals_service

# In _update_participant_memory_for_voting_with_consensus()
async def _update_participant_memory_for_voting_with_consensus(self, participant, context, participant_vote, discussion_state, vote_result):
    try:
        # ... existing code ...
        
        # NEW: Calculate counterfactual earnings for this participant
        counterfactual_earnings = None
        if self.counterfactuals_service:
            # Generate distribution set for counterfactual analysis
            from core.distribution_generator import DistributionGenerator
            distribution_set = DistributionGenerator.generate_dynamic_distribution(
                # Use same range as Phase 2 - need config access
                (0.8, 1.2)  # Temporary - should come from config
            )
            
            # Simulate income class assignment for counterfactual calculation
            # Use the same class assignment logic as the main payoff calculation
            probabilities = getattr(self.settings, 'income_class_probabilities', None)
            if probabilities:
                # Simulate class assignment (this matches main payoff logic)
                if self.seed_manager:
                    random_distribution = self.seed_manager.random.choice(distribution_set.distributions)
                else:
                    import random
                    random_distribution = random.choice(distribution_set.distributions)
                
                assigned_class, _ = DistributionGenerator.calculate_payoff(random_distribution, probabilities)
                
                # Calculate counterfactuals using the same class
                counterfactual_earnings = await self.counterfactuals_service.calculate_voting_counterfactuals(
                    distribution_set=distribution_set,
                    assigned_class=assigned_class,
                    participant_vote=participant_vote
                )
        
        # Enhanced memory content with counterfactuals
        memory_content = build_two_stage_voting_complete_delta(
            participant_name=participant_vote.participant_name,
            principle_num=participant_vote.principle_num,
            principle_display_name=principle_display_name,
            constraint_amount=participant_vote.constraint_amount,
            consensus_reached=consensus_reached,
            agreed_principle=agreed_principle,
            total_stages=total_stages,
            total_attempts=total_attempts,
            counterfactual_earnings=counterfactual_earnings,  # NEW PARAMETER
            language_manager=self.language_manager
        )
        
        # ... rest of existing code ...
    except Exception as e:
        # ... existing error handling ...
```

### Phase 2: Memory Content Enhancement

**Objective**: Extend memory content builder to include counterfactual information following Phase 1 patterns.

**Key Changes**:

1. **Enhance `build_two_stage_voting_complete_delta()`**
   - Add `counterfactual_earnings` parameter
   - Format counterfactual table using Phase 1 patterns
   - Maintain multilingual support

**Implementation Details**:

```python
def build_two_stage_voting_complete_delta(
    participant_name: str,
    principle_num: int,
    principle_display_name: str,
    constraint_amount: Optional[int] = None,
    consensus_reached: bool = False,
    agreed_principle: Optional[str] = None,
    total_stages: int = 1,
    total_attempts: int = 1,
    counterfactual_earnings: Optional[Dict[str, float]] = None,  # NEW PARAMETER
    language_manager: Optional[LanguageManager] = None
) -> str:
    """
    Build memory content for complete two-stage voting process with counterfactual earnings.
    """
    # ... existing code for basic voting info ...
    
    # NEW: Add counterfactual earnings information (following Phase 1 pattern)
    if counterfactual_earnings:
        if language_manager:
            counterfactual_header = language_manager.get('memory.voting_counterfactuals.header')
        else:
            counterfactual_header = "Alternative earnings under each principle:"
        
        delta_parts.append(f"\n{counterfactual_header}")
        
        # Format earnings table (following phase1_manager.py pattern)
        principle_names = {
            'maximizing_floor': language_manager.get('common.principle_names.maximizing_floor') if language_manager else 'Maximizing Floor Income',
            'maximizing_average': language_manager.get('common.principle_names.maximizing_average') if language_manager else 'Maximizing Average Income',
            'maximizing_average_floor_constraint': language_manager.get('common.principle_names.maximizing_average_floor_constraint') if language_manager else 'Maximizing Average with Floor Constraint',
            'maximizing_average_range_constraint': language_manager.get('common.principle_names.maximizing_average_range_constraint') if language_manager else 'Maximizing Average with Range Constraint'
        }
        
        for principle_key, earnings in counterfactual_earnings.items():
            principle_name = principle_names.get(principle_key, principle_key)
            # Format as income and payoff (matching Phase 1 pattern)
            income = int(earnings * 10000)  # Convert payoff back to income
            delta_parts.append(f"{principle_name:<40} ${income:,} ${earnings:.2f}")
    
    return " | ".join(delta_parts)
```

### Phase 3: CounterfactualsService Integration

**Objective**: Add specialized method for calculating counterfactuals during voting process.

**Key Changes**:

1. **Add `calculate_voting_counterfactuals()` method to CounterfactualsService**
   - Specialized for voting context
   - Handles distribution generation for counterfactual analysis
   - Returns properly formatted counterfactual data

**Implementation Details**:

```python
# In CounterfactualsService
async def calculate_voting_counterfactuals(
    self,
    distribution_set,
    assigned_class: IncomeClass,
    participant_vote
) -> Dict[str, float]:
    """
    Calculate counterfactual earnings for voting memory updates.
    
    This method calculates what the participant would have earned under
    each of the 4 principles using their assigned income class.
    
    Args:
        distribution_set: Generated distribution set for analysis
        assigned_class: The participant's assigned income class
        participant_vote: ParticipantVote object with constraint info
        
    Returns:
        Dict mapping principle keys to alternative earnings
    """
    try:
        # Use constraint amount from participant's vote if available
        constraint_amount = participant_vote.constraint_amount
        
        # Delegate to existing proven method
        alternative_earnings = DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class(
            distribution_set.distributions,
            assigned_class,
            constraint_amount
        )
        
        self.logger.debug(f"Voting counterfactuals calculated for {participant_vote.participant_name}")
        return alternative_earnings
        
    except Exception as e:
        self.logger.warning(f"Failed to calculate voting counterfactuals: {e}")
        # Return empty dict to avoid blocking the voting process
        return {}
```

### Phase 4: Translation Support

**Objective**: Ensure proper multilingual support for counterfactual information.

**Key Changes**:

1. **Add translation keys to all language files**
   - `memory.voting_counterfactuals.header`
   - Reuse existing principle name translations
   - Follow Phase 1 formatting patterns

**Translation Keys to Add**:

```json
// In translations/english_prompts.json
{
  "memory": {
    "voting_counterfactuals": {
      "header": "Alternative earnings under each principle:"
    }
  }
}

// Similar entries for spanish_prompts.json and mandarin_prompts.json
```

## Technical Considerations

### Architecture Decisions

1. **Service Integration Pattern**
   - Follow existing CounterfactualsService integration pattern
   - Maintain dependency injection approach
   - Preserve service boundaries and responsibilities

2. **Data Flow Consistency**
   - Use same distribution generation logic as main payoff calculation
   - Maintain consistency with Phase 1 counterfactual calculations
   - Preserve income class assignment logic

3. **Error Handling Strategy**
   - Graceful degradation if counterfactual calculation fails
   - Don't block voting process for counterfactual errors
   - Log warnings but continue with basic voting information

### Performance Considerations

1. **Distribution Generation**
   - Reuse distribution generation logic from CounterfactualsService
   - Consider caching generated distributions if performance becomes an issue
   - Minimal impact on voting process timing

2. **Memory Update Efficiency**
   - Counterfactual calculation adds minimal computational overhead
   - Memory content building remains efficient
   - No significant increase in memory size

### Backward Compatibility

1. **Optional Parameter Design**
   - `counterfactual_earnings` parameter is optional in memory content builder
   - Existing calls continue to work without modification
   - Graceful fallback to current behavior if data unavailable

2. **Service Integration**
   - CounterfactualsService dependency is optional in TwoStageVotingManager
   - Existing initialization continues to work
   - Feature activates only when service is provided

## Testing Strategy

### Unit Testing Requirements

1. **TwoStageVotingManager Testing**
   - Test counterfactual calculation integration
   - Test memory update with and without counterfactual data
   - Test error handling for failed counterfactual calculations

2. **Memory Content Builder Testing**
   - Test enhanced `build_two_stage_voting_complete_delta()` 
   - Test multilingual counterfactual formatting
   - Test optional parameter handling

3. **CounterfactualsService Testing**
   - Test new `calculate_voting_counterfactuals()` method
   - Test integration with existing calculation methods
   - Test error handling and edge cases

### Integration Testing Requirements

1. **End-to-End Voting Process**
   - Test complete voting process with counterfactual information
   - Verify memory updates include proper counterfactual data
   - Test both consensus and non-consensus scenarios

2. **Multilingual Testing**
   - Test counterfactual information in English, Spanish, Mandarin
   - Verify proper translation key usage
   - Test formatting consistency across languages

3. **Service Integration Testing**
   - Test TwoStageVotingManager + CounterfactualsService integration
   - Test proper dependency injection and service coordination
   - Test graceful degradation when service unavailable

### Validation Testing

1. **Information Accuracy**
   - Verify counterfactual earnings match Phase 1 calculation patterns
   - Test income class assignment consistency
   - Validate earnings calculations against expected values

2. **Memory Content Quality**
   - Verify enhanced memory content includes all necessary information
   - Test readability and formatting of counterfactual information
   - Validate consistent information presentation

## Risk Assessment

### Implementation Risks

1. **Service Integration Complexity**
   - **Risk**: Complex dependency injection between TwoStageVotingManager and CounterfactualsService
   - **Mitigation**: Follow existing service integration patterns, thorough testing

2. **Memory Content Format Changes**
   - **Risk**: Changes to memory content format could affect agent understanding
   - **Mitigation**: Follow proven Phase 1 patterns, maintain consistent formatting

3. **Performance Impact**
   - **Risk**: Additional calculations could slow down voting process
   - **Mitigation**: Minimal computational overhead, async processing, error handling

### Operational Risks

1. **Translation Completeness**
   - **Risk**: Missing or incorrect translations could break multilingual support
   - **Mitigation**: Comprehensive translation testing, fallback to English

2. **Backward Compatibility**
   - **Risk**: Changes could break existing voting functionality
   - **Mitigation**: Optional parameter design, thorough regression testing

3. **Error Propagation**
   - **Risk**: Counterfactual calculation errors could break voting process
   - **Mitigation**: Graceful error handling, continue with basic information

## Timeline Estimation

### Phase 1: Core Implementation (2-3 days)
- TwoStageVotingManager enhancement: 1 day
- CounterfactualsService method addition: 0.5 day
- Memory content builder enhancement: 1 day
- Unit testing: 0.5 day

### Phase 2: Integration and Translation (1-2 days)
- Service integration testing: 0.5 day
- Translation key additions: 0.5 day
- Multilingual testing: 1 day

### Phase 3: Validation and Testing (1-2 days)
- End-to-end testing: 1 day
- Performance validation: 0.5 day
- Documentation and cleanup: 0.5 day

**Total Estimated Timeline: 4-7 days**

## Dependencies and Prerequisites

### Technical Dependencies
1. **Existing CounterfactualsService** - Already implemented and functional
2. **TwoStageVotingManager** - Current implementation stable
3. **Phase 1 Counterfactual Methods** - Pattern to follow exists and works
4. **Translation System** - Infrastructure exists for multilingual support

### Configuration Dependencies
1. **Phase2Settings** - Access to income class probabilities and distribution ranges
2. **ExperimentConfiguration** - Consistent with existing configuration patterns
3. **Language Manager** - Existing multilingual support framework

### Testing Dependencies
1. **Existing Test Framework** - Build on current testing infrastructure
2. **Mock Services** - For isolated unit testing
3. **Integration Test Environment** - For end-to-end validation

## Success Criteria

### Functional Success Criteria
1. **Information Completeness**: Agents receive counterfactual earnings for all 4 principles in voting memory updates
2. **Consistency**: Counterfactual information matches Phase 1 formatting and calculation patterns
3. **Multilingual Support**: Proper localization in English, Spanish, and Mandarin
4. **Process Integration**: Seamless integration with existing two-stage voting process

### Quality Success Criteria
1. **Accuracy**: Counterfactual calculations match expected values and Phase 1 patterns
2. **Reliability**: No errors or failures in counterfactual calculation or memory updates
3. **Performance**: No significant impact on voting process timing
4. **Maintainability**: Clean code integration following existing architectural patterns

### User Experience Success Criteria
1. **Information Richness**: Agents have complete information for informed final rankings
2. **Clarity**: Counterfactual information is clearly formatted and understandable
3. **Consistency**: Information presentation matches Phase 1 user experience
4. **Language Support**: Proper localization maintains user experience quality

## Conclusion

This implementation plan addresses the critical gap in counterfactual earnings information during Phase 2 voting memory updates. By following proven Phase 1 patterns and leveraging existing CounterfactualsService infrastructure, we can enhance the voting process to provide agents with the complete information they need for informed decision-making.

The solution maintains backward compatibility, supports multilingual environments, and integrates cleanly with the existing services-first architecture. The estimated 4-7 day implementation timeline includes comprehensive testing and validation to ensure quality and reliability.

Key benefits of this enhancement:
- **Improved Decision Quality**: Agents have complete counterfactual information for final rankings
- **Consistency**: Phase 1 and Phase 2 provide equivalent information transparency
- **Architectural Integrity**: Clean integration with existing service patterns
- **Multilingual Support**: Maintains quality user experience across languages
- **Maintainability**: Follows established code patterns and service boundaries