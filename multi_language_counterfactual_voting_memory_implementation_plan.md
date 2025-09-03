# Multi-Language Counterfactual Voting Memory Implementation Plan

## Executive Summary

**Issue**: Currently, when agents complete voting in Phase 2, they receive voting memory updates showing only their own vote and outcome, missing crucial counterfactual information showing what they would have earned under each of the other 3 principles they didn't choose. This issue affects ALL THREE supported languages: English, Spanish, and Mandarin.

**Impact**: Without counterfactual information, agents cannot make informed final rankings since they lack transparency about alternative outcomes, reducing the quality of post-voting decision-making across all language configurations.

**Solution**: Extend the existing two-stage voting memory update process to include multi-language counterfactual earnings information similar to Phase 1's transparency level, ensuring consistent behavior across English, Spanish, and Mandarin experiments.

## Current State Analysis

### Phase 1 Multi-Language Counterfactual Implementation

**Key Finding**: Phase 1 already has excellent multi-language counterfactual support:

1. **Counterfactual Table Generation** (`/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase1_manager.py`, lines 408-427):
   - Uses `language_manager.get("prompts.phase1_counterfactual_table_header")` for localized headers
   - Retrieves principle display names using `language_manager.get("common.principle_names.*")`
   - Formats counterfactuals with income and payoff information in appropriate language

2. **Translation Keys Available**:
   - **English**: `"phase1_counterfactual_table_header": "This assigns you to the following income class: {assigned_class}\n\nFor each principle of justice the following income would be received by each member of this income class. You will receive a payoff of $1 for each $10,000 of income.\n\nPrinciple of Justice                          Income    Payoff"`
   - **Spanish**: `"phase1_counterfactual_table_header": "Esto le asigna a la siguiente clase de ingresos: {assigned_class}\n\nPara cada principio de justicia, cada miembro de esta clase de ingresos recibiría los siguientes ingresos. Recibirá un pago de $1 por cada $10,000 de ingresos.\n\nPrincipio de Justicia                    Ingresos    Pago"`
   - **Mandarin**: `"phase1_counterfactual_table_header": "这将把您分配到以下收入类别：{assigned_class}\n\n对于每个公正原则，该收入类别的每个成员将获得以下收入。每 10 000 美元的收入，您将获得 1 美元的回报。\n\n公正原则收入回报"`

3. **Principle Name Localization**:
   - All three languages have complete `common.principle_names.*` translations
   - English: "Maximizing Floor Income", "Maximizing Average Income", etc.
   - Spanish: "Maximizar los ingresos mínimos", "Maximizar los ingresos promedio", etc.
   - Mandarin: Appropriate Chinese translations available

### Current Voting Memory Update Gap

**Problem Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/two_stage_voting_manager.py`, method `_update_participant_memory_for_voting_with_consensus` (lines 945-1015):

**Current Memory Content** (line 992-1002):
```python
memory_content = build_two_stage_voting_complete_delta(
    participant_name=participant_vote.participant_name,
    principle_num=participant_vote.principle_num,
    principle_display_name=principle_display_name,
    constraint_amount=participant_vote.constraint_amount,
    consensus_reached=consensus_reached,
    agreed_principle=agreed_principle,
    total_stages=total_stages,
    total_attempts=total_attempts,
    language_manager=self.language_manager
)
```

**Missing**: Counterfactual earnings information showing what the agent would have earned under principles 1, 2, 3, and 4.

### CounterfactualsService Multi-Language Support

**Analysis**: The CounterfactualsService already has the infrastructure needed:

1. **Counterfactual Calculation** (`calculate_phase2_counterfactuals`, lines 188-238):
   - Uses `DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class`
   - Returns `Dict[agent_name, Dict[principle_key, earnings]]`
   - Same method as Phase 1 but for Phase 2 distributions

2. **Multi-Language Participant Support** (`_get_participant_language_manager`, lines 311-356):
   - Detects participant language from config
   - Creates participant-specific language managers
   - Supports English, Spanish, Mandarin mapping

3. **Localized Principle Names** (`build_detailed_results`, lines 293-302):
   - Already retrieves localized principle names using `language_manager.get('common.principle_names.*')`

## Implementation Strategy

### Phase 1: Extend Memory Content Builder

**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/memory_content.py`

**Enhancement**: Add counterfactual information to `build_two_stage_voting_complete_delta` function:

