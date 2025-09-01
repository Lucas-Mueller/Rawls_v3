# Voting Tool Flow Fix Implementation Plan

## Problem Summary

When the `propose_vote()` tool is called by a participant agent:
1. The tool call is detected but the agent continues with their public statement
2. After the tool call, the agent is asked for another public statement (which causes the flow to break)
3. The voting process doesn't immediately notify all agents that voting has started
4. The existing confirmation and ballot phases aren't properly triggered

## Root Cause

The issue is in `phase2_manager.py` in the `_get_participant_statement_enhanced()` method. When a tool is called:
- The method returns the statement (often empty or minimal) along with tool_call_info
- The flow continues as if it was a normal statement
- The voting handler is called, but the agent who initiated the vote isn't properly notified

## Target Flow (As Requested)

1. **Group Discussion**: Agents discuss principles, can call vote via tool when ready
2. **When tool is called** (immediately after tool call):
3. **Message to all agents**: Voting has started notification
4. **Agent memory update**: All agents update memory with voting start info
5. **Confirmation Phase**: All agents (except initiator) must confirm vote
   - If not all confirm → discussion continues
   - If all confirm → proceed to secret ballot
6. **Secret Ballot**: 
   - Agents vote for principle (1-4)
   - If principle needs constraint (3 or 4) → specify amount
7. **Consensus Detection**:
   - If all agree on same principle:
     - No constraint → Success, end discussion
     - With constraint → Check if amounts match
       - Match → Success, end discussion  
       - No match → Update public log with disagreement
   - If principles differ → Update public log with no agreement

## Implementation Plan

### Phase 1: Fix Immediate Tool Call Handling
**File**: `core/phase2_manager.py`

#### 1.1 Modify `handle_vote_proposal_tool()` method
- **Add immediate notification to all agents** that voting has started
- **Update all agent memories** with voting initiation information
- **Set proper state flags** to prevent re-entry issues

```python
# Around line 1026, after logging the vote proposal
# Add notification to all agents
voting_start_message = self.language_manager.get(
    "prompts.voting_has_started",
    initiator_name=participant.name
)

# Update discussion state immediately
discussion_state.public_history += f"\n[VOTING INITIATED] {participant.name} has proposed formal voting."
discussion_state.public_history += f"\n[SYSTEM] {voting_start_message}"

# Update all agent memories with voting start
for i, context in enumerate(contexts):
    voting_memory = f"Voting has been initiated by {participant.name}. Formal voting process is starting."
    context.memory = await MemoryManager.prompt_agent_for_memory_update(
        self.participants[i], context, voting_memory, 
        memory_guidance_style=self.config.memory_guidance_style,
        language_manager=self.language_manager
    )
```

### Phase 2: Fix Agent Communication Flow
**File**: `core/phase2_manager.py`

#### 2.1 Prevent Double Statement Request
- **Modify** `_get_participant_statement_enhanced()` at line 876
- **When tool is called**, don't return the statement as normal
- **Instead**, return a special marker indicating voting was initiated

```python
# After line 876, check if voting tool was called
if tool_call_info and tool_call_info.get('tool_name') == 'propose_vote':
    # Return special marker to indicate voting initiated
    return "[VOTING_INITIATED]", internal_reasoning, tool_call_info
```

#### 2.2 Handle Special Marker in Main Loop
- **Modify** the main discussion loop around line 538
- **Check for voting initiation marker** before processing as normal statement

```python
# After line 540
if statement == "[VOTING_INITIATED]":
    # Don't add to public history as statement
    # Voting flow will be handled by _check_and_handle_voting
    # Skip normal statement processing
    pass
else:
    # Normal statement processing
    discussion_state.add_statement(participant.name, statement)
```

### Phase 3: Enhance Confirmation Phase
**File**: `core/phase2_manager.py`

