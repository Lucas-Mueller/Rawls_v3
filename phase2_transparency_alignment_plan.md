# Phase 2 Transparency Alignment Plan

## Executive Summary

This plan outlines the systems-level changes required to align Phase 2's information disclosure with Phase 1's transparency model. Currently, Phase 1 provides agents with complete counterfactual information (their class assignment and earnings under all four principles), while Phase 2 only provides final earnings and consensus status. This misalignment limits agents' ability to make informed final rankings based on comparable information.

## Problem Statement

**Current Information Asymmetry:**
- **Phase 1**: Complete transparency with class assignments and full counterfactual earnings
- **Phase 2**: Limited disclosure with only final earnings and consensus status
- **Result**: Agents cannot make equally informed decisions in their final rankings

**Impact:**
- Reduced experimental validity due to information inconsistency
- Agents may base final rankings on incomplete information
- Potential bias toward Phase 1 experiences over Phase 2 outcomes

## Current State Analysis

### Phase 1 Information Disclosure Pattern
```
For each of 4 demonstration rounds:
1. Agent chooses a justice principle
2. System assigns income class based on chosen principle
3. System reveals:
   ✓ Assigned income class (e.g., "MEDIUM HIGH")
   ✓ Earnings under chosen principle (e.g., $1,234.56)
   ✓ Counterfactual earnings under ALL 4 principles with SAME class assignment
   ✓ Highlights of best/worst alternatives
```

### Phase 2 Information Disclosure Pattern
```
After group discussion concludes:
1. Group selects principle (or random assignment occurs)
2. System calculates payoffs
3. System reveals:
   ✓ Final earnings amount only (e.g., $5,678.90)
   ✓ Consensus status (reached/not reached)
   ✗ No class assignment disclosure
   ✗ No counterfactual earnings under other principles
```

### Key Differences
| Aspect | Phase 1 | Phase 2 | Gap |
|--------|---------|---------|-----|
| Class Assignment | ✓ Disclosed | ✗ Hidden | **Critical Gap** |
| Chosen Principle Earnings | ✓ Disclosed | ✓ Disclosed | Aligned |
| Alternative Earnings | ✓ All 4 principles | ✗ None | **Critical Gap** |
| Counterfactual Analysis | ✓ Detailed | ✗ None | **Critical Gap** |

## Target State Design

### Enhanced Phase 2 Information Disclosure
After group discussion and principle selection/random assignment, each agent receives:

```
PHASE 2 FINAL RESULTS

Consensus Status: [Consensus reached on Principle X] OR [No consensus - random assignment]
Your Income Class Assignment: [CLASS_NAME]
Your Earnings: $[AMOUNT]

COUNTERFACTUAL ANALYSIS - What you would have earned under each principle:
┌─────────────────────────────────────────┬──────────┬──────────┐
│ Justice Principle                       │ Income   │ Earnings │
├─────────────────────────────────────────┼──────────┼──────────┤
│ Maximizing Floor Income                 │ $XX,XXX  │ $XXX.XX  │
│ Maximizing Average Income               │ $XX,XXX  │ $XXX.XX  │
│ Maximizing Average with Floor Constraint│ $XX,XXX  │ $XXX.XX  │
│ Maximizing Average with Range Constraint│ $XX,XXX  │ $XXX.XX  │
└─────────────────────────────────────────┴──────────┴──────────┘

Key Insights:
- [Best alternative: Would have earned $XXX.XX more under Principle Y]
- [Worst alternative: Would have earned $XXX.XX less under Principle Z]
```

## Implementation Approach

### Phase 1: Core System Changes

#### 1. Enhance `_apply_group_principle_and_calculate_payoffs` Method
```python
# Current signature:
async def _apply_group_principle_and_calculate_payoffs(
    self, discussion_result, config
) -> tuple[Dict[str, float], Dict[str, str]]

# Enhanced signature:
async def _apply_group_principle_and_calculate_payoffs(
    self, discussion_result, config
) -> tuple[Dict[str, float], Dict[str, str], Dict[str, Dict[str, float]]]
#   returns: (payoffs, assigned_classes, alternative_earnings_by_agent)
```

**Key Changes:**
- Calculate alternative earnings for ALL participants under ALL principles
- Use the SAME class assignment for counterfactual calculations
- Return structured data for both consensus and non-consensus scenarios

