# Agent-Managed Memory System Implementation Plan

## Overview
Transform the current system-generated memory system to an agent-managed memory system where agents create and update their own memory entries throughout the experiment.

## Key Changes Summary
- **From**: System string manipulation for memory updates
- **To**: Agent-generated memory via direct prompting
- **Memory Limit**: Increase from 5,000 to 50,000 characters (configurable)
- **Error Handling**: Retry mechanism with 5 attempts max, abort run on failure
- **Agent Control**: Complete freedom in memory structure and content

## Detailed Implementation Plan

### 1. Configuration Changes (`config/`)

#### 1.1 Update `default_config.yaml`
```yaml
# Replace existing memory_length with:
memory_character_limit: 50000  # New parameter name and increased limit

# Maintain all existing agent configuration
```

#### 1.2 Update `config/models.py`
```python
# In AgentConfig class, replace:
# memory_length: int = 5000
# With:
memory_character_limit: int = 50000
```

### 2. Memory Manager Overhaul (`utils/memory_manager.py`)

#### 2.1 Remove Current Methods
- Remove `update_memory()` - string manipulation logic
- Remove `add_memory_entry()` - automatic entry creation
- Remove `extract_key_learnings()` - system analysis
- Remove `create_phase_transition_summary()` - system-generated transitions
- Remove all truncation and priority logic

#### 2.2 Add New Agent-Based Memory Methods
```python
class MemoryManager:
    async def prompt_agent_for_memory_update(
        self, 
        agent: ParticipantAgent,
        context: ParticipantContext,
        round_content: str,
        max_retries: int = 5
    ) -> str:
        """Prompt agent to update their memory based on round content"""
        
    async def validate_memory_length(
        self, 
        memory: str, 
        limit: int
    ) -> tuple[bool, int]:
        """Validate memory doesn't exceed character limit"""
        
    def create_memory_update_prompt(
        self,
        current_memory: str,
        round_content: str
    ) -> str:
        """Create generic prompt for memory update"""
```

#### 2.3 Memory Update Flow
1. Present agent with current memory (n-1)
2. Present agent with round content (prompt + response + outcome)
3. Request memory update with generic prompt
4. Validate character limit
5. Retry up to 5 times if limit exceeded
6. Abort run after 5 failed attempts

### 3. Experiment Types Model Updates (`models/experiment_types.py`)

#### 3.1 Update ParticipantContext
```python
# Replace memory field usage to reflect new system
# No structural changes needed - still stores as string
# But remove any memory_length references
```

### 4. Phase Manager Updates

#### 4.1 Phase 1 Manager (`core/phase1_manager.py`)
Replace all memory update calls:

**Current Pattern:**
```python
await memory_manager.add_memory_entry(context, "ROUND 1: Chose...")
```

**New Pattern:**
```python
round_content = f"""
Prompt: {original_prompt}
Your Response: {agent_response}
Outcome: {outcome_details}
"""
context.memory = await memory_manager.prompt_agent_for_memory_update(
    agent, context, round_content
)
```

**Update Locations:**
- After initial ranking (line ~67)
- After detailed explanation (line ~75) 
- After each of 4 application rounds (lines ~98)
- After final ranking (line ~107)

#### 4.2 Phase 2 Manager (`core/phase2_manager.py`)
Similar pattern replacement for:
- After each participant statement (line ~133)
- After voting results (line ~152)
- After final earnings (line ~365)

**Remove Phase Transition Logic:**
- Remove automatic phase transition summary creation (lines 84-92)
- Let agents handle phase awareness naturally

### 5. Agent Implementation Updates (`experiment_agents/participant_agent.py`)

#### 5.1 Add Memory Update Method
```python
async def update_memory(
    self, 
    current_memory: str, 
    round_content: str
) -> str:
    """Agent updates their own memory based on round content"""
    
    prompt = f"""
    Current Memory: {current_memory}
    
    Recent Activity: {round_content}
    
    Update your memory based on what just happened.
    """
    
    response = await self.run(prompt)
    return response.content
```

#### 5.2 Remove Memory Formatting
- Remove `format_memory_prompt()` usage in agent instructions
- Agents now receive raw memory string in their context

