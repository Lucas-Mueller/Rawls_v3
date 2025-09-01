# Voting Forgetting Bug Report

## Problem Summary

**Critical Issue**: Agents agree on compromises during Phase 2 discussions but "forget" these agreements when transitioning to the voting phase, potentially voting inconsistently with their previously agreed positions.

**Impact**: This bug undermines experimental validity by breaking the logical flow from discussion consensus to voting behavior, making experiment results unreliable.

## Technical Root Cause

The issue stems from **context-aware memory summarization** in `utils/memory_summarizer.py`. When agents transition from discussion to voting, the memory context detection switches from "discussion" to "voting", triggering different summarization logic that strips out compromise details.

### Context Detection Logic
```python
# In experiment_agents/participant_agent.py:176
def _detect_memory_context_type(context: ParticipantContext, role_description: str) -> str:
    # Check for voting-related contexts
    if any(keyword in role_description.lower() for keyword in ["vote", "ballot", "consensus"]):
        return "voting"  # Triggers problematic voting context summarization
    
    # Phase 2 discussion contexts
    if context.phase == ExperimentPhase.PHASE_2:
        if "vote" not in role_description.lower():
            return "discussion"
        else:
            return "voting"
```

### Problematic Voting Summarization
```python
# In utils/memory_summarizer.py:124
def _create_voting_summary(full_memory: str, insights: List[str], max_lines: int) -> str:
    """Create voting-focused summary emphasizing Phase 1 experience and voting history."""
    lines = []
    
    # Phase 1 earnings summary - preserves individual experience
    # Best performing principle - preserves individual preference
    # Current voting status/preference - loses group context
    # Key insight if space allows - may not include compromise details
```

## Bug Investigation Results

### Test Case Analysis
Using `test_compromise_forgetting_issue.py`, we analyzed a realistic scenario where agents reached consensus on "maximizing average with floor constraint at $18,000".

**Full Memory Content** (what agents actually remember):
- `compromise`: 5 mentions
- `$18,000`: 6 mentions  
- `consensus`: 2 mentions
- `agreed`: 3 mentions
- `everyone`: 2 mentions

**Discussion Context Summary** (what agents see during discussion):
- Preserves most compromise indicators
- Shows group dynamics and agreement building

**Voting Context Summary** (what agents see during voting):
- `compromise`: **0 mentions**
- `$18,000`: **0 mentions**
- `consensus`: **0 mentions** 
- `agreed`: **0 mentions**
- `everyone`: **0 mentions**

### Information Loss Pattern

The voting context summarization focuses on:
1. Phase 1 individual earnings (`"Phase 1: Earned $9.60 total across principle applications"`)
2. Individual best performing principle (`"Best performing: floor principle"`)
3. Individual voting status (loses group agreements)
4. Single key insight (may miss compromise details)

**What Gets Lost**:
- Specific compromise amounts (`$18,000 floor constraint`)
- Group consensus statements (`everyone agreed on...`)
- Compromise language (`reasonable`, `middle ground`, `accept`)
- Multi-party agreement details

## Experimental Impact

### Scenario Example
1. **Discussion Phase**: Agents agree on compromise - "maximizing average with $18,000 floor constraint"
2. **Context Switch**: Role changes from "Phase 2 Group Discussion" to "Phase 2 - Secret ballot selection"
3. **Memory Loss**: Voting summary drops compromise details
4. **Inconsistent Voting**: Agents may vote for their original preferences rather than agreed compromise

### Validity Concerns
- **Internal Consistency**: Agents' voting behavior doesn't match their stated agreements
- **Experimental Design**: The two-phase structure relies on memory continuity
- **Data Reliability**: Results may reflect memory bugs rather than agent reasoning

## Proposed Solution

### Phase 1: Enhance Voting Context Summarization

**Target**: Modify `_create_voting_summary()` in `utils/memory_summarizer.py` to preserve compromise information.

```python
def _create_voting_summary(full_memory: str, insights: List[str], max_lines: int) -> str:
    """Create voting-focused summary preserving group agreements and compromise details."""
    lines = []
    
    # 1. Group consensus information (NEW)
    group_consensus = _extract_group_consensus(full_memory)
    if group_consensus:
        lines.append(f"Group agreement: {group_consensus}")
    
    # 2. Specific compromise details (NEW)  
    compromise_details = _extract_compromise_details(full_memory)
    if compromise_details:
        lines.append(f"Compromise: {compromise_details}")
    
    # 3. Phase 1 performance (existing, condensed)
    if len(lines) < max_lines:
        phase1_summary = _extract_phase1_summary(full_memory)
        if phase1_summary:
            lines.append(phase1_summary)
    
    # 4. Current voting context (existing, enhanced)
    if len(lines) < max_lines:
        voting_context = _extract_enhanced_voting_context(full_memory)
        if voting_context:
            lines.append(voting_context)
    
    return " ".join(lines[:max_lines])
```

