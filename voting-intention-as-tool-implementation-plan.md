# Tool-Based Voting Intention Implementation Plan

## Executive Summary

This document outlines a comprehensive plan to replace natural language voting intention detection in Phase 2 complex mode with a tool-based approach using the OpenAI Agents SDK. The plan addresses the brittleness of current text parsing by implementing a `request_group_vote` tool that agents can call directly to initiate voting, eliminating the need to monitor communication for phrases like "let's vote".

**Key Principle**: All languages (English, Spanish, Mandarin) are treated identically with only direct translations - no cultural adaptations.

## Table of Contents

1. [Problem Analysis](#problem-analysis)
2. [Proposed Architecture](#proposed-architecture)
3. [Systems-Level Impact Analysis](#systems-level-impact-analysis)
4. [Core Implementation Changes](#core-implementation-changes)
5. [Multi-Language Implementation](#multi-language-implementation)
6. [Agent Perspective & Failure Modes](#agent-perspective--failure-modes)
7. [Detailed Implementation Steps](#detailed-implementation-steps)
8. [Testing Strategy](#testing-strategy)
9. [Risk Assessment](#risk-assessment)
10. [Success Metrics](#success-metrics)

---

## Problem Analysis

### Current System Issues
1. **Brittleness**: Text parsing for voting intentions fails on variations of "let's vote"
2. **Language Complexity**: Multi-language phrase detection requires complex pattern matching
3. **False Positives**: Agents discussing voting vs. actually requesting votes
4. **Maintenance Overhead**: Need to maintain trigger phrases for English, Spanish, and Mandarin

### Current Architecture Flow
```
Agent Statement → _is_voting_trigger_phrase() → Confirmation Phase → Two-Stage Voting
```

### Pain Points
- `_is_voting_trigger_phrase()` contains hardcoded phrase lists per language (lines 1258-1285 in phase2_manager.py)
- Complex LLM-based parsing in utility agents for vote intention detection
- Inconsistent behavior across languages
- Difficult to debug when voting detection fails

---

## Proposed Architecture

### New Tool-Based Flow
```
Agent Tool Call → Tool Handler → Confirmation Phase → Two-Stage Voting
```

### Tool Definition
```python
@function_tool
async def request_group_vote(reason: Optional[str] = None) -> str:
    """Request that the group proceed to formal voting on justice principles.
    
    Args:
        reason: Optional brief explanation for why voting should begin
        
    Returns:
        Confirmation that the vote request has been received
    """
    return "Vote request registered. Proceeding to group confirmation phase."
```

### Key Benefits
- **Deterministic**: Tool calls are unambiguous, no parsing required
- **Language Agnostic**: Same tool function across all languages
- **Explicit Intent**: Agents must consciously choose to call the voting tool
- **Debuggable**: Clear tool call logs vs. text interpretation
- **Extensible**: Future voting enhancements can extend tool parameters

---

## Systems-Level Impact Analysis

### 1. Core Systems (HIGH IMPACT)

#### A. `core/phase2_manager.py`
**Current Dependency**: Lines 1249-1286 implement `_is_voting_trigger_phrase()` with hardcoded phrase lists
**Required Changes**:
- Replace phrase detection with tool call detection in `_handle_complex_voting_mode()`
- Extract tool parameters (reason) for logging
- Maintain all existing confirmation and consensus workflows

#### B. `experiment_agents/participant_agent.py`
**Current State**: No existing tool integration
**Required Changes**:
- Add tool configuration to agent initialization
- Tool availability controlled by `voting_detection_mode == "complex"`
- Update `base_kwargs` to include tools array

#### C. `core/two_stage_voting_manager.py`
**Impact**: No changes needed - tool replaces trigger detection, not the voting process

### 2. Language Management Systems (MEDIUM IMPACT)

#### A. `utils/language_manager.py`
**Current Multilingual Support**: Extensive prompt translations
**Required Changes**:
- Add tool description localization methods
- Update Phase 2 instructions to mention tool availability
- Remove voting trigger phrase translations (cleanup)

#### B. Translation Files (`translations/*.json`)
**Files Affected**: `english_prompts.json`, `spanish_prompts.json`, `mandarin_prompts.json`
**Required Changes**:
- Add tool descriptions and confirmations
- Update Phase 2 discussion prompts
- Remove obsolete trigger phrase references

### 3. Configuration Systems (LOW IMPACT)

#### A. `config/models.py`
**Impact**: No structural changes needed
**Note**: Existing `voting_detection_mode` setting determines tool availability

#### B. `config/phase2_settings.py`
**Potential Enhancement**: Add tool-specific settings for cooldowns, rate limiting

### 4. Logging and Monitoring (MEDIUM IMPACT)

#### A. `utils/agent_centric_logger.py`
**Required Changes**:
- Add tool call logging methods
- Update voting history structures to include tool usage
- Track tool vs. text-based voting initiation for analytics

---

## Core Implementation Changes

### Phase 1: Tool Definition and Registration

#### 1.1 Create Tool Function
**Location**: `experiment_agents/participant_agent.py`

```python
@function_tool
async def request_group_vote(reason: Optional[str] = None) -> str:
    """Request that the group proceed to formal voting on justice principles.
    
    Use this tool when you believe the group has discussed sufficiently and
    should proceed to formal voting to reach consensus on which justice
    principle to adopt.
    
    Args:
        reason: Optional brief explanation for why you think voting should begin
        
    Returns:
        Confirmation message that your vote request has been registered
    """
    # Tool response will be localized based on agent's language setting
    return "Vote request registered. Proceeding to group confirmation phase."
```

#### 1.2 Agent Configuration Update
**Location**: `experiment_agents/participant_agent.py` - `async_init()` method

```python
# Determine tool availability based on voting mode
tools = []
if (self.experiment_config and 
    self.experiment_config.voting_detection_mode == "complex"):
    tools.append(request_group_vote)

base_kwargs = {
    "name": self.config.name,
    "instructions": lambda ctx, agent: _generate_dynamic_instructions(
        ctx, agent, self.config, self.experiment_config, self.language_manager
    ),
    "tools": tools  # Add tools array
}
```

### Phase 2: Core Logic Updates

#### 2.1 Vote Detection Logic Replacement
**Location**: `core/phase2_manager.py` - `_handle_complex_voting_mode()` method

```python
async def _handle_complex_voting_mode(
    self,
    participant: 'ParticipantAgent',
    statement: str,
    discussion_state: GroupDiscussionState,
    contexts: List[ParticipantContext],
    result: Any  # Runner result containing potential tool calls
) -> bool:
    """Handle complex voting detection via tool calls instead of text parsing."""
    
    # Ensure we're not already in a voting process
    if self._voting_in_progress:
        self._log_info("Voting already in progress, skipping new vote detection")
        return False
    
    # Check for voting tool call instead of text parsing
    if not (hasattr(result, 'tool_calls') and result.tool_calls):
        return False  # No tool calls made
    
    # Look for request_group_vote tool call
    vote_tool_call = None
    for tool_call in result.tool_calls:
        if tool_call.name == 'request_group_vote':
            vote_tool_call = tool_call
            break
    
    if not vote_tool_call:
        return False  # No voting tool called
    
    # Extract reason parameter if provided
    reason = None
    if vote_tool_call.arguments and isinstance(vote_tool_call.arguments, dict):
        reason = vote_tool_call.arguments.get('reason')
    
    self._log_info(f"Voting tool called by {participant.name}" + 
                  (f" with reason: {reason}" if reason else ""))
    
    # Mark that voting has been triggered
    discussion_state.vote_triggered = True
    
    # Continue with existing confirmation phase logic...
    # [Rest of existing voting workflow remains unchanged]
```

#### 2.2 Statement Processing Update
**Location**: `core/phase2_manager.py` - `_get_participant_statement_with_retry()` method

```python
# Update to capture Runner result with tool calls
result = await asyncio.wait_for(
    Runner.run(participant.agent, discussion_prompt, context=context),
    timeout=self.settings.statement_timeout_seconds
)
statement = result.final_output

# Pass result to voting handler for tool call detection
consensus_via_voting = await self._handle_complex_voting_mode(
    participant, statement, discussion_state, contexts, result  # Pass result
)
```

---

## Multi-Language Implementation

**Core Principle**: All languages use identical tool functionality with only direct translations of text content.

### Tool Implementation Pattern
```python
def create_voting_tool(language_manager) -> Any:
    """Create voting tool with localized description and confirmation."""
    
    @function_tool
    async def request_group_vote(reason: Optional[str] = None) -> str:
        # Return localized confirmation message
        return language_manager.get("tools.request_group_vote.confirmation")
    
    # Set localized tool description
    request_group_vote.__doc__ = language_manager.get("tools.request_group_vote.description")
    
    return request_group_vote
```

### English Translation Keys
**File**: `translations/english_prompts.json`

```json
{
  "tools": {
    "request_group_vote": {
      "description": "Request that the group proceed to formal voting on justice principles. Use this when you believe sufficient discussion has occurred and the group should vote to reach consensus.",
      "confirmation": "Vote request registered. Proceeding to group confirmation phase."
    }
  },
  "prompts": {
    "phase2_voting_tool_instructions": "VOTING TOOL USAGE:\nWhen ready to move to formal voting, use the request_group_vote tool:\n- request_group_vote() - Request immediate voting\n- request_group_vote(reason=\"brief explanation\") - Request voting with explanation\n\nAll participants must confirm before voting proceeds."
  }
}
```

### Spanish Translation Keys (Direct Translation)
**File**: `translations/spanish_prompts.json`

```json
{
  "tools": {
    "request_group_vote": {
      "description": "Solicitar que el grupo proceda a votación formal sobre principios de justicia. Úselo cuando crea que ha habido suficiente discusión y el grupo debe votar para llegar a un consenso.",
      "confirmation": "Solicitud de votación registrada. Procediendo a fase de confirmación grupal."
    }
  },
  "prompts": {
    "phase2_voting_tool_instructions": "USO DE HERRAMIENTA DE VOTACIÓN:\nCuando esté listo para proceder a votación formal, use la herramienta request_group_vote:\n- request_group_vote() - Solicitar votación inmediata\n- request_group_vote(reason=\"breve explicación\") - Solicitar votación con explicación\n\nTodos los participantes deben confirmar antes de proceder con la votación."
  }
}
```

### Mandarin Translation Keys (Direct Translation)
**File**: `translations/mandarin_prompts.json`

```json
{
  "tools": {
    "request_group_vote": {
      "description": "请求小组进行正义原则正式投票。当您认为已进行充分讨论且小组应进行投票以达成共识时使用此工具。",
      "confirmation": "投票请求已记录。进行小组确认阶段。"
    }
  },
  "prompts": {
    "phase2_voting_tool_instructions": "投票工具使用：\n当准备进行正式投票时，使用 request_group_vote 工具：\n- request_group_vote() - 请求立即投票\n- request_group_vote(reason=\"简要说明\") - 请求投票并说明理由\n\n所有参与者必须确认后才能继续投票。"
  }
}
```

### Language Manager Updates
**Location**: `utils/language_manager.py`

```python
def get_voting_tool_description(self) -> str:
    """Get localized description for the request_group_vote tool."""
    return self.get("tools.request_group_vote.description")

def get_voting_tool_confirmation(self) -> str:
    """Get localized confirmation message for vote requests."""
    return self.get("tools.request_group_vote.confirmation")

def get_phase2_voting_tool_instructions(self) -> str:
    """Get localized voting tool usage instructions."""
    return self.get("prompts.phase2_voting_tool_instructions")
```

---

## Agent Perspective & Failure Modes

### Agent Usage Perspective

#### Successful Usage Flow
1. Agent participates in discussion
2. Agent determines group has discussed sufficiently
3. Agent calls `request_group_vote()` tool
4. Tool confirms request is registered
5. Group confirmation phase begins

#### Agent Decision Making Process
**When to use the tool:**
- After sufficient discussion rounds
- When consensus seems achievable
- When discussion becomes circular
- When time pressure exists (later rounds)

**Tool Parameters:**
- No reason: Quick voting request
- With reason: Explained voting request ("We seem aligned on principle 3")

### Failure Modes & Mitigation

#### 1. Agent Doesn't Use Tool
**Scenario**: Agent wants to vote but doesn't call the tool
**Agent Perspective**: Unclear when/how to trigger voting
**Mitigation**: 
- Clear instructions in Phase 2 prompts
- Examples of tool usage in different scenarios
- Reminder messages after round 3 if no tool calls made

#### 2. Multiple Concurrent Tool Calls
**Scenario**: Multiple agents call voting tool simultaneously
**System Impact**: Race conditions in voting initiation
**Mitigation**:
- First tool call wins, others logged but ignored
- Clear feedback to agents about voting status
- Voting lock mechanism prevents concurrent processes

#### 3. Tool Call During Ongoing Vote
**Scenario**: Agent calls voting tool while vote is in progress
**Agent Feedback**: Confusing "request ignored" message
**Mitigation**:
- Check voting status before processing tool calls
- Clear status messages: "Voting already in progress"
- Tool temporarily unavailable during active votes

#### 4. Tool Call Parsing Errors
**Scenario**: Tool call malformed or missing
**System Behavior**: Silent failure or unclear error
**Mitigation**:
- Robust tool call validation
- Clear error messages for malformed calls
- Fallback error handling with user-friendly messages

#### 5. Language Consistency Issues
**Scenario**: Tool behavior differs between languages
**Agent Confusion**: Inconsistent experimental experience
**Mitigation**:
- Identical tool function across all languages
- Only text translations, no functional differences
- Standardized tool parameters and behavior

---

## Detailed Implementation Steps

### Week 1: Foundation
- [ ] **Day 1-2**: Implement base tool function in `participant_agent.py`
- [ ] **Day 3-4**: Add tool call detection logic to `phase2_manager.py`
- [ ] **Day 5-7**: Create comprehensive unit tests for tool functionality

### Week 2: Language Integration
- [ ] **Day 1-2**: Add tool localization methods to `language_manager.py`
- [ ] **Day 3-4**: Update all translation files with direct translations
- [ ] **Day 5-7**: Implement dynamic tool description assignment

### Week 3: Integration Testing
- [ ] **Day 1-2**: Update Phase 2 prompts to include tool instructions
- [ ] **Day 3-4**: Test tool integration across all three languages
- [ ] **Day 5-7**: Integration testing with existing voting workflows

### Week 4: Logging and Monitoring
- [ ] **Day 1-2**: Add tool call logging to `agent_centric_logger.py`
- [ ] **Day 3-4**: Update voting history structures
- [ ] **Day 5-7**: Create monitoring dashboards for tool usage

### Week 5: Testing and Validation
- [ ] **Day 1-2**: End-to-end testing across all languages
- [ ] **Day 3-4**: Performance testing and optimization
- [ ] **Day 5-7**: Cross-language consistency validation

---

## Testing Strategy

### Unit Testing

#### Tool Function Tests
```python
class TestVotingToolFunctionality:
    async def test_tool_call_detection(self):
        """Test that tool calls are properly detected in Runner results."""
        
    async def test_tool_parameter_extraction(self):
        """Test extraction of reason parameter from tool calls."""
        
    async def test_tool_cross_language_consistency(self):
        """Test identical tool behavior across English, Spanish, Mandarin."""
        
    async def test_concurrent_tool_calls(self):
        """Test handling of simultaneous voting tool calls."""
```

#### Integration Tests
```python
class TestVotingToolIntegration:
    async def test_tool_to_confirmation_flow(self):
        """Test complete flow from tool call to confirmation phase."""
        
    async def test_tool_voting_vs_text_voting_equivalence(self):
        """Ensure tool-based voting produces same outcomes as text-based."""
        
    async def test_cross_language_tool_consistency(self):
        """Test identical tool behavior across all languages."""
        
    async def test_tool_error_handling(self):
        """Test tool failure modes and error recovery."""
```

### End-to-End Testing

#### Complete Experiment Flows
- **English experiment**: Tool-initiated voting with consensus
- **Spanish experiment**: Tool-initiated voting without consensus
- **Mandarin experiment**: Mixed tool and discussion rounds
- **Multi-language experiment**: Cross-language tool consistency validation

#### Cross-Language Consistency Testing
- Same tool call triggers identical system behavior
- Confirmation messages localized but functionally identical
- Voting outcomes identical across languages

---

## Risk Assessment

### High-Risk Areas

#### 1. Tool Call Processing Reliability
**Risk**: Tool calls not detected or processed correctly
**Impact**: Voting never initiated, experiment failures
**Mitigation**:
- Comprehensive tool call validation
- Robust error handling with fallbacks
- Extensive automated testing

#### 2. Cross-Language Consistency
**Risk**: Inconsistent tool behavior between languages
**Impact**: Experimental validity concerns
**Mitigation**:
- Identical tool function across all languages
- Only text translations, no functional differences
- Automated cross-language consistency tests

#### 3. Agent Adoption of Tool Usage
**Risk**: Agents don't learn to use the tool effectively
**Impact**: Reduced voting frequency, incomplete experiments
**Mitigation**:
- Clear tool usage examples in prompts
- Progressive hint system (reminders after round 3)
- Tool usage analytics and optimization

### Medium-Risk Areas

#### 1. Existing Workflow Integration
**Risk**: Tool integration breaks existing voting mechanisms
**Impact**: Confirmation/consensus phases malfunction
**Mitigation**:
- Minimal changes to post-detection workflows
- Comprehensive regression testing
- Gradual rollout with monitoring

#### 2. Performance Impact
**Risk**: Tool processing adds latency to experiments
**Impact**: Slower experiment completion
**Mitigation**:
- Lightweight tool implementation
- Performance benchmarking
- Resource monitoring

---

## Success Metrics

### Technical Success Metrics
- **Tool Call Success Rate**: >95% of tool calls processed correctly
- **Cross-Language Consistency**: 100% identical tool behavior across languages
- **Vote Initiation Reliability**: Tool-based voting initiated successfully vs. text-based baseline
- **Performance Impact**: <10% increase in average experiment duration

### Experimental Success Metrics
- **Voting Frequency**: Comparable voting rates to current system
- **Consensus Achievement**: No degradation in consensus rates
- **Agent Behavior Consistency**: Similar discussion patterns before tool usage
- **Cross-Language Equivalence**: Identical outcomes regardless of language

### Operational Success Metrics
- **Error Rate Reduction**: Fewer voting detection failures vs. text parsing
- **Debugging Efficiency**: Faster issue resolution with clear tool call logs
- **Maintenance Overhead**: Eliminated phrase pattern maintenance
- **Language Consistency**: Zero functional differences between languages

---

## Conclusion

This implementation plan provides a comprehensive roadmap for replacing brittle text-based voting detection with robust tool-based voting initiation. The approach:

- **Eliminates Parsing Brittleness**: Direct tool calls replace unreliable text analysis
- **Ensures Cross-Language Consistency**: Identical functionality with only direct translations
- **Maintains Experimental Integrity**: No changes to confirmation or consensus mechanisms
- **Provides Clear Agent Experience**: Unambiguous voting initiation mechanism
- **Enables Future Enhancements**: Foundation for additional voting tools and features

**Key Design Principle**: All languages are treated identically - only translations differ, never functionality or behavior. This ensures experimental validity and consistency across all supported languages.

---

**Document Created**: August 31, 2025  
**Status**: Ready for Implementation  
**Priority**: High - Addresses Critical System Brittleness