### 6. Error Handling Implementation

#### 6.1 Memory Length Error Class
```python
class MemoryLengthExceededError(Exception):
    def __init__(self, attempted_length: int, limit: int):
        self.attempted_length = attempted_length
        self.limit = limit
        super().__init__(f"Memory length {attempted_length} exceeds limit {limit}")
```

#### 6.2 Retry Logic
```python
async def prompt_agent_for_memory_update(self, agent, context, round_content, max_retries=5):
    for attempt in range(max_retries):
        try:
            updated_memory = await agent.update_memory(context.memory, round_content)
            
            is_valid, length = await self.validate_memory_length(
                updated_memory, 
                agent.config.memory_character_limit
            )
            
            if is_valid:
                return updated_memory
            else:
                error_msg = f"Memory length {length} exceeds limit {agent.config.memory_character_limit}. Please shorten your memory."
                # Continue to next attempt with error feedback
                
        except Exception as e:
            if attempt == max_retries - 1:
                raise ExperimentAbortError(f"Agent {agent.name} failed to create valid memory after {max_retries} attempts")
```

### 7. Testing Updates

#### 7.1 Update Memory Manager Tests (`tests/unit/test_memory_manager.py`)
- Remove tests for old string manipulation methods
- Add tests for agent prompting and validation
- Add tests for retry logic and error handling
- Add tests for character limit validation

#### 7.2 Add Integration Tests
- Test complete memory update flow with mock agents
- Test error handling and retry mechanisms
- Test memory persistence across phases

### 8. Configuration Migration

#### 8.1 Backward Compatibility
- Support both `memory_length` and `memory_character_limit` in config loading
- Default `memory_character_limit` to 50,000 if neither specified
- Log warning if old parameter used

### 9. Documentation Updates

#### 9.1 Update CLAUDE.md
- Reflect new agent-managed memory system
- Update memory limit from 5,000 to 50,000 characters
- Remove references to system-generated memory entries

#### 9.2 Update Master Plan Reference
- Note deviation from "agent is asked to update memory" to direct agent management
- Clarify that agents now have complete control over memory structure

## System-Wide Impact Analysis

### 🟢 **Positive Impacts**
1. **Agent Autonomy**: Agents gain complete control over their memory representation
2. **Flexibility**: No system constraints on memory structure or content
3. **Authenticity**: Memory reflects agent's genuine understanding and priorities
4. **Scalability**: Higher character limit accommodates longer experiments

### 🟡 **Potential Challenges**
1. **Performance**: Additional API calls for each memory update
2. **Reliability**: Dependency on agent ability to manage memory effectively
3. **Debugging**: Harder to trace memory-related issues due to agent control
4. **Consistency**: No guarantee of memory format consistency across agents

### 🔴 **Risk Mitigation**
1. **Abort Mechanism**: Clear failure path after 5 retry attempts
2. **Validation**: Character limit enforcement prevents runaway memory
3. **Testing**: Comprehensive test coverage for new memory system
4. **Configuration**: Configurable limits allow tuning for different experiments

## Implementation Timeline

### Phase 1: Core Infrastructure (Day 1-2)
- Update configuration models and YAML
- Implement new MemoryManager methods
- Create error handling classes

### Phase 2: Manager Updates (Day 2-3)
- Update Phase 1 and Phase 2 managers
- Replace all memory update calls
- Remove old memory logic

### Phase 3: Agent Integration (Day 3-4)
- Add memory update method to ParticipantAgent
- Update agent instruction formatting
- Test agent memory generation

### Phase 4: Testing & Validation (Day 4-5)
- Update all tests
- Add integration tests
- Validate complete experiment flow

### Phase 5: Documentation (Day 5)
- Update CLAUDE.md and documentation
- Validate against master plan requirements

## Success Criteria
- [ ] Agents successfully create and manage their own memory
- [ ] Character limit enforcement works with retry mechanism
- [ ] Experiment runs complete without memory-related failures
- [ ] Memory persists correctly across phases
- [ ] All tests pass with new memory system
- [ ] Configuration migration works seamlessly