#### 2. Create New `_calculate_phase2_counterfactuals` Method
```python
async def _calculate_phase2_counterfactuals(
    self,
    distribution_set: Any,
    assigned_classes: Dict[str, str],
    consensus_principle: Optional[PrincipleChoice] = None,
    constraint_amount: Optional[int] = None
) -> Dict[str, Dict[str, float]]:
    """
    Calculate what each agent would earn under all four principles
    using their assigned income class from Phase 2.
    
    Returns:
        Dict[agent_name, Dict[principle_key, earnings]]
    """
```

#### 3. Enhance `_collect_final_rankings` Method
```python
# Current: Basic earnings notification
result_content = f"FINAL RESULTS: Phase 2 earnings: ${final_earnings:.2f}. "

# Enhanced: Full transparency matching Phase 1
result_content = await self._build_phase2_detailed_results(
    participant_name=participant.name,
    final_earnings=final_earnings,
    assigned_class=assigned_classes[participant.name],
    alternative_earnings=alternative_earnings_by_agent[participant.name],
    consensus_result=discussion_result
)
```

### Phase 2: Content Generation

#### 4. Create `_build_phase2_detailed_results` Method
```python
async def _build_phase2_detailed_results(
    self,
    participant_name: str,
    final_earnings: float,
    assigned_class: str,
    alternative_earnings: Dict[str, float],
    consensus_result: GroupDiscussionResult
) -> str:
    """
    Build detailed Phase 2 results matching Phase 1 transparency level.
    Includes class assignment and full counterfactual analysis.
    """
```

#### 5. Add New Language Manager Templates
Add to `translations/english_prompts.json`:
```json
{
  "prompts": {
    "phase2_detailed_results_header": "PHASE 2 FINAL RESULTS\n\nConsensus Status: {consensus_status}\nYour Income Class Assignment: {assigned_class}\nYour Earnings: ${earnings:.2f}",
    
    "phase2_counterfactual_table_header": "COUNTERFACTUAL ANALYSIS - What you would have earned under each principle:\n┌─────────────────────────────────────────┬──────────┬──────────┐\n│ Justice Principle                       │ Income   │ Earnings │\n├─────────────────────────────────────────┼──────────┼──────────┤",
    
    "phase2_counterfactual_insights": "Key Insights:\n- Best alternative: Would have earned ${best_diff:.2f} more under {best_principle}\n- Worst alternative: Would have earned ${worst_diff:.2f} less under {worst_principle}"
  }
}
```

### Phase 3: Memory Management Enhancement

#### 6. Enhance Memory Content Generation
Create new utility in `utils/memory_content.py`:
```python
def build_phase2_detailed_delta(
    participant_name: str,
    final_earnings: float,
    assigned_class: str,
    alternative_earnings: Dict[str, float],
    consensus_result: GroupDiscussionResult,
    top_counterfactuals: List[str]
) -> str:
    """
    Build Phase 2 memory content with same detail level as Phase 1.
    """
```

## Technical Requirements

### Core Components to Modify

1. **`core/phase2_manager.py`**:
   - `_apply_group_principle_and_calculate_payoffs()` - Enhanced return values
   - `_collect_final_rankings()` - Enhanced result communication
   - New `_calculate_phase2_counterfactuals()` method
   - New `_build_phase2_detailed_results()` method

2. **`core/distribution_generator.py`**:
   - Verify `calculate_alternative_earnings_by_principle_fixed_class()` works for Phase 2
   - May need Phase 2-specific variants for different distribution scenarios

3. **`translations/*.json`**:
   - Add Phase 2-specific result templates
   - Add counterfactual table formatting
   - Add multilingual support for new content

4. **`utils/memory_content.py`**:
   - New `build_phase2_detailed_delta()` function
   - New `extract_phase2_counterfactual_highlights()` function

### Data Flow Changes

#### Current Flow:
```
Group Discussion → Principle Selection → Payoff Calculation → Basic Results → Final Rankings
```

#### Enhanced Flow:
```
Group Discussion → Principle Selection → Enhanced Payoff Calculation → 
    ↓
Counterfactual Analysis → Detailed Results Generation → Enhanced Memory Update →
    ↓
Final Rankings with Complete Information
```

### New Data Structures

#### Enhanced ApplicationResult for Phase 2:
```python
@dataclass
class Phase2ApplicationResult:
    """Enhanced Phase 2 result with full transparency."""
    consensus_reached: bool
    agreed_principle: Optional[PrincipleChoice]
    final_earnings: float
    assigned_class: str
    alternative_earnings_by_principle: Dict[str, float]
    counterfactual_highlights: List[str]
    consensus_explanation: str
```

## Implementation Timeline