1. **Add Parameters**:
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
       # NEW PARAMETERS:
       alternative_earnings: Optional[Dict[str, float]] = None,
       assigned_class: Optional[str] = None,
       language_manager: Optional[LanguageManager] = None
   ) -> str:
   ```

2. **Add Counterfactual Section**:
   - Use existing `phase1_counterfactual_table_header` translation key
   - Format alternative earnings for all 4 principles
   - Use localized principle names from `common.principle_names.*`
   - Maintain same format as Phase 1 for consistency

### Phase 2: Enhance TwoStageVotingManager

**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/two_stage_voting_manager.py`

**Modification**: Update `_update_participant_memory_for_voting_with_consensus` method:

1. **Calculate Counterfactuals** (before line 992):
   ```python
   # Calculate counterfactual earnings for this participant
   alternative_earnings = None
   assigned_class = None
   if self.memory_service and hasattr(self.memory_service, 'counterfactuals_service'):
       # Get Phase 2 distributions and calculate counterfactuals
       alternative_earnings, assigned_class = await self._calculate_voting_counterfactuals(
           participant_vote, discussion_state, vote_result
       )
   ```

2. **Pass to Memory Builder**:
   ```python
   memory_content = build_two_stage_voting_complete_delta(
       participant_name=participant_vote.participant_name,
       principle_num=participant_vote.principle_num,
       principle_display_name=principle_display_name,
       constraint_amount=participant_vote.constraint_amount,
       consensus_reached=consensus_reached,
       agreed_principle=agreed_principle,
       total_stages=total_stages,
       total_attempts=total_attempts,
       alternative_earnings=alternative_earnings,  # NEW
       assigned_class=assigned_class,              # NEW
       language_manager=self.language_manager
   )
   ```

3. **Add Helper Method**:
   ```python
   async def _calculate_voting_counterfactuals(
       self,
       participant_vote: ParticipantVote,
       discussion_state: Any,
       vote_result: Any
   ) -> tuple[Optional[Dict[str, float]], Optional[str]]:
       """
       Calculate counterfactual earnings for voting memory update.
       
       Returns:
           tuple: (alternative_earnings, assigned_class)
       """
       # Implementation details below
   ```

### Phase 3: Integration with CounterfactualsService

**Challenge**: TwoStageVotingManager doesn't currently have access to distribution data or CounterfactualsService.

**Solution Options**:

1. **Option A - Dependency Injection**: Pass CounterfactualsService to TwoStageVotingManager
2. **Option B - Service Discovery**: Access CounterfactualsService through MemoryService
3. **Option C - Direct Integration**: Move counterfactual calculation to Phase2Manager and pass results

**Recommended**: Option B - Service Discovery through MemoryService for minimal coupling:

```python
# In TwoStageVotingManager.__init__:
self.counterfactuals_service = getattr(memory_service, 'counterfactuals_service', None) if memory_service else None

# In _calculate_voting_counterfactuals:
if self.counterfactuals_service and discussion_state and vote_result:
    # Use CounterfactualsService.calculate_phase2_counterfactuals
    # Get distribution_set from discussion_state or vote_result
    # Calculate counterfactuals using existing infrastructure
```

### Phase 4: Translation Key Additions

