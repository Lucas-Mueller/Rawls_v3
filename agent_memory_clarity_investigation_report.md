# Agent Memory Clarity Investigation Report

## Executive Summary

This report investigates whether agents in the Frohlich Experiment are clearly informed about their previous inputs and responses during Phase 1 and Phase 2. The investigation systematically examines the entire experiment flow to determine if agents have clear visibility into their activity history.

## Methodology

The investigation covered:
1. **Phase 1 Manager** - Individual agent familiarization
2. **Phase 2 Manager** - Group discussion and consensus building
3. **Memory Service** - Unified memory management system
4. **Participant Agent Implementation** - How prompts are constructed
5. **Translation Files** - Prompt templates and memory formatting
6. **Discussion Service** - Statement handling and memory updates
7. **Voting Service** - Vote initiation and confirmation processes

## Key Findings

### Phase 1: Individual Familiarization

#### Initial Ranking (Round 0)
**Memory Status: CLEAR**
- **Input Clarity**: Agents receive the ranking prompt directly in the main prompt field
- **Response Clarity**: Agents see their previous response in memory as "Your Response: [response]"
- **Outcome Clarity**: Clear indication of "Completed initial ranking of justice principles"

**Code Location**: `core/phase1_manager.py:585-599`
```python
round_content = f"""{language_manager.get('memory_field_labels.prompt')} {prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}
{language_manager.get('memory_field_labels.outcome')} {self._get_completion_message_for_task(task_name)}"""
```

#### Principle Explanation (Round -1)
**Memory Status: CLEAR**
- **Input Clarity**: Agents see the explanation prompt as "Prompt: [prompt]"
- **Response Clarity**: Agents see their response as "Your Response: [response]"
- **Outcome Clarity**: "Learned how each justice principle is applied to income distributions through examples"

**Code Location**: `core/phase1_manager.py:601-621`

#### Post-Explanation Ranking (Round 0)
**Memory Status: CLEAR**
- **Input Clarity**: Ranking prompt provided in main prompt
- **Response Clarity**: "Your Response: [response]" format
- **Outcome Clarity**: "Completed ranking after learning how principles apply to distributions"

**Code Location**: `core/phase1_manager.py:895-907`

#### Application Rounds (Rounds 1-4)
**Memory Status: PARTIALLY CLEAR**
- **Input Clarity**: ✅ Clear - "Prompt: [application_prompt]" shows the exact prompt given
- **Response Clarity**: ✅ Clear - "Your Response: [text_response]" shows exactly what agent said
- **Outcome Clarity**: ⚠️ **PARTIAL ISSUE** - While earnings are shown, the format could be clearer about what the agent's input was versus what the outcome was

**Code Location**: `core/phase1_manager.py:886-891`
```python
round_content = f"""{language_manager.get('memory_field_labels.prompt')} {application_prompt}
{language_manager.get('memory_field_labels.your_response')} {text_response}

{earnings_display}

{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.applied_principle_round', round_number=round_num)}"""
```

**Issue**: The earnings display section appears between the agent's response and the outcome, which could make it less clear what the agent actually input versus what the system calculated.

#### Final Ranking (Round 5)
**Memory Status: CLEAR**
- **Input Clarity**: Final ranking prompt provided
- **Response Clarity**: "Your Response: [response]" format
- **Outcome Clarity**: "Completed final ranking of justice principles after experiencing all four rounds"

### Phase 2: Group Discussion

#### Discussion Statements
**Memory Status: PARTIALLY CLEAR**
- **Input Clarity**: ⚠️ **UNCLEAR** - Agents do not see the specific prompt that was given to them for their statement
- **Response Clarity**: ✅ Clear - "Your Statement: [statement]" is shown in discussion history
- **Context Clarity**: ⚠️ **UNCLEAR** - While discussion history is shown, agents don't see what specific prompt elicited their statement

**Code Location**: `core/services/memory_service.py:237-278`
```python
# For discussion memory updates, the content includes discussion history
# but not the specific prompt that was given to elicit the statement
round_content = f"{history_header}\n{discussion_history}\n\n"
```

**Critical Issue**: In Phase 2, agents see their statements in the discussion history, but they don't see what question or prompt caused them to make that statement. The memory update includes discussion history and internal reasoning, but not the specific prompt.