### Week 1: Core Infrastructure
- [ ] Enhance `_apply_group_principle_and_calculate_payoffs()` method
- [ ] Create `_calculate_phase2_counterfactuals()` method
- [ ] Add new language templates
- [ ] Unit tests for counterfactual calculations

### Week 2: Content Generation
- [ ] Implement `_build_phase2_detailed_results()` method
- [ ] Enhance memory content utilities
- [ ] Create multilingual support
- [ ] Integration tests for full flow

### Week 3: System Integration
- [ ] Enhance `_collect_final_rankings()` method
- [ ] Update memory management integration
- [ ] End-to-end testing
- [ ] Performance validation

### Week 4: Validation & Rollout
- [ ] A/B testing with existing experiments
- [ ] Results comparison validation
- [ ] Documentation updates
- [ ] Production deployment

## Risk Assessment

### High Risk
- **Breaking Changes**: Modifications affect core experimental flow
  - **Mitigation**: Feature flag for gradual rollout, backward compatibility
  
- **Performance Impact**: Additional calculations for all participants
  - **Mitigation**: Async processing, caching, performance monitoring

### Medium Risk
- **Memory Constraints**: Enhanced content may exceed agent memory limits
  - **Mitigation**: Configurable detail level, memory optimization

- **Multilingual Consistency**: New templates need translation accuracy
  - **Mitigation**: Professional translation review, validation testing

### Low Risk
- **Display Formatting**: Table formatting may vary across models
  - **Mitigation**: Multiple format options, fallback plain text

## Success Metrics

### Quantitative Metrics
- **Information Completeness**: 100% of agents receive class assignments and counterfactuals
- **Consistency Check**: Phase 1 and Phase 2 information disclosure patterns match
- **Performance Impact**: <10% increase in Phase 2 processing time
- **Memory Usage**: <15% increase in average agent memory consumption

### Qualitative Metrics
- **Agent Decision Quality**: More informed final rankings based on complete information
- **Experimental Validity**: Consistent information availability across phases
- **User Experience**: Clear, readable results presentation

## Backwards Compatibility

### Configuration Flag
```yaml
# In experiment configuration
phase2_enhanced_transparency:
  enabled: true                    # Enable enhanced transparency
  detail_level: "full"             # Options: "basic", "enhanced", "full"
  include_counterfactuals: true    # Show alternative earnings
  include_class_assignment: true   # Show income class
```

### Gradual Migration
1. **Phase A**: Deploy with feature flag disabled (existing behavior)
2. **Phase B**: Enable for new experiments, validate results
3. **Phase C**: Enable for all experiments after validation
4. **Phase D**: Remove old code path after stable operation

## Testing Strategy

### Unit Tests
- `test_phase2_counterfactual_calculations()`: Verify accurate alternative earnings
- `test_phase2_detailed_results_generation()`: Validate content formatting
- `test_multilingual_phase2_templates()`: Check translation consistency

### Integration Tests
- `test_enhanced_phase2_flow()`: End-to-end enhanced transparency flow
- `test_backward_compatibility()`: Existing experiments continue working
- `test_memory_management_with_enhancement()`: Memory limits respected

### Performance Tests
- `test_phase2_processing_time()`: Measure performance impact
- `test_concurrent_agent_processing()`: Validate async processing
- `test_large_group_scalability()`: Test with maximum participant counts

## Documentation Updates

### Developer Documentation
- Update API documentation for modified methods
- Add examples of new data structures
- Document configuration options

### User Documentation  
- Update experiment result interpretation guide
- Add examples of enhanced Phase 2 results
- Document migration path from existing experiments

## Future Considerations

### Potential Enhancements
- **Interactive Counterfactuals**: Allow agents to query specific "what-if" scenarios
- **Comparative Analysis**: Show Phase 1 vs Phase 2 earnings comparison
- **Group-Level Insights**: Show how group decision affected individual outcomes

### Scalability Considerations
- **Large Groups**: Optimize for experiments with 10+ participants
- **Complex Principles**: Support for custom justice principle definitions
- **Real-Time Updates**: Live counterfactual calculations during discussion

---

## Implementation Checklist

- [ ] Core system modifications completed
- [ ] Content generation implemented
- [ ] Memory management enhanced
- [ ] Language templates added
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Performance validation completed
- [ ] Backward compatibility verified
- [ ] Documentation updated
- [ ] A/B testing completed
- [ ] Production deployment ready

---

*This plan ensures Phase 2 information disclosure matches Phase 1's transparency level, enabling agents to make equally informed decisions throughout the experimental process.*