#### 3.1 Fix Confirmation Message to Initiator
- **Modify** `_conduct_confirmation_phase()` at line 1719
- **Skip confirmation request** for the initiator
- **Auto-confirm** for the initiator since they proposed

```python
# Around line 1720
if participant.name == initiator_name:
    # Auto-confirm for initiator
    confirmations.append({
        'participant': participant.name,
        'response': "1 (auto-confirmed as initiator)",
        'agrees': True
    })
    discussion_state.public_history += f"\n[VOTING CONFIRMATION] {participant.name}: Confirmed (initiated vote)"
    continue
```

### Phase 4: Improve Voting Result Communication
**File**: `core/phase2_manager.py`

#### 4.1 Enhanced Result Messages
- **Modify** `_conduct_secret_ballot_phase()` at line 1869
- **Add clearer messages** for different disagreement scenarios

```python
# Around line 1873, enhance disagreement analysis
if not vote_result.consensus_reached:
    # Check if principles match but constraints differ
    principles = [v.principle for v in vote_result.votes]
    if len(set(p.value for p in principles)) == 1:
        # Same principle, different constraints
        principle_name = principles[0].value
        constraints = [v.constraint_amount for v in vote_result.votes if v.constraint_amount]
        message = f"Agreement on principle ({principle_name}) but constraint amounts differ: {constraints}"
    else:
        # Different principles
        message = f"No agreement on principles. Votes: {vote_result.vote_counts}"
    
    discussion_state.public_history += f"\n[VOTING RESULT] {message}"
```

### Phase 5: Memory Management Improvements
**File**: `core/phase2_manager.py`

#### 5.1 Add Voting Phase Memory Updates
- **Create helper method** for voting phase transitions
- **Ensure all agents** have synchronized understanding of voting state

```python
async def _update_all_memories_for_voting_phase(
    self, 
    phase_name: str,
    contexts: List[ParticipantContext],
    additional_info: str = ""
):
    """Update all participant memories for voting phase transitions."""
    for i, context in enumerate(contexts):
        memory_content = f"Voting Phase: {phase_name}. {additional_info}"
        context.memory = await MemoryManager.prompt_agent_for_memory_update(
            self.participants[i], context, memory_content,
            memory_guidance_style=self.config.memory_guidance_style,
            language_manager=self.language_manager
        )
```

## Testing Strategy

1. **Unit Test**: Test tool call detection in isolation
2. **Integration Test**: Test full voting flow from tool call to consensus
3. **Edge Cases**:
   - Re-entrant tool calls during confirmation
   - Timeout during voting phases
   - Mixed language responses

## Implementation Order

1. **Priority 1** (Critical Fix):
   - Fix double statement request (Phase 2.1, 2.2)
   - Add voting started notification (Phase 1.1)

2. **Priority 2** (Flow Enhancement):
   - Fix initiator confirmation (Phase 3.1)
   - Add memory updates for voting start (Phase 1.1)

3. **Priority 3** (Polish):
   - Enhance result messages (Phase 4.1)
   - Add memory helper (Phase 5.1)

## Existing Methods to Reuse

- `_conduct_confirmation_phase()` - Already handles confirmation logic
- `_conduct_secret_ballot_phase()` - Already handles ballot and consensus
- `TwoStageVotingManager.conduct_full_voting_process()` - Handles structured voting
- `MemoryManager.prompt_agent_for_memory_update()` - For memory updates
- `language_manager.get()` - For localized messages

## Minimal Changes Required

The fix requires minimal changes:
1. **3-4 lines** to prevent double statement request
2. **5-10 lines** to add voting notification
3. **3-5 lines** to fix initiator confirmation
4. **5-10 lines** for enhanced messages

Total: ~20-30 lines of focused changes to fix the core issue.

## Success Criteria

1. When `propose_vote()` is called, voting starts immediately
2. All agents are notified that voting has started
3. No double statement request after tool call
4. Confirmation phase works correctly
5. Consensus detection provides clear feedback
6. Discussion continues if voting fails