**Files**: 
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`

**New Keys Needed**:

1. **Voting Counterfactual Header** (if different formatting needed):
   ```json
   "voting_counterfactual_table_header": "Your assigned income class: {assigned_class}\n\nCounterfactual Analysis - What you would have earned under each principle:\n\nPrinciple                                     Income    Earnings"
   ```

2. **Memory Integration Labels**:
   ```json
   "memory": {
       "two_stage": {
           "counterfactual_header": "Counterfactual earnings:",
           "alternative_format": "{principle}: ${earnings:.2f}"
       }
   }
   ```

**Translation Requirements**:
- Spanish equivalents for all new keys
- Mandarin equivalents for all new keys  
- Consistent terminology with existing Phase 1 translations

## Detailed Implementation Steps

### Step 1: Update Memory Content Builder

**Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/utils/memory_content.py`

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
    alternative_earnings: Optional[Dict[str, float]] = None,
    assigned_class: Optional[str] = None,
    language_manager: Optional[LanguageManager] = None
) -> str:
    """
    Build memory content for complete two-stage voting process with counterfactual analysis.
    
    New Args:
        alternative_earnings: Earnings under each principle (same format as Phase 1)
        assigned_class: Assigned income class for counterfactual display
    """
    # Existing implementation...
    
    # NEW: Add counterfactual section if data available
    if alternative_earnings and assigned_class and language_manager:
        try:
            # Use same translation key as Phase 1 for consistency
            class_name_mapping = {
                "high": "HIGH",
                "medium_high": "MEDIUM HIGH", 
                "medium": "MEDIUM",
                "medium_low": "MEDIUM LOW",
                "low": "LOW"
            }
            
            assigned_class_display = class_name_mapping.get(assigned_class, assigned_class.upper())
            
            counterfactual_header = language_manager.get(
                "prompts.phase1_counterfactual_table_header",
                assigned_class=assigned_class_display
            )
            
            delta_parts.append(f"\n{counterfactual_header}")
            
            # Get principle display names
            principle_names = {
                'maximizing_floor': language_manager.get('common.principle_names.maximizing_floor'),
                'maximizing_average': language_manager.get('common.principle_names.maximizing_average'),
                'maximizing_average_with_floor': language_manager.get('common.principle_names.maximizing_average_floor_constraint'),
                'maximizing_average_with_range': language_manager.get('common.principle_names.maximizing_average_range_constraint')
            }
            
            # Format each alternative earning (same as Phase 1)
            for principle_key, earnings in alternative_earnings.items():
                principle_name = principle_names.get(principle_key, principle_key)
                income = int(earnings * 10000)  # Convert earnings back to income
                delta_parts.append(f"{principle_name:<40}  ${income:,}    ${earnings:.2f}")
                
        except Exception as e:
            # Fallback: just mention counterfactuals are available
            if language_manager:
                try:
                    delta_parts.append(language_manager.get("memory.counterfactuals_available"))
                except:
                    delta_parts.append("Counterfactual analysis available")
            else:
                delta_parts.append("Counterfactual analysis available")
    
    return " | ".join(delta_parts)
```

### Step 2: Update TwoStageVotingManager

**Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/two_stage_voting_manager.py`

