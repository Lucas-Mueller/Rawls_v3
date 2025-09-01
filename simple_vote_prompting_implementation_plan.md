# Simple Vote Prompting Implementation Plan

## Overview

This plan replaces the current tool-based voting approach with a simple "Yes/No" prompting system at the end of each discussion round. The implementation leverages existing voting infrastructure while simplifying the entry point.

## Target Flow

```
Discussion Round Ends
        ↓
Prompt Agent: "Do you want to initiate a vote? (Yes/No)"
        ↓
If "No" → Continue Discussion
        ↓
If "Yes" → Start Voting Process:
    1. Confirmation Phase (all other agents must confirm)
    2. Secret Ballot Phase (if all confirm)
    3. Consensus Detection
    4. Continue or End Discussion based on results
```

## Current Architecture Analysis

### Existing Components to Reuse

1. **`_conduct_confirmation_phase()`** (phase2_manager.py:1621)
   - Already handles agent confirmation logic
   - Uses `utility_agent.detect_numerical_agreement()` for 1/0 parsing
   - Auto-confirms initiator, prompts others for agreement
   - Returns `True` if all agree, `False` otherwise

2. **`_conduct_secret_ballot_phase()`** (phase2_manager.py:1765)
   - Uses `TwoStageVotingManager` for structured voting
   - Handles principle selection and constraint specification
   - Performs consensus detection and result generation
   - Returns `True` if consensus reached, `False` otherwise

3. **`utility_agent.detect_numerical_agreement()`** (utility_agent.py:587)
   - Parses "1"/"0" responses reliably
   - Returns `(bool, error_message)` tuple
   - Already handles multilingual number formats

4. **`TwoStageVotingManager`** (core/two_stage_voting_manager.py)
   - Complete voting process implementation
   - Numerical validation with fallback keyword matching
   - Memory updates and logging integration
   - Consensus checking with detailed results

## Implementation Plan

### 1. Remove Tool-Based Approach

**Files to Modify:**
- `experiment_agents/tools/voting_tools.py`
- `core/phase2_manager.py`

**Changes:**
1. **Remove voting tool** from `voting_tools.py`
   - Delete the `propose_vote` function entirely
   - Remove tool state tracking in `tool_state.py`

2. **Remove tool detection logic** from `phase2_manager.py:539-569`
   - Remove `vote_tracker.check_and_clear_proposals()` calls
   - Remove `handle_vote_proposal_tool()` method calls
   - Remove tool-based voting branches in consensus detection

3. **Clean up existing voting detection methods**
   - Remove `_is_voting_trigger_phrase()` method (no longer needed)
   - Remove `_handle_complex_voting_mode()` method
   - Remove `_check_and_handle_voting()` method
   - Keep only the new prompt-based system

### 2. Add End-of-Round Vote Prompting

**Location:** `core/phase2_manager.py` in `_run_group_discussion()` method

**Implementation:**
```python
async def _prompt_for_vote_initiation(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext
) -> bool:
    """
    Ask participant if they want to initiate voting at end of discussion round.
    
    Returns:
        True if agent wants to vote, False otherwise
    """
    language_manager = self.language_manager
    vote_prompt = language_manager.get("prompts.vote_initiation_prompt")
    
    try:
        # Set interaction type for vote prompting
        context.interaction_type = "vote_prompt"
        result = await asyncio.wait_for(
            Runner.run(participant.agent, vote_prompt, context=context),
            timeout=self.settings.statement_timeout_seconds
        )
        response = result.final_output.strip()
        
        # Use numerical agreement detection (1=Yes, 0=No)
        wants_vote, parse_error = self.utility_agent.detect_numerical_agreement(response)
        
        if parse_error is not None:
            # Invalid response - default to No (continue discussion)
            self._log_warning(f"Invalid vote prompt response from {participant.name}: {parse_error}")
            return False
            
        return wants_vote
        
    except asyncio.TimeoutError:
        self._log_warning(f"Vote prompt timeout for {participant.name}")
        return False  # Default to continue discussion
```

**Integration Point:**
Add this logic at the end of each discussion round in `_run_group_discussion()`:

```python
# After all participants have made statements in the round
for participant_idx, participant in enumerate(self.participants):
    context = contexts[participant_idx]
    
    # Prompt for vote initiation
    wants_vote = await self._prompt_for_vote_initiation(participant, context)
    
    if wants_vote:
        # Start voting process using existing infrastructure
        consensus_reached = await self._conduct_voting_process(
            participant, contexts, discussion_state
        )
        
        if consensus_reached:
            # End discussion - consensus found
            return discussion_state._consensus_result
        # If no consensus, continue discussion
        break
```

### 3. Create Unified Voting Process Method

**New Method:** `_conduct_voting_process()`

