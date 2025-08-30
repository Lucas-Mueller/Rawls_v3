# Hybrid Vote Initiation Tool: Comprehensive Implementation Plan

## Executive Summary

This document outlines the complete implementation plan for replacing the current text-based voting detection system in Phase 2 with a hybrid tool-based vote initiation mechanism. The plan covers all affected subsystems, multilingual considerations, migration strategies, and testing requirements across the entire Rawls_v3 experimental architecture.

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Affected Subsystems](#affected-subsystems)
3. [Core Implementation Changes](#core-implementation-changes)
4. [Multilingual Integration Strategy](#multilingual-integration-strategy)
5. [Configuration and Settings Updates](#configuration-and-settings-updates)
6. [Testing Strategy](#testing-strategy)
7. [Migration and Rollout Plan](#migration-and-rollout-plan)
8. [Risk Assessment and Mitigation](#risk-assessment-and-mitigation)

---

## System Architecture Overview

### Current Architecture
```
Phase 2 Discussion → Text Statement → detect_vote_intention_enhanced() → Confirmation → Secret Ballot → Consensus
```

### Proposed Hybrid Architecture
```
Phase 2 Discussion → Text Statement + Optional Tool Call → Direct to Confirmation → Secret Ballot → Consensus
```

### Tool Definition
```python
@function_tool
async def request_group_vote(reason: Optional[str] = None) -> str:
    """Request that the group proceed to formal voting on justice principles.
    
    Args:
        reason: Optional brief reason for requesting the vote
        
    Returns:
        Confirmation that vote request has been registered
    """
    return "Vote request registered. Proceeding to group confirmation."
```

---

## Affected Subsystems

### 1. Core Systems (HIGH IMPACT)

#### A. `core/phase2_manager.py`
**Changes Required:**
- Modify `_handle_complex_voting_mode()` method
- Replace `detect_vote_intention_enhanced()` call with tool call detection
- Update vote initiation logic flow
- Maintain all existing confirmation and consensus mechanisms

**Specific Code Changes:**
```python
# BEFORE (line ~1203):
vote_detection_result = await self.utility_agent.detect_vote_intention_enhanced(statement)
if vote_detection_result is None:
    return False

# AFTER:
if hasattr(result, 'tool_calls') and any(call.name == 'request_group_vote' for call in result.tool_calls):
    # Extract reason if provided
    vote_tool_call = next(call for call in result.tool_calls if call.name == 'request_group_vote')
    reason = vote_tool_call.arguments.get('reason') if vote_tool_call.arguments else None
    
    self._log_info(f"Vote tool called by {participant.name}" + (f" with reason: {reason}" if reason else ""))
    # Continue with existing confirmation logic...
else:
    return False  # No vote initiated
```

#### B. `experiment_agents/participant_agent.py`
**Changes Required:**
- Add tool configuration to agent initialization
- Update agent creation logic to include voting tool
- Ensure tool is available in both simple and complex modes

**Implementation:**
```python
# In async_init() method, add tool configuration:
from agents import function_tool

@function_tool
async def request_group_vote(reason: Optional[str] = None) -> str:
    # Implementation handled by phase2_manager
    language_manager = get_language_manager()
    return language_manager.get("tools.vote_request_confirmation")

# Add to base_kwargs:
base_kwargs = {
    "name": self.config.name,
    "instructions": lambda ctx, agent: _generate_dynamic_instructions(ctx, agent, self.config, self.experiment_config),
    "tools": [request_group_vote] if self.experiment_config and self.experiment_config.voting_detection_mode == "complex" else []
}
```

#### C. `experiment_agents/utility_agent.py`
**Changes Required:**
- Deprecate `detect_vote_intention_enhanced()` method
- Keep method for backward compatibility during transition
- Add logging for deprecated method usage

### 2. Language and Localization Systems (HIGH IMPACT)

#### A. `utils/language_manager.py`
**Changes Required:**
- Add tool description localization methods
- Update voting instruction prompts
- Add tool confirmation messages

**New Methods Needed:**
```python
def get_voting_tool_description(self) -> str:
    """Get localized description for the voting tool."""
    return self.get("tools.request_group_vote_description")

def get_voting_tool_confirmation_message(self) -> str:
    """Get localized confirmation message for vote requests."""
    return self.get("tools.vote_request_confirmation")

def get_phase2_instructions_with_tool(self, round_number: int) -> str:
    """Get Phase 2 instructions that mention the voting tool."""
    return self.get("prompts.phase2_discussion_with_tool", 
                    round_number=round_number, 
                    max_rounds=self.config.phase2_rounds)
```

#### B. Translation Files (`translations/`)
**Files to Update:**
- `english_prompts.json`
- `spanish_prompts.json` 
- `mandarin_prompts.json`

**New Keys Required:**
```json
{
  "tools": {
    "request_group_vote_description": "Request that the group proceed to formal voting on justice principles",
    "vote_request_confirmation": "Vote request registered. Proceeding to group confirmation."
  },
  "prompts": {
    "phase2_discussion_with_tool": "You can either:\n1. Continue discussion and share your reasoning\n2. Use the 'request_group_vote' tool when ready to initiate voting\n\nTo initiate voting, call the tool with: request_group_vote(reason='Brief reason for voting')",
    "phase2_tool_usage_instructions": "VOTING TOOL USAGE:\n- Call request_group_vote() when ready to vote\n- Optional reason parameter: request_group_vote(reason='We seem to have consensus')\n- All participants must confirm before voting proceeds"
  }
}
```

**Multilingual Tool Descriptions:**

**English:**
```json
{
  "tools": {
    "request_group_vote_description": "Request that the group proceed to formal voting on justice principles",
    "vote_request_confirmation": "Vote request registered. Proceeding to group confirmation."
  }
}
```

**Spanish (Direct Translation):**
```json
{
  "tools": {
    "request_group_vote_description": "Solicitar que el grupo proceda a votación formal sobre principios de justicia",
    "vote_request_confirmation": "Solicitud de votación registrada. Procediendo a confirmación grupal."
  }
}
```

**Mandarin (Direct Translation):**
```json
{
  "tools": {
    "request_group_vote_description": "请求小组进行正义原则正式投票",
    "vote_request_confirmation": "投票请求已记录。进行小组确认。"
  }
}
```

### 3. Configuration Systems (MEDIUM IMPACT)

#### A. `config/models.py`
**Changes Required:**
- No structural changes needed
- Existing `voting_detection_mode` setting determines when tool is available
- Consider adding tool-specific settings if needed

#### B. `config/phase2_settings.py`
**Potential Changes:**
- Add tool-specific timeout settings
- Add concurrent vote request handling settings

**New Settings:**
```python
class Phase2Settings(BaseModel):
    # ... existing settings ...
    
    # Tool-specific settings
    vote_tool_enabled: bool = Field(True, description="Enable voting tool for complex mode")
    concurrent_vote_requests_allowed: bool = Field(False, description="Allow multiple simultaneous vote requests")
    vote_tool_cooldown_seconds: int = Field(5, description="Cooldown between vote requests")
```

### 4. Logging and Tracking Systems (MEDIUM IMPACT)

#### A. `utils/agent_centric_logger.py`
**Changes Required:**
- Update vote detection logging methods
- Add tool call tracking
- Modify voting history structures

**New Methods:**
```python
def log_vote_tool_usage(
    self, 
    participant_name: str, 
    round_number: int, 
    reason: Optional[str] = None,
    tool_call_successful: bool = True
):
    """Log voting tool usage."""
    
def log_vote_initiation_method(self, method: str, participant_name: str):
    """Log whether vote was initiated via tool or text detection."""
    # method: "tool_call" or "text_detection" (during transition)
```

#### B. Voting History Models
**Updates to tracking structures:**
- Add `initiation_method` field to vote tracking
- Include tool call details in vote history
- Track tool usage statistics

### 5. Testing Systems (HIGH IMPACT)

#### A. Affected Test Files
**Unit Tests:**
- `tests/unit/test_phase2_vote_intention_detection.py` - Major updates needed
- `tests/unit/test_phase2_spanish_parsing.py` - Update for tool usage
- `tests/unit/test_phase2_multilingual_parsing_edge_cases.py` - Add tool tests
- `tests/unit/test_voting_history_structures.py` - Update logging tests

**Integration Tests:**
- `tests/integration/test_consensus_mechanisms.py` - Update voting flows
- `tests/integration/test_phase2_mixed_languages.py` - Tool multilingual tests
- `tests/validation/test_end_to_end_letter_rejection.py` - Update end-to-end flows

#### B. New Test Categories Needed
**Tool-Specific Tests:**
```python
class TestVotingToolIntegration:
    async def test_tool_call_triggers_voting(self):
        """Test that calling request_group_vote tool triggers voting process."""
        
    async def test_tool_with_reason_parameter(self):
        """Test tool call with reason parameter."""
        
    async def test_multiple_concurrent_tool_calls(self):
        """Test handling of multiple simultaneous vote requests."""
        
    async def test_tool_multilingual_descriptions(self):
        """Test tool descriptions in all supported languages."""
```

---

## Core Implementation Changes

### Phase 1: Tool Definition and Agent Configuration

1. **Create voting tool function** in `experiment_agents/participant_agent.py`
2. **Update agent initialization** to include tool in complex mode
3. **Add multilingual tool descriptions** to translation files

### Phase 2: Core Logic Updates

1. **Modify `_handle_complex_voting_mode()`** in `phase2_manager.py`
2. **Update vote detection logic** to check for tool calls
3. **Maintain all existing confirmation/consensus workflows**

### Phase 3: Language and UI Updates

1. **Update Phase 2 instructions** to mention tool availability
2. **Localize tool descriptions** for all supported languages
3. **Update voting prompts** to reference new initiation method

---

## Multilingual Integration Strategy

### Tool Description Localization

**Implementation Pattern:**
```python
def create_localized_voting_tool(language: str):
    language_manager = get_language_manager()
    
    @function_tool
    async def request_group_vote(reason: Optional[str] = None) -> str:
        # Tool description automatically localized by language_manager
        return language_manager.get("tools.vote_request_confirmation")
    
    # Update tool metadata based on language
    request_group_vote.__doc__ = language_manager.get("tools.request_group_vote_description")
    return request_group_vote
```

### Language-Specific Considerations

**English:**
- Clear, direct tool descriptions
- Standard parameter naming conventions

**Spanish:**
- Direct translation of English tool descriptions
- Maintain same tone and style as English

**Mandarin:**
- Direct translation of English tool descriptions
- Maintain same tone and style as English

### Prompt Updates by Language

Each language needs updates to:
1. Phase 2 discussion instructions
2. Voting explanation prompts
3. Tool usage guidance
4. Error messages for tool failures

---

## Configuration and Settings Updates

### Agent Configuration Changes

**Current `AgentConfiguration`:**
- No changes needed to existing structure
- Tool availability determined by `voting_detection_mode`

**Tool Assignment Logic:**
```python
def should_include_voting_tool(self) -> bool:
    """Determine if voting tool should be included for this agent."""
    return (
        self.experiment_config and 
        self.experiment_config.voting_detection_mode == "complex"
    )
```

### Experiment Configuration Updates

**Backward Compatibility:**
- All existing configurations work unchanged
- `voting_detection_mode` setting determines tool availability
- Simple mode continues to use preference-based consensus

**New Optional Settings:**
```python
class ExperimentConfiguration(BaseModel):
    # ... existing fields ...
    
    # Optional tool-specific settings
    vote_tool_settings: Optional[VoteToolSettings] = None

class VoteToolSettings(BaseModel):
    enabled: bool = Field(True, description="Enable voting tool")
    require_reason: bool = Field(False, description="Require reason parameter")
    cooldown_seconds: int = Field(5, description="Cooldown between requests")
```

---

## Testing Strategy

### Phase 1: Unit Tests

**New Test Categories:**
1. **Tool Function Tests**
   - Tool call detection
   - Parameter validation
   - Return value verification

2. **Multilingual Tool Tests**
   - Description localization
   - Message translation
   - Cultural appropriateness

3. **Integration Tests**
   - Tool → confirmation flow
   - Tool → secret ballot flow
   - Error handling

### Phase 2: Integration Tests

**Updated Test Flows:**
1. **Complete voting workflows with tool calls**
2. **Mixed tool/text scenarios during transition**
3. **Multilingual tool usage patterns**
4. **Error recovery and fallback scenarios**

### Phase 3: End-to-End Validation

**Full Experiment Tests:**
1. **Complex mode with tool-initiated voting**
2. **Simple mode unchanged behavior**
3. **Cross-language experiment consistency**
4. **Performance impact assessment**

---

## Migration and Rollout Plan

### Phase 1: Preparation (Week 1)
- [ ] Implement tool definition and basic infrastructure
- [ ] Add multilingual translations
- [ ] Update agent configuration logic
- [ ] Create unit tests for tool functions

### Phase 2: Core Integration (Week 2)
- [ ] Modify `phase2_manager.py` vote detection logic
- [ ] Update logging and tracking systems
- [ ] Implement error handling for tool calls
- [ ] Create integration tests

### Phase 3: Language and UI (Week 3)
- [ ] Update all Phase 2 instruction prompts
- [ ] Localize tool descriptions and messages
- [ ] Update documentation and help text
- [ ] Test multilingual workflows

### Phase 4: Testing and Validation (Week 4)
- [ ] Comprehensive testing across all languages
- [ ] Performance testing and optimization
- [ ] End-to-end validation
- [ ] User acceptance testing

### Phase 5: Deployment (Week 5)
- [ ] Deploy to staging environment
- [ ] Monitor tool usage patterns
- [ ] Performance monitoring
- [ ] Production deployment

---

## Risk Assessment and Mitigation

### High-Risk Areas

#### 1. Tool Call Detection Reliability
**Risk:** Tool calls not properly detected or processed
**Mitigation:** 
- Comprehensive error handling with fallback logging
- Tool call validation and sanitization
- Extensive testing of tool detection edge cases

#### 2. Multilingual Tool Compatibility
**Risk:** Tool descriptions or functionality inconsistent across languages
**Mitigation:**
- Direct translation validation (no cultural adaptation needed)
- Consistent tone and style across languages
- Language-specific integration tests

#### 3. Existing Workflow Disruption
**Risk:** Changes break existing confirmation/consensus mechanisms
**Mitigation:**
- Maintain all existing logic after vote detection
- Comprehensive regression testing
- Gradual rollout with monitoring

### Medium-Risk Areas

#### 1. Agent Training and Adoption
**Risk:** Agents may not use tool effectively
**Mitigation:**
- Clear tool descriptions and examples
- Instruction prompt optimization
- Usage analytics and feedback

#### 2. Performance Impact
**Risk:** Tool processing adds latency
**Mitigation:**
- Performance benchmarking
- Tool call optimization
- Resource monitoring

### Low-Risk Areas

#### 1. Configuration Compatibility
**Risk:** Existing configurations become invalid
**Mitigation:**
- Backward compatibility maintained
- Configuration validation
- Migration scripts if needed

---

## Success Metrics

### Technical Metrics
- Tool call success rate > 95%
- Vote initiation reliability improvement (baseline vs. tool-based)
- Zero breaking changes to existing simple mode workflows
- Multilingual consistency across all supported languages

### Experimental Metrics
- Voting frequency and timing consistency
- Consensus rate consistency compared to text-based detection
- Participant behavior consistency across languages
- Error rate reduction in vote detection

### Performance Metrics
- Average vote initiation time
- System responsiveness during tool calls
- Memory and CPU usage impact
- End-to-end experiment completion time

---

## Conclusion

This implementation plan provides a comprehensive roadmap for transitioning from text-based vote detection to a hybrid tool-based approach. The plan maintains all existing sophisticated consensus mechanisms while eliminating the brittleness of LLM-based text parsing.

Key benefits of this approach:
- **Surgical precision:** Only changes the most problematic component
- **Zero disruption:** Maintains all existing consensus workflows
- **Clean implementation:** Single mechanism without fallback complexity
- **Multilingual excellence:** Proper localization across all supported languages
- **Extensibility:** Foundation for future tool-based enhancements

The phased approach ensures thorough testing and validation while minimizing risk to the experimental platform's stability and scientific validity.

---

**Document Version:** 1.0  
**Created:** August 30, 2025  
**Last Updated:** August 30, 2025  
**Status:** Draft - Ready for Review