```python
async def _update_participant_memory_for_voting_with_consensus(
    self, 
    participant: Any, 
    context: Any, 
    participant_vote: ParticipantVote,
    discussion_state: Any,
    vote_result: Any
):
    """Update participant memory with voting experience including counterfactual information."""
    try:
        # Existing code...
        principle_display_name = self._get_principle_display_name(participant_vote.principle_num)
        
        # Calculate total stages and attempts (existing code...)
        total_stages = 1 if participant_vote.constraint_amount is None else 2
        total_attempts = (
            (participant_vote.principle_selection_result.attempts_used if participant_vote.principle_selection_result else 1) +
            (participant_vote.amount_specification_result.attempts_used if participant_vote.amount_specification_result else 0)
        )
        
        # Extract consensus information (existing code...)
        consensus_reached = vote_result.consensus_reached if vote_result else False
        agreed_principle = None
        if consensus_reached and vote_result.agreed_principle:
            # Existing consensus extraction logic...
        
        # NEW: Calculate counterfactual earnings
        alternative_earnings = None
        assigned_class = None
        
        try:
            alternative_earnings, assigned_class = await self._calculate_voting_counterfactuals(
                participant, participant_vote, discussion_state, vote_result
            )
        except Exception as e:
            logger.warning(f"Failed to calculate counterfactuals for {participant.name}: {e}")
            # Continue without counterfactuals rather than failing entire process
        
        # Build memory content with counterfactual information
        memory_content = build_two_stage_voting_complete_delta(
            participant_name=participant_vote.participant_name,
            principle_num=participant_vote.principle_num,
            principle_display_name=principle_display_name,
            constraint_amount=participant_vote.constraint_amount,
            consensus_reached=consensus_reached,
            agreed_principle=agreed_principle,
            total_stages=total_stages,
            total_attempts=total_attempts,
            alternative_earnings=alternative_earnings,  # NEW
            assigned_class=assigned_class,              # NEW
            language_manager=self.language_manager
        )
        
        # Update participant memory (existing code...)
        memory_guidance_style = getattr(self.settings, 'memory_guidance_style', 'narrative') if self.settings else 'narrative'
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            participant, context, memory_content, memory_guidance_style=memory_guidance_style, 
            language_manager=self.language_manager, error_handler=self.error_handler, utility_agent=self.utility_agent
        )
        
        logger.info(f"Updated memory for {participant.name} with counterfactual information")
        
    except Exception as e:
        logger.warning(f"Failed to update memory for {participant.name} after voting: {e}")

async def _calculate_voting_counterfactuals(
    self,
    participant: Any,
    participant_vote: ParticipantVote,
    discussion_state: Any,
    vote_result: Any
) -> tuple[Optional[Dict[str, float]], Optional[str]]:
    """
    Calculate counterfactual earnings for voting memory update.
    
    This method calculates what the participant would have earned under each
    of the 4 justice principles, using the same logic as Phase 1 counterfactuals
    but with Phase 2 distribution data.
    
    Returns:
        tuple: (alternative_earnings_dict, assigned_class_string)
    """
    try:
        # Access CounterfactualsService through memory service or create ad-hoc
        counterfactuals_service = None
        if self.memory_service and hasattr(self.memory_service, 'counterfactuals_service'):
            counterfactuals_service = self.memory_service.counterfactuals_service
        
        if not counterfactuals_service:
            logger.debug("CounterfactualsService not available, skipping counterfactual calculation")
            return None, None
        
        # Get Phase 2 distribution data from discussion_state or vote_result
        # This requires coordination with Phase2Manager to store distribution_set
        distribution_set = None
        if hasattr(discussion_state, 'distribution_set'):
            distribution_set = discussion_state.distribution_set
        elif hasattr(vote_result, 'distribution_set'):
            distribution_set = vote_result.distribution_set
        
        if not distribution_set:
            logger.debug("Distribution set not available, skipping counterfactual calculation")
            return None, None
        
        # Simulate income class assignment for this participant
        # Use same logic as CounterfactualsService.apply_group_principle_and_calculate_payoffs
        from core.distribution_generator import DistributionGenerator
        from models import IncomeClass
        
        # For counterfactual analysis, we need to know what income class this participant
        # would be assigned. Since this is called during voting (before final payoffs),
        # we need to simulate the assignment.
        
        # Option A: Use a consistent assignment based on participant index/name
        # Option B: Use the actual assignment if available from vote_result
        # Option C: Calculate for multiple income classes and show range
        
        # For now, use Option A - consistent assignment
        participant_index = hash(participant.name) % 5  # Map to one of 5 income classes
        income_classes = [IncomeClass.HIGH, IncomeClass.MEDIUM_HIGH, IncomeClass.MEDIUM, 
                         IncomeClass.MEDIUM_LOW, IncomeClass.LOW]
        assigned_class = income_classes[participant_index]
        
        # Calculate alternative earnings using Phase 1 logic
        alternative_earnings = DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class(
            distribution_set.distributions,
            assigned_class,
            participant_vote.constraint_amount
        )
        
        return alternative_earnings, assigned_class.value
        
    except Exception as e:
        logger.warning(f"Error calculating voting counterfactuals for {participant.name}: {e}")
        return None, None
```

### Step 3: Translation Updates

**Add to all three translation files**:

```json
// English
"memory": {
    "two_stage": {
        "counterfactual_header": "Counterfactual Analysis",
        "counterfactuals_available": "Counterfactual earnings analysis included"
    }
}

// Spanish  
"memory": {
    "two_stage": {
        "counterfactual_header": "Análisis Contrafactual", 
        "counterfactuals_available": "Análisis contrafactual de ganancias incluido"
    }
}

// Mandarin
"memory": {
    "two_stage": {
        "counterfactual_header": "反事实分析",
        "counterfactuals_available": "包含反事实收益分析"
    }
}
```

## Data Flow Architecture

### Current Flow (Missing Counterfactuals)
```
TwoStageVotingManager.conduct_full_voting_process
├── Stage 1: Principle Selection (per participant)  
├── Stage 2: Amount Specification (if needed)
├── Create VoteResult with consensus info
└── Update memory with basic voting info (MISSING counterfactuals)
    └── build_two_stage_voting_complete_delta (basic version)
```

### Enhanced Flow (With Counterfactuals)
```
TwoStageVotingManager.conduct_full_voting_process
├── Stage 1: Principle Selection (per participant)
├── Stage 2: Amount Specification (if needed)  
├── Create VoteResult with consensus info
└── Update memory with voting info + counterfactuals
    ├── _calculate_voting_counterfactuals (NEW)
    │   ├── Access distribution_set from discussion_state
    │   ├── Simulate/determine income class assignment
    │   └── Calculate alternative earnings (same as Phase 1)
    └── build_two_stage_voting_complete_delta (enhanced)
        └── Format counterfactual table (same as Phase 1)
```

## Distribution Data Access Strategy

**Challenge**: TwoStageVotingManager doesn't currently have access to the Phase 2 distribution set needed for counterfactual calculations.