### Phase 2: Add Compromise-Specific Extraction Methods

```python
@staticmethod
def _extract_group_consensus(memory: str) -> Optional[str]:
    """Extract group consensus statements preserving compromise agreements."""
    patterns = [
        r"(?:group|everyone|all|consensus).*?(?:agreed|consensus|support).*?(\$[\d,]+|principle \d+|floor constraint)",
        r"(?:compromise|middle ground).*?(\$[\d,]+|principle \d+)",
        r"(?:Alice|Bob|Charlie).*?(?:Alice|Bob|Charlie).*?(?:agreed|consensus).*?(\$[\d,]+|principle \d+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, memory, re.IGNORECASE)
        if match:
            return match.group(0)[:60]  # Preserve key consensus details
    
    return None

@staticmethod  
def _extract_compromise_details(memory: str) -> Optional[str]:
    """Extract specific compromise amounts and principle combinations."""
    patterns = [
        r"(\$[\d,]+)\s+(?:floor constraint|constraint)",
        r"(?:maximizing average|average).*?(?:with|plus).*?(\$[\d,]+)",
        r"(?:principle \d+).*?(?:with|plus|constraint).*?(\$[\d,]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, memory, re.IGNORECASE)
        if match:
            return match.group(0)[:40]  # Preserve specific compromise terms
    
    return None
```

### Phase 3: Configuration Options

Add configuration flags to control compromise preservation:

```python
# In config/models.py
preserve_compromise_in_voting: bool = Field(
    True, 
    description="Preserve compromise details when summarizing memory for voting contexts"
)

compromise_preservation_priority: str = Field(
    "high",
    description="Priority level for preserving compromise info: 'low', 'medium', 'high'"
)
```

### Phase 4: Validation Strategy

1. **Unit Tests**: Test extraction methods with various compromise scenarios
2. **Integration Tests**: Verify full discussion-to-voting flow preservation
3. **Regression Tests**: Ensure existing functionality remains intact
4. **Experiment Validation**: Run controlled experiments to verify fix effectiveness

## Implementation Priority

### Critical (Immediate)
- [ ] Implement `_extract_group_consensus()` method
- [ ] Implement `_extract_compromise_details()` method  
- [ ] Enhance `_create_voting_summary()` to use new extractors
- [ ] Test with the existing `test_compromise_forgetting_issue.py`

### High (Next Sprint)
- [ ] Add configuration options for compromise preservation
- [ ] Create comprehensive test suite for various compromise scenarios
- [ ] Validate fix with real experiment data

### Medium (Future)
- [ ] Consider alternative memory optimization that preserves more context
- [ ] Add compromise preservation metrics to experiment reports
- [ ] Implement compromise preservation for other context types if needed

## Testing Strategy

### Existing Test Enhancement
The `test_compromise_forgetting_issue.py` provides a solid foundation. Enhance it to:
- Test multiple compromise scenarios (different amounts, principles)
- Validate extraction method accuracy
- Verify end-to-end preservation in voting phase

### New Test Cases Needed
1. **Multiple Compromise Types**: Floor constraints, range constraints, hybrid approaches
2. **Complex Negotiations**: Multi-round compromise evolution
3. **Edge Cases**: Very long negotiations, multiple compromise attempts
4. **Cross-Language**: Ensure compromise preservation works in Spanish/Mandarin

## Risk Assessment

### Low Risk
- The fix targets specific extraction methods without changing core architecture
- Existing functionality preserved through careful method enhancement
- Configuration flags allow gradual rollout

### Mitigation Strategies
- Comprehensive testing before deployment
- Fallback to existing summarization if new methods fail
- Configuration flags to disable enhancement if issues arise

## Success Metrics

### Quantitative
- Compromise keywords preserved: target >80% retention in voting context
- Agent voting consistency: >90% alignment between discussion agreements and votes
- No regression in existing memory summarization performance

### Qualitative  
- Agents vote consistently with their stated discussion agreements
- Experiment results reflect genuine agent reasoning rather than memory artifacts
- Enhanced experimental validity and reliability

## Timeline

- **Week 1**: Implement core extraction methods and enhanced voting summarization
- **Week 2**: Comprehensive testing and validation
- **Week 3**: Configuration options and deployment preparation
- **Week 4**: Production deployment and monitoring

This fix addresses a critical experimental validity issue while maintaining the benefits of memory optimization through targeted enhancement rather than complete redesign.