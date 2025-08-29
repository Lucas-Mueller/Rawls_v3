# Phase 2 Memory Update Investigation Report

## Executive Summary

Investigation of experiment `experiment_results_20250827_142227.json` revealed two critical issues in Phase 2:

1. **Missing Memory Updates After Voting Actions**: Agents do not update their memory after participating in voting confirmations or casting ballots, leading to lack of awareness of their own voting actions.

2. **Principle Parsing Misalignment**: James consistently advocates for "maximizing_average_floor_constraint" (在最低收入约束条件下最大化平均收入) but the system incorrectly detects it as "maximizing_average" only, causing a mismatch between stated and detected preferences.

## Issue 1: Missing Memory Updates After Voting

### Current Behavior
- Memory updates occur ONLY after discussion statements (line 473 in phase2_manager.py)
- NO memory updates after:
  - Voting confirmation responses (lines 1194-1221)
  - Secret ballot casting (lines 1259-1283)
- Agents remain unaware of their voting actions in subsequent discussions

### Evidence
In `phase2_manager.py`:
```python
# Line 473: Memory update after statement
context.memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, round_content, memory_guidance_style=memory_guidance_style
)

# Lines 1194-1221: NO memory update after confirmation
result = await Runner.run(participant.agent, confirmation_prompt, context=context)
confirmation_response = result.final_output
# Missing: memory update

# Lines 1259-1283: NO memory update after ballot
result = await Runner.run(participant.agent, ballot_prompt, context=context)
ballot_response = result.final_output  
# Missing: memory update
```

### Impact
- Agents cannot reference their voting behavior in later discussions
- Creates cognitive disconnect where agents are unaware of their own actions
- Reduces experimental validity as agents cannot learn from voting outcomes

## Issue 2: Principle Detection Failure

### Current Behavior
- James consistently states support for "在最低收入约束条件下最大化平均收入" (maximizing_average_floor_constraint)
- System detects this as "maximizing_average" only (missing the floor constraint part)
- Occurs in all 5 rounds of discussion

### Evidence
From experiment data analysis:
```
Round 1: System detected: maximizing_average, Actually advocates: maximizing_average_floor_constraint
Round 2: System detected: maximizing_average, Actually advocates: maximizing_average_floor_constraint
Round 3: System detected: maximizing_average, Actually advocates: maximizing_average_floor_constraint
Round 4: System detected: maximizing_average, Actually advocates: maximizing_average_floor_constraint
Round 5: System detected: maximizing_average, Actually advocates: maximizing_average_floor_constraint
```

### Root Cause Analysis

The principle detection uses LLM-based parsing via `parse_principle_choice_llm()` which appears to be failing for Chinese text. The mapping exists in the code:

```python
# Line 814 in utility_agent.py
"最低收入约束": "maximizing_average_floor_constraint"
```

But the LLM parser is likely:
1. Not receiving proper context about Chinese principle names
2. Truncating or simplifying the principle name during parsing
3. Defaulting to the simpler "maximizing_average" when uncertain

## Why James Votes Against Stated Preference

This is likely a cascade effect:
1. James states support for "maximizing_average_floor_constraint" 
2. System incorrectly logs it as "maximizing_average"
3. James's memory doesn't get updated after voting
4. James may be confused about what he previously supported
5. Without memory of voting actions, James cannot maintain consistency

## Proposed Solutions

### Solution 1: Add Memory Updates After Voting (Priority: HIGH)

Add memory updates after both confirmation and ballot phases:

```python
# After confirmation (around line 1221)
confirmation_content = f"""Voting Confirmation Round {discussion_state.round_number}:
You were asked if you agree to proceed with voting.
Your response: {confirmation_response}
Outcome: {'Agreed to vote' if agrees_to_vote else 'Declined to vote'}"""

context.memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, confirmation_content, memory_guidance_style=memory_guidance_style
)

# After ballot (around line 1283)
ballot_content = f"""Secret Ballot Vote Round {discussion_state.round_number}:
You cast a secret ballot for a justice principle.
Your vote: {principle_choice.principle.value}
{f'With constraint: ${principle_choice.constraint_amount}' if principle_choice.constraint_amount else ''}
Outcome: Vote recorded (secret ballot - results pending)"""

context.memory = await MemoryManager.prompt_agent_for_memory_update(
    participant, context, ballot_content, memory_guidance_style=memory_guidance_style
)
```

### Solution 2: Fix Principle Detection for Multilingual Content (Priority: HIGH)

Enhance the LLM parsing prompt to better handle Chinese principles:

1. **Option A - Direct Mapping Fix**: Add preprocessing to detect exact Chinese phrases before LLM parsing:
```python
# In _extract_favored_principle before calling parse_principle_choice_enhanced
chinese_mappings = {
    "在最低收入约束条件下最大化平均收入": "maximizing_average_floor_constraint",
    "在范围约束条件下最大化平均收入": "maximizing_average_range_constraint",
    "最大化最低收入": "maximizing_floor",
    "最大化平均收入": "maximizing_average"
}

for chinese_term, principle in chinese_mappings.items():
    if chinese_term in statement:
        return principle
```

2. **Option B - Enhanced LLM Context**: Provide the LLM parser with explicit multilingual mappings in the prompt to ensure correct detection.

### Solution 3: Add Voting Awareness Validation (Priority: MEDIUM)

Add a check after voting to ensure agents are aware of their vote:

```python
# After ballot phase completion
if consensus_reached:
    # Verify each agent remembers their vote
    for i, participant in enumerate(self.participants):
        memory_check = f"What principle did you just vote for?"
        response = await Runner.run(participant.agent, memory_check, context=contexts[i])
        # Log any discrepancies for debugging
```

## Implementation Recommendations

1. **Immediate Fix**: Implement Solution 1 (memory updates) - this is straightforward and critical
2. **High Priority**: Implement Solution 2 Option A (direct mapping) - quick fix for Chinese detection
3. **Validation**: Add logging to track when principle detection fails vs succeeds
4. **Testing**: Create test cases specifically for:
   - Memory persistence across voting actions
   - Multilingual principle detection accuracy
   - Agent awareness of their voting history

## Conclusion

The two issues are interconnected - poor principle detection combined with missing memory updates creates a situation where agents lose track of their preferences and actions. This explains why James appears to vote against his stated preference and is unaware of it afterward.

The solutions are focused and implementable without major architectural changes. Priority should be given to adding memory updates after voting actions, as this is both the most impactful fix and the easiest to implement correctly.