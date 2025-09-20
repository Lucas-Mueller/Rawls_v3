# Plan to Fix Duplicate Text in Final Ranking Prompts

## Problem Summary
When collecting final preference rankings from participants in Phase 2, duplicate text appears in the prompt footer, specifically:
- "GROUP DISCUSSION - Round 5 of 5"
- "What is your statement to the group for this round?"

This occurs because the OpenAI Agent context still contains stale values from previous discussion rounds that cause incorrect prompt formatting.

## Root Cause Analysis
The issue occurs in `core/services/counterfactuals_service.py` in the `_get_final_ranking_task_streamlined()` method (line 770):

```python
result = await Runner.run(participant.agent, final_ranking_prompt, context=context)
```

**Problem**: The `context` object contains stale values from the last discussion round:
- `context.round_number = 5` (from last discussion round)
- `context.interaction_type = "statement"` (from discussion mode)

**Effect**: The OpenAI Agent SDK automatically applies discussion-style formatting to the final ranking prompt based on these context values, causing the duplicate text to appear.

## Technical Solution

### Core Fix
Clear the discussion-related context values before calling `Runner.run()` for final ranking collection:

```python
# In _get_final_ranking_task_streamlined(), before Runner.run():
context.interaction_type = None  # Clear discussion mode
context.round_number = 0  # Reset to prevent round-based formatting
```

### Files to Modify
- `core/services/counterfactuals_service.py` - Update `_get_final_ranking_task_streamlined()` method

### Implementation Steps
1. **Context Reset**: Clear `interaction_type` and `round_number` before `Runner.run()`
2. **Optional Enhancement**: Set `interaction_type = "final_ranking"` if explicit typing needed
3. **Testing**: Verify across all supported languages (English, Spanish, Mandarin)
4. **Validation**: Ensure ranking collection still functions correctly

## Enhanced Testing Strategy

### Primary Tests
1. **Prompt Verification**: Confirm final ranking prompts no longer contain duplicate text
2. **Language Support**: Test fix across English, Spanish, and Mandarin configurations
3. **Functionality**: Ensure ranking collection and parsing still work correctly
4. **Context State**: Verify context clearing doesn't affect memory updates

### Test Cases
- Run experiments with different personality configurations
- Verify agent responses are still properly parsed by utility agents
- Check that memory updates continue to work after context clearing
- Ensure no regression in consensus handling or results delivery

### Success Criteria
- ✅ No duplicate discussion text in final ranking prompts
- ✅ Rankings are collected successfully across all languages
- ✅ No side effects on memory management or parsing
- ✅ Agent responses maintain expected format and quality

## Risk Assessment

### Minimal Risk Factors
- **Isolated Change**: Single-line fix in focused location
- **Clear Rollback**: Easy to revert if issues arise
- **No Breaking Changes**: Doesn't modify interfaces or data models
- **Architectural Alignment**: Follows existing services-first pattern

### Potential Concerns
- Context clearing might affect other OpenAI Agent SDK features (low probability)
- Memory updates could be affected (mitigated by testing)
- Language-specific formatting edge cases (addressed by multi-language testing)

## Alternative Approaches

### If Simple Fix Fails
1. **Clean Context Copy**: Create minimal context object specifically for final ranking
2. **Explicit Interaction Type**: Use `interaction_type = "final_ranking"` with language manager support
3. **Direct Prompt Execution**: Bypass context-based formatting entirely

### Why Current Approach is Best
- **Simplicity**: Minimal necessary change
- **Root Cause Focus**: Addresses the actual problem, not symptoms
- **Architecture Compliance**: Fits within CounterfactualsService ownership
- **Low Complexity**: Single-line fix with clear intent

## Implementation Priority

**Priority**: Critical - blocks proper final ranking collection  
**Complexity**: Low - targeted fix in correct service  
**Estimated Effort**: 1 hour implementation + 2 hours testing  
**Risk Level**: Minimal - isolated change with clear rollback path

## Success Metrics

### Immediate Success
- Duplicate text eliminated from final ranking prompts
- All existing functionality preserved
- Multi-language support maintained

### Long-term Success  
- No regression in experiment quality or results
- Maintained code simplicity and clarity
- Clean separation between discussion and ranking phases

---

**Note**: This plan has been reviewed by the plan-reviewer agent and incorporates feedback on technical soundness, risk assessment, and testing completeness.