**Solution**: Extend discussion_state or vote_result to include distribution data:

### Option 1: Extend GroupDiscussionState
```python
# In models/experiment_types.py or equivalent
@dataclass  
class GroupDiscussionState:
    # existing fields...
    distribution_set: Optional[Any] = None  # Add this field
```

### Option 2: Extend VoteResult  
```python
# In models/principle_types.py or equivalent
@dataclass
class VoteResult:
    # existing fields...
    distribution_set: Optional[Any] = None  # Add this field
```

### Option 3: Pass via Method Parameter
```python
# In TwoStageVotingManager.conduct_full_voting_process
async def conduct_full_voting_process(
    self, 
    contexts: List[Any], 
    discussion_state: Any,
    distribution_set: Optional[Any] = None  # NEW parameter
) -> Optional[Any]:
```

**Recommended**: Option 1 (GroupDiscussionState extension) for cleaner architecture.

## Multi-Language Testing Strategy

### Test Coverage Required

1. **Unit Tests**:
   - `test_build_two_stage_voting_complete_delta_with_counterfactuals_english`
   - `test_build_two_stage_voting_complete_delta_with_counterfactuals_spanish` 
   - `test_build_two_stage_voting_complete_delta_with_counterfactuals_mandarin`

2. **Integration Tests**:
   - `test_voting_memory_update_with_counterfactuals_english`
   - `test_voting_memory_update_with_counterfactuals_spanish`
   - `test_voting_memory_update_with_counterfactuals_mandarin`

3. **End-to-End Tests**:
   - Full voting process in each language with counterfactual verification
   - Memory content validation across languages
   - Final ranking impact assessment

### Test Implementation

**Location**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/tests/unit/test_memory_content.py`

```python
def test_build_two_stage_voting_complete_delta_with_counterfactuals_english():
    """Test counterfactual integration in English voting memory."""
    # Setup English language manager
    lang_manager = create_language_manager(SupportedLanguage.ENGLISH)
    
    alternative_earnings = {
        'maximizing_floor': 1.2,
        'maximizing_average': 2.8,
        'maximizing_average_with_floor': 2.1,
        'maximizing_average_with_range': 1.9
    }
    
    result = build_two_stage_voting_complete_delta(
        participant_name="TestAgent",
        principle_num=3,
        principle_display_name="Maximizing Average with Floor Constraint",
        constraint_amount=15000,
        consensus_reached=True,
        agreed_principle="Maximizing Average with Floor Constraint",
        alternative_earnings=alternative_earnings,
        assigned_class="medium",
        language_manager=lang_manager
    )
    
    # Verify counterfactual information is included
    assert "This assigns you to the following income class: MEDIUM" in result
    assert "Maximizing Floor Income" in result
    assert "$12,000    $1.20" in result  # Check income conversion
    assert "Maximizing Average Income" in result
    assert "$28,000    $2.80" in result

def test_build_two_stage_voting_complete_delta_with_counterfactuals_spanish():
    """Test counterfactual integration in Spanish voting memory."""
    # Similar test with Spanish language manager
    lang_manager = create_language_manager(SupportedLanguage.SPANISH)
    # ... test implementation
    
    # Verify Spanish counterfactual text
    assert "Esto le asigna a la siguiente clase de ingresos: MEDIO" in result
    assert "Maximizar los ingresos mínimos" in result

def test_build_two_stage_voting_complete_delta_with_counterfactuals_mandarin():
    """Test counterfactual integration in Mandarin voting memory."""
    # Similar test with Mandarin language manager  
    lang_manager = create_language_manager(SupportedLanguage.MANDARIN)
    # ... test implementation
    
    # Verify Mandarin counterfactual text  
    assert "这将把您分配到以下收入类别：中等" in result