#### Vote Initiation Decisions
**Memory Status: PARTIALLY CLEAR**
- **Input Clarity**: ⚠️ **UNCLEAR** - Vote initiation prompts are not preserved in memory
- **Response Clarity**: ✅ Clear - Decision recorded as "I chose to initiate voting" or "I chose to continue discussion"
- **Context Clarity**: ⚠️ **UNCLEAR** - Recent statement and reasoning may be included in prompt but not preserved

**Code Location**: `core/services/memory_service.py:459-478`

#### Voting Confirmation
**Memory Status: CLEAR**
- **Input Clarity**: ⚠️ **UNCLEAR** - Confirmation prompt not preserved
- **Response Clarity**: ✅ Clear - "Voting confirmation: I agreed to participate" or "declined to participate"

#### Secret Ballot Selection
**Memory Status: CLEAR**
- **Input Clarity**: ⚠️ **UNCLEAR** - Ballot prompt not preserved
- **Response Clarity**: ✅ Clear - "Secret ballot: I voted for [principle_name]"

#### Constraint Amount Specification
**Memory Status: CLEAR**
- **Input Clarity**: ⚠️ **UNCLEAR** - Amount specification prompt not preserved
- **Response Clarity**: ✅ Clear - "Constraint amount: I specified [amount]"

### Memory Service Architecture

#### Memory Update Patterns
**Memory Service Status: INCONSISTENT**

The MemoryService uses two primary patterns:

1. **Direct Selective Updates** (`update_memory_selective`)
2. **Specialized Updates** (discussion, voting, results)

**Issue**: The discussion memory updates don't preserve the prompt that elicited the statement, unlike Phase 1 which consistently shows both prompt and response.

**Code Location**: `core/services/memory_service.py:210-278`

#### Content Truncation
**Status: POTENTIALLY PROBLEMATIC**
- Statements truncated to 300 characters
- Reasoning truncated to 200 characters
- Full content preserved (no truncation applied)

**Code Location**: `core/services/memory_service.py:417-432`

## Critical Issues Identified

### 1. Phase 2 Prompt Visibility Gap
**Severity: HIGH**

In Phase 2, agents can see their statements in the discussion history, but they cannot see what specific question or prompt caused them to make that statement. This creates a disconnect between what the agent remembers saying and the context that elicited the response.

**Current Phase 2 Memory Format:**
```
=== Discussion History ===
[Other participants' statements]
[Agent's own statement]
=== Your Internal Reasoning ===
[Agent's reasoning]
```

**Missing**: The specific prompt that was given to the agent for this round.

### 2. Vote Prompt Context Loss
**Severity: MEDIUM**

During voting processes, agents make decisions but don't retain the specific prompts that led to those decisions. While the decisions themselves are recorded, the context that influenced the decision is lost.

### 3. Inconsistent Memory Formatting
**Severity: LOW**

Phase 1 consistently shows "Prompt: [prompt]" followed by "Your Response: [response]", but Phase 2 discussion memory doesn't follow this pattern, instead showing discussion history.

## Recommendations

### Immediate Fixes

1. **Add Prompt Preservation to Phase 2 Discussion Memory**
   ```python
   # In DiscussionService or MemoryService
   round_content = f"""{language_manager.get('memory_field_labels.prompt')} {discussion_prompt}
   {language_manager.get('memory_field_labels.your_statement')} {statement}
   {history_header}\n{discussion_history}"""
   ```

2. **Standardize Vote Prompt Preservation**
   Ensure voting prompts are included in memory updates similar to Phase 1 pattern.

3. **Add Prompt Context to Vote Initiation Memory**
   Include the vote initiation prompt in the memory update for better decision traceability.

### Long-term Improvements

1. **Unified Memory Format**
   Create a consistent memory update format across all phases that clearly separates:
   - What prompt was given
   - What response was provided
   - What outcome resulted

2. **Enhanced Context Preservation**
   Preserve not just responses but the full context that led to each decision.

3. **Memory Structure Standardization**
   Implement a standardized memory entry structure that clearly delineates input, response, and outcome for all agent interactions.

## Conclusion

**Overall Status: PARTIALLY CLEAR**

Agents have clear visibility into their responses in both phases, but there are significant gaps in prompt visibility, particularly in Phase 2 discussion rounds. While Phase 1 maintains good clarity with consistent "Prompt/Response/Outcome" formatting, Phase 2 discussion memory lacks the specific prompts that elicited statements, creating a context gap for agents reviewing their activity history.

The memory system provides good response visibility but inconsistent prompt preservation, which could impact agent learning and decision-making consistency across the experiment.