```python
async def _conduct_voting_process(
    self,
    initiator: ParticipantAgent,
    contexts: List[ParticipantContext],
    discussion_state: GroupDiscussionState
) -> bool:
    """
    Conduct complete voting process using existing infrastructure.
    
    Args:
        initiator: Agent who initiated the vote
        contexts: All participant contexts
        discussion_state: Current discussion state
        
    Returns:
        True if consensus reached, False otherwise
    """
    # Mark voting as triggered
    discussion_state.vote_triggered = True
    self._voting_in_progress = True
    
    try:
        # Log voting initiation
        if self.logger:
            self.logger.start_vote_round(
                round_number=discussion_state.round_number,
                vote_type="prompted_vote",
                trigger_participant=initiator.name,
                trigger_statement=f"Responded 'Yes' to vote initiation prompt"
            )
        
        # Phase 1: Confirmation (all others must agree)
        confirmation_success = await self._conduct_confirmation_phase(
            initiator.name, 
            f"Vote initiation: {initiator.name} wants to vote", 
            contexts, 
            discussion_state
        )
        
        if not confirmation_success:
            self._log_info("Vote confirmation failed - continuing discussion")
            if self.logger:
                self.logger.complete_vote_round(
                    consensus_reached=False,
                    warnings=["Confirmation phase failed"]
                )
            return False
        
        # Phase 2: Secret Ballot
        consensus_reached = await self._conduct_secret_ballot_phase(
            contexts, discussion_state
        )
        
        # Log results
        if self.logger and discussion_state.last_vote_result:
            vote_result = discussion_state.last_vote_result
            self.logger.complete_vote_round(
                consensus_reached=vote_result.consensus_reached,
                agreed_principle=vote_result.agreed_principle.principle.value if vote_result.agreed_principle else None,
                agreed_constraint=vote_result.agreed_principle.constraint_amount if vote_result.agreed_principle else None,
                vote_counts=vote_result.vote_counts
            )
        
        return consensus_reached
        
    finally:
        self._voting_in_progress = False
```

### 4. Translation Keys

**Files to Update:** 
- `translations/english_prompts.json`
- `translations/spanish_prompts.json`  
- `translations/mandarin_prompts.json`

**New Keys:**
```json
{
  "prompts": {
    "vote_initiation_prompt": "Do you want to initiate a vote on the justice principles now? Respond with 1 for Yes or 0 for No.",
  }
}
```

**Spanish:**
```json
{
  "prompts": {
    "vote_initiation_prompt": "¿Quieres iniciar una votación sobre los principios de justicia ahora? Responde con 1 para Sí o 0 para No.",
  }
}
```

**Mandarin:**
```json
{
  "prompts": {
    "vote_initiation_prompt": "你想现在就正义原则进行投票吗？回答1表示是，0表示否。",
  }
}
```

### 5. Configuration Updates

**File:** `config/phase2_settings.py`

**Add settings:**
```python
# Vote prompting settings
vote_prompt_every_round: bool = True  # Prompt after every round vs only after round 3+
vote_prompt_timeout_seconds: float = 30.0  # Timeout for vote initiation prompts
```

### 6. Update Discussion Prompt Templates

**Modify existing prompts to remove tool references:**

1. Remove mentions of `propose_vote` tool from discussion prompts
2. Update voting instructions to refer to end-of-round prompting
3. Ensure consistency across all three languages

## Testing Strategy

### Unit Tests
1. Test `_prompt_for_vote_initiation()` with various responses
2. Test integration with existing confirmation and ballot phases  
3. Test handling of timeouts and invalid responses

### Integration Tests
1. Test complete flow from round end to vote completion
2. Test scenarios where vote is declined
3. Test scenarios where confirmation fails
4. Test scenarios where consensus is/isn't reached

## Migration Path

### Phase 1: Remove Tool System
1. Remove `propose_vote` tool and related infrastructure
2. Remove tool detection logic from phase2_manager.py
3. Run existing tests to ensure no regressions

### Phase 2: Add Prompt System  
1. Implement `_prompt_for_vote_initiation()` method
2. Add translation keys for vote prompting
3. Integrate into discussion loop

### Phase 3: Testing & Refinement
1. Run comprehensive test suite
2. Test with actual experiment configurations
3. Adjust prompting frequency and timeouts based on results

## Expected Benefits

1. **Simplicity**: Clear, predictable entry point for voting
2. **Reliability**: No complex tool detection or parsing
3. **User Control**: Agents decide when to vote, not automatic triggers
4. **Maintainability**: Reuses existing, tested voting infrastructure
5. **Multilingual**: Leverages existing translation system

## Risks and Mitigations

**Risk**: Agents may always say "No" to voting prompts
**Mitigation**: Add escalating prompts after round 3+ or configure prompting frequency

**Risk**: Translation keys may be inconsistent  
**Mitigation**: Test all three languages thoroughly during implementation

**Risk**: Performance impact from additional prompting
**Mitigation**: Use same timeout settings as existing statement collection

## Files Modified Summary

### Core Changes
- `core/phase2_manager.py`: Remove tools, add prompting logic
- `experiment_agents/tools/voting_tools.py`: Delete file or remove propose_vote
- `experiment_agents/tools/tool_state.py`: Remove vote tracking

### Translation Updates  
- `translations/english_prompts.json`: Add vote_initiation_prompt
- `translations/spanish_prompts.json`: Add vote_initiation_prompt  
- `translations/mandarin_prompts.json`: Add vote_initiation_prompt

### Configuration
- `config/phase2_settings.py`: Add vote prompting settings

### Tests
- New test files for prompt-based voting flow
- Update existing voting tests to use new system

This plan provides a clean migration path from the current tool-based system to a simpler, more reliable prompt-based approach while reusing all the existing voting infrastructure.