```

## Risk Assessment and Mitigation

### Risk 1: Distribution Data Unavailability
**Impact**: Medium - Counterfactuals cannot be calculated
**Mitigation**: Graceful fallback to current behavior, log warning for debugging

### Risk 2: Language Manager Issues  
**Impact**: Low - Fallback to English or basic formatting
**Mitigation**: Try-catch blocks with fallback translation handling

### Risk 3: Performance Impact
**Impact**: Low - Additional calculations during memory updates
**Mitigation**: Counterfactuals calculated once, minimal computation overhead

### Risk 4: Memory Content Size Increase
**Impact**: Low - Slightly longer memory updates
**Mitigation**: Existing memory truncation logic will handle size increases

### Risk 5: Translation Inconsistencies
**Impact**: Medium - User confusion across languages
**Mitigation**: Use existing Phase 1 translation keys for consistency

## Success Criteria

### Functional Requirements
1. ✅ Voting memory updates include counterfactual earnings information
2. ✅ Multi-language support (English, Spanish, Mandarin)  
3. ✅ Consistent formatting with Phase 1 counterfactuals
4. ✅ Graceful fallback when distribution data unavailable
5. ✅ No breaking changes to existing voting process

### Quality Requirements  
1. ✅ Unit test coverage for all three languages
2. ✅ Integration test coverage for voting memory updates
3. ✅ Performance impact < 100ms per participant
4. ✅ Memory content increase < 500 characters per update
5. ✅ Zero breaking changes to existing translation keys

### User Experience Requirements
1. ✅ Agents receive complete transparency about alternative outcomes
2. ✅ Consistent information quality across Phase 1 and Phase 2
3. ✅ Language-appropriate formatting and terminology
4. ✅ Clear income class assignment information  
5. ✅ Formatted counterfactual table matching Phase 1 style

## Implementation Timeline

### Phase 1 (Foundation): 2-3 hours
- Update memory content builder with counterfactual parameters
- Add basic translation keys to all three language files
- Unit tests for memory content builder

### Phase 2 (Integration): 3-4 hours  
- Extend TwoStageVotingManager with counterfactual calculation
- Implement distribution data access strategy
- Add helper methods for counterfactual computation

### Phase 3 (Testing): 2-3 hours
- Integration tests for voting memory updates
- End-to-end testing across all three languages
- Performance and memory usage validation

### Phase 4 (Refinement): 1-2 hours
- Error handling and fallback improvements
- Documentation updates
- Code review and optimization

**Total Estimated Time**: 8-12 hours

## Backward Compatibility

This implementation maintains full backward compatibility:

1. **No Breaking Changes**: All existing method signatures remain the same
2. **Optional Parameters**: New parameters have default values (None)
3. **Graceful Degradation**: If counterfactual data is unavailable, behavior falls back to current implementation
4. **Translation Reuse**: Leverages existing Phase 1 translation keys where possible
5. **Service Independence**: TwoStageVotingManager continues to work without CounterfactualsService

## Future Enhancements

1. **Rich Counterfactual Analysis**: Add insights about best/worst alternatives
2. **Income Class Optimization**: Allow agents to see counterfactuals for different income classes
3. **Constraint Analysis**: Show how different constraint amounts would affect outcomes
4. **Group Comparison**: Show how individual choice compares to group choice
5. **Historical Analysis**: Compare Phase 2 counterfactuals with Phase 1 experience

## Conclusion

This implementation plan provides a comprehensive solution for adding multi-language counterfactual earnings information to voting memory updates. By reusing existing Phase 1 infrastructure and translation keys, we ensure consistency across the experiment while maintaining full backward compatibility.

The solution addresses the core issue - agents not having transparency about alternative outcomes after voting - while preserving the robust multi-language support that the framework already provides in Phase 1.

**Key Benefits**:
- ✅ Complete transparency matching Phase 1 standards
- ✅ Full multi-language support (English, Spanish, Mandarin)  
- ✅ Minimal implementation complexity by reusing existing infrastructure
- ✅ Zero breaking changes to existing functionality
- ✅ Graceful fallback behavior when data unavailable
- ✅ Comprehensive testing strategy across all languages

This enhancement will significantly improve the quality of final rankings by ensuring agents have complete information about counterfactual outcomes, leading to more informed decision-making in the crucial post-voting phase of the experiment.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Analyze Phase 1 multi-language counterfactual implementation", "status": "completed", "activeForm": "Analyzing Phase 1 multi-language counterfactual implementation"}, {"content": "Examine current voting memory update process across languages", "status": "completed", "activeForm": "Examining current voting memory update process across languages"}, {"content": "Analyze translation files for counterfactual keys", "status": "completed", "activeForm": "Analyzing translation files for counterfactual keys"}, {"content": "Examine CounterfactualsService multi-language support", "status": "completed", "activeForm": "Examining CounterfactualsService multi-language support"}, {"content": "Review TwoStageVotingManager memory update implementation", "status": "completed", "activeForm": "Reviewing TwoStageVotingManager memory update implementation"}, {"content": "Create comprehensive multi-language implementation plan", "status": "completed", "activeForm": "Creating comprehensive multi-language implementation plan"}]