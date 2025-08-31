# Voting Trigger Migration Plan: From Keyword Detection to Tool Calls

## 1. Current Voting Flow

### Entry Point
- **Location**: `core/phase2_manager.py` line 536-540
- **Method**: `_handle_complex_voting_mode()`
- **Trigger Detection**: 
  - `_is_voting_trigger_phrase()` (line 1249-1286) - Simple keyword matching
  - Keywords matched against English, Spanish, and Mandarin trigger phrases
  - Once detected, initiates two-phase voting process

### Current Flow Sequence
```
1. Agent makes statement during discussion round
   ↓
2. phase2_manager._handle_complex_voting_mode() checks statement
   ↓  
3. phase2_manager._is_voting_trigger_phrase() performs keyword matching
   ↓
4. If match found → Start voting process:
   a. _conduct_confirmation_phase() - Get unanimous agreement
   b. _conduct_secret_ballot_phase() - Actual voting via TwoStageVotingManager
```

### Key Methods in Current System
- `phase2_manager._is_voting_trigger_phrase()` - Keyword detection (lines 1249-1286)
- `phase2_manager._handle_complex_voting_mode()` - Main voting orchestration (lines 1288-1365)
- `phase2_manager._conduct_confirmation_phase()` - Confirmation phase (lines 1367-1459)
- `phase2_manager._conduct_secret_ballot_phase()` - Ballot phase (lines 1461-1518)
- `utility_agent.detect_vote_intention_enhanced()` - Legacy LLM detection (lines 551-566)
- `MemoryStateCapture.extract_vote_intention()` - For logging only (lines 513-525 in agent_centric_logger.py)

## 2. Target Voting Flow

### Entry Point
- **Agent Tool Call**: Participant agents will have access to a `propose_vote` tool
- **Tool Availability**: Only during Phase 2 group discussion rounds
- **No Keyword Parsing**: Direct intent expression via tool call

### Target Flow Sequence
```
1. Agent decides to initiate voting
   ↓
2. Agent calls propose_vote() tool
   ↓
3. Tool call received by phase2_manager
   ↓  
4. Start voting process (unchanged):
   a. _conduct_confirmation_phase() - Get unanimous agreement
   b. _conduct_secret_ballot_phase() - Actual voting via TwoStageVotingManager
```

## 3. Changes Necessary

### 3.1 Add Tool to Participant Agents
**File**: `experiment_agents/participant_agent.py`
- Add `propose_vote` tool to agent's available tools during Phase 2
- Tool should only be available when `context.phase == ExperimentPhase.PHASE_2`
- Tool should be disabled during Phase 1 and Phase 2 final rankings

### 3.2 Create Tool Handler
**File**: `core/phase2_manager.py`
- Add new method `handle_vote_proposal_tool(participant, context, discussion_state)`
- This replaces the keyword detection logic
- Should set the same flags as current `_handle_complex_voting_mode()`

### 3.3 Modify Discussion Round Loop
**File**: `core/phase2_manager.py` (lines 426-606)
- Check if agent response includes tool call for `propose_vote`
- If tool called, invoke `handle_vote_proposal_tool()` instead of keyword detection
- Remove call to `_is_voting_trigger_phrase()` (line 1306)

### 3.4 Tool Definition
```python
def propose_vote():
    """
    Propose that the group proceeds to a formal vote on justice principles.
    This will initiate a confirmation phase where all participants must agree.
    """
    return {"action": "propose_vote"}
```

## 4. Implementation Plan

### Step 1: Define the Tool (New File)
Create `experiment_agents/tools/voting_tools.py`:
```python
from agents.tools import Tool

class ProposeVoteTool(Tool):
    name = "propose_vote"
    description = "Propose that the group proceeds to formal voting"
    
    def __init__(self):
        super().__init__(
            name=self.name,
            description=self.description,
            parameters={}  # No parameters needed
        )
    
    async def run(self) -> dict:
        return {"action": "propose_vote", "success": True}
```

### Step 2: Add Tool to Participant Agent
Modify `experiment_agents/participant_agent.py`:
- Import the tool
- Add tool to agent during Phase 2 initialization
- Ensure tool is context-aware (only available during group discussion)

### Step 3: Handle Tool Calls in Phase2Manager
Modify `core/phase2_manager.py`:
- Add method to check if response contains tool call
- Route tool calls to appropriate handler
- Maintain all existing voting logic after tool trigger

### Step 4: Update Prompts
Modify language manager prompts to inform agents about the tool:
- `prompts.phase2_discussion_prompt_complex` should mention the tool
- Remove references to saying "let's vote" or other keyword phrases
- Include English, Spanish and Mandarin

### Step 5: Testing
- Ensure tool is only available during Phase 2 discussion rounds
- Verify tool triggers voting process correctly
- Test that confirmation and ballot phases remain unchanged

## 5. Methods/Functions to Delete

After successful implementation, the following can be removed:

### Primary Deletions
1. **`phase2_manager._is_voting_trigger_phrase()`** (lines 1249-1286)
   - No longer needed as tool calls replace keyword detection

2. **`utility_agent.detect_vote_intention_enhanced()`** (lines 551-566)
   - Legacy LLM-based detection no longer used

### Secondary Deletions (After Verification)
3. **`MemoryStateCapture.extract_vote_intention()`** (lines 513-525 in agent_centric_logger.py)
   - Currently used for logging but can be simplified to just check for tool call

4. **Keyword trigger references in prompts**
   - Remove "say 'let's vote'" instructions from all language translations
   - Update voting reminder messages (line 789-800 in phase2_manager.py)

### Test Deletions
5. All tests related to keyword detection:
   - `tests/unit/test_phase2_vote_intention_detection.py`
   - `tests/unit/test_logger_vote_detection.py`
   - `tests/unit/test_vote_detection.py`
   - Relevant sections in integration tests

## Key Principles
- **Surgical Change**: Only modify the voting trigger mechanism
- **Preserve Logic**: All voting process logic remains unchanged
- **Backward Compatibility**: Keep configuration option to use old method during transition
- **Simplicity**: Tool call is a direct, unambiguous signal vs. parsing natural language