# DiscussionService Statement Retrieval Implementation Plan

## Issue Summary

The current Phase2Manager's `_get_participant_statement` method (lines ~939–1000) directly calls `Runner.run(...)` without retry/backoff functionality. According to the refactoring plan, this logic needs to be moved to DiscussionService with proper retry/backoff mechanisms to improve reliability and centralize discussion-related operations.

## Root Cause Analysis

### Current Implementation Problems
1. **No Retry Logic**: Direct `Runner.run()` call fails permanently on transient errors (network issues, API rate limits, timeouts)
2. **Scattered Responsibility**: Statement retrieval logic is in Phase2Manager instead of the specialized DiscussionService
3. **Inconsistent Error Handling**: Unlike VotingService which has retry patterns, statement retrieval lacks resilience
4. **No Backoff Strategy**: Immediate failures without exponential backoff for rate limiting scenarios

### Current Implementation Details
Located in `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase2_manager.py` lines 939-960:

```python
async def _get_participant_statement(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    discussion_state: GroupDiscussionState,
    agent_config: AgentConfiguration
) -> tuple[str, str]:
    """Get participant's statement for the current round."""
    
    discussion_prompt = self._build_discussion_prompt(discussion_state, context.round_number)
    
    # Always use text responses, no structured output needed for statements
    result = await Runner.run(participant.agent, discussion_prompt, context=context)
    statement = result.final_output
    
    # Create round content for memory
    language_manager = self.language_manager
    round_content = f"""{language_manager.get('memory_field_labels.prompt')} {discussion_prompt}
{language_manager.get('memory_field_labels.your_statement')} {statement}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.made_discussion_statement', round_number=context.round_number)}"""
    
    return statement, round_content
```

## Affected Components

### Primary Components
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/discussion_service.py`: Target for new method
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase2_manager.py`: Source of logic to be moved
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/config/phase2_settings.py`: Contains retry configuration

### Supporting Components
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/experiment_agents/participant_agent.py`: ParticipantAgent interface
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/models.py`: ParticipantContext and GroupDiscussionState models
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/config/__init__.py`: AgentConfiguration model

### Reference Implementation
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/voting_service.py`: Contains retry patterns (lines 90-184)

## Implementation Strategy

### Phase 1: Add Required Imports and Protocols to DiscussionService

1. **Add Required Imports**:
   ```python
   import asyncio
   from typing import List, Optional, Protocol, Tuple
   from agents import Runner
   ```

2. **Add New Protocols**:
   ```python
   class ParticipantAgent(Protocol):
       """Protocol for participant agents."""
       agent: Any  # OpenAI Agent
       name: str
   
   class ParticipantContext(Protocol):
       """Protocol for participant context."""
       round_number: int
       interaction_type: str
   
   class AgentConfiguration(Protocol):
       """Protocol for agent configuration."""
       # Add required fields as needed
   ```

### Phase 2: Implement Core Method with Retry Logic

1. **Add Method to DiscussionService**:
   ```python
   async def get_participant_statement_with_retry(
       self,
       participant: ParticipantAgent,
       context: ParticipantContext,
       discussion_state: GroupDiscussionState,
       agent_config: AgentConfiguration,
       max_retries: Optional[int] = None
   ) -> Tuple[str, str]:
       """
       Get participant statement with retry/backoff functionality.
       
       Args:
           participant: The participant agent to get statement from
           context: The participant's context for the round
           discussion_state: Current discussion state with history
           agent_config: Agent configuration settings
           max_retries: Optional override for max retry attempts
           
       Returns:
           Tuple of (statement, round_content_for_memory)
           
       Raises:
           Exception: If all retry attempts are exhausted
       """
   ```

2. **Implement Retry Logic Pattern** (based on VotingService pattern):
   ```python
   max_attempts = max_retries or self.settings.max_statement_retries
   timeout_seconds = self.settings.statement_timeout_seconds
   
   for attempt in range(max_attempts):
       try:
           # Log retry attempts
           if attempt > 0:
               self._log_info(f"Statement retry {attempt + 1}/{max_attempts} for {participant.name}")
               # Exponential backoff
               backoff_time = self.settings.retry_backoff_factor ** (attempt - 1)
               await asyncio.sleep(backoff_time)
           
           # Build discussion prompt
           discussion_prompt = self.build_discussion_prompt(
               discussion_state=discussion_state,
               round_num=context.round_number,
               max_rounds=self._get_max_rounds(),  # Need to add this method
               participant_names=self._get_participant_names()  # Need to add this method
           )
           
           # Set interaction type for statement retrieval
           context.interaction_type = "statement"
           
           # Execute with timeout
           result = await asyncio.wait_for(
               Runner.run(participant.agent, discussion_prompt, context=context),
               timeout=timeout_seconds
           )
           
           statement = result.final_output
           
           # Validate statement
           if not self.validate_statement(statement, participant.name, self._get_agent_language(agent_config)):
               if attempt < max_attempts - 1:
                   self._log_warning(f"Invalid statement from {participant.name}, retrying...")
                   continue
               else:
                   raise ValueError(f"Invalid statement after {max_attempts} attempts")
           
           # Create memory content
           round_content = self._create_statement_memory_content(
               discussion_prompt, statement, context.round_number
           )
           
           self._log_info(f"Successfully retrieved statement from {participant.name}")
           return statement, round_content
           
       except asyncio.TimeoutError:
           self._log_warning(f"Statement timeout for {participant.name} (attempt {attempt + 1})")
           if attempt == max_attempts - 1:
               raise
               
       except Exception as e:
           self._log_warning(f"Statement error for {participant.name} (attempt {attempt + 1}): {str(e)}")
           if attempt == max_attempts - 1:
               raise
   
   # Should not reach here due to raise in final attempt
   raise RuntimeError("Unexpected end of retry loop")
   ```

### Phase 3: Add Supporting Methods

1. **Memory Content Creation**:
   ```python
   def _create_statement_memory_content(self, prompt: str, statement: str, round_number: int) -> str:
       """Create formatted memory content for statement round."""
       return f"""{self._get_localized_message('memory_field_labels.prompt')} {prompt}
{self._get_localized_message('memory_field_labels.your_statement')} {statement}
{self._get_localized_message('memory_field_labels.outcome')} {self._get_localized_message('memory_outcomes.made_discussion_statement', round_number=round_number)}"""
   ```

2. **Helper Methods**:
   ```python
   def _get_max_rounds(self) -> int:
       """Get maximum rounds from settings or default."""
       # Implementation depends on how this is accessed
       return getattr(self.settings, 'phase2_rounds', 10)  # Default fallback
   
   def _get_participant_names(self) -> List[str]:
       """Get participant names - may need to be passed as parameter."""
       # This might need to be a parameter to the main method
       return []  # Placeholder
   
   def _get_agent_language(self, agent_config: AgentConfiguration) -> str:
       """Extract language from agent configuration."""
       return getattr(agent_config, 'language', 'english')  # Default fallback
   ```

### Phase 4: Update Phase2Manager Integration

1. **Modify Phase2Manager Constructor** to ensure DiscussionService is initialized:
   ```python
   def _initialize_services(self):
       """Initialize refactored services if enabled."""
       if self.settings.refactored_services_enabled:
           if not self.discussion_service:
               self.discussion_service = DiscussionService(
                   language_manager=self.language_manager,
                   settings=self.settings,
                   logger=self.logger
               )
   ```

2. **Update `_get_participant_statement` Method** to delegate to DiscussionService:
   ```python
   async def _get_participant_statement(
       self,
       participant: ParticipantAgent,
       context: ParticipantContext,
       discussion_state: GroupDiscussionState,
       agent_config: AgentConfiguration
   ) -> tuple[str, str]:
       """Get participant's statement for the current round."""
       
       # Initialize services if needed
       self._initialize_services()
       
       # Use refactored service if enabled
       if self.settings.refactored_services_enabled and self.discussion_service:
           return await self.discussion_service.get_participant_statement_with_retry(
               participant=participant,
               context=context,
               discussion_state=discussion_state,
               agent_config=agent_config
           )
       
       # Fallback to original implementation
       discussion_prompt = self._build_discussion_prompt(discussion_state, context.round_number)
       result = await Runner.run(participant.agent, discussion_prompt, context=context)
       statement = result.final_output
       
       # Create round content for memory
       language_manager = self.language_manager
       round_content = f"""{language_manager.get('memory_field_labels.prompt')} {discussion_prompt}
{language_manager.get('memory_field_labels.your_statement')} {statement}
{language_manager.get('memory_field_labels.outcome')} {language_manager.get('memory_outcomes.made_discussion_statement', round_number=context.round_number)}"""
       
       return statement, round_content
   ```

## Technical Considerations

### Configuration Integration
- **Retry Settings**: Use existing `Phase2Settings` configuration:
  - `max_statement_retries` (default: 3)
  - `retry_backoff_factor` (default: 1.5)
  - `statement_timeout_seconds` (default: 180)

### Error Handling Strategy
- **Timeout Errors**: Retry with backoff
- **Validation Errors**: Retry with different prompt if possible
- **Network/API Errors**: Retry with exponential backoff
- **Final Failure**: Propagate exception to Phase2Manager for handling

### Memory Management
- **Context Preservation**: Maintain interaction_type for proper agent behavior
- **Memory Content**: Use existing localized message patterns
- **Logging**: Follow established patterns from VotingService

### Backward Compatibility
- **Conditional Activation**: Only use new service when `refactored_services_enabled` is true
- **Fallback Implementation**: Keep original code as fallback
- **Gradual Migration**: Allow testing without breaking existing functionality

## Testing Strategy

### Unit Tests
1. **Retry Logic Testing**:
   - Test successful retrieval on first attempt
   - Test retry behavior on transient failures
   - Test final failure after exhausting retries
   - Test exponential backoff timing

2. **Statement Validation**:
   - Test valid statement acceptance
   - Test invalid statement retry behavior
   - Test language-specific validation

3. **Memory Content Creation**:
   - Test proper formatting of memory content
   - Test localized message integration

### Integration Tests
1. **Phase2Manager Integration**:
   - Test service initialization
   - Test method delegation
   - Test fallback behavior

2. **End-to-End Statement Flow**:
   - Test complete statement retrieval workflow
   - Test error recovery in real scenarios

### Error Scenario Tests
1. **Network Issues**: Simulate API timeouts and recoveries
2. **Rate Limiting**: Test backoff behavior under rate limits
3. **Invalid Responses**: Test validation and retry cycles

## Risk Assessment

### Implementation Risks
- **Complexity**: Adding retry logic increases code complexity
- **Timing**: Exponential backoff may extend experiment duration
- **Resource Usage**: Multiple retries increase API costs

### Mitigation Strategies
- **Gradual Rollout**: Use feature flag for controlled testing
- **Timeout Limits**: Reasonable maximum timeout to prevent hanging
- **Retry Limits**: Configurable maximum attempts to control costs
- **Monitoring**: Enhanced logging for troubleshooting

### Compatibility Risks
- **Interface Changes**: New protocols may need adjustment
- **Dependency Changes**: Additional imports may cause conflicts
- **Performance Impact**: Retry logic may slow happy path

## Timeline Estimation

### Phase 1: Protocol and Import Updates (2-3 hours)
- Add required imports to DiscussionService
- Define new protocols for type safety
- Update existing method signatures

### Phase 2: Core Implementation (4-6 hours)
- Implement `get_participant_statement_with_retry` method
- Add retry logic with exponential backoff
- Implement statement validation integration
- Add memory content creation helper

### Phase 3: Helper Methods and Integration (2-3 hours)
- Add supporting helper methods
- Update Phase2Manager to use new service
- Add conditional service initialization

### Phase 4: Testing and Validation (3-4 hours)
- Write comprehensive unit tests
- Add integration tests for Phase2Manager
- Test error scenarios and edge cases
- Validate backward compatibility

### Total Estimated Time: 11-16 hours

## Dependencies and Prerequisites

### Required Imports
- `asyncio`: For timeout and backoff functionality
- `agents.Runner`: For agent execution
- Type hints for ParticipantAgent, ParticipantContext, AgentConfiguration

### Configuration Dependencies
- `Phase2Settings` must include retry-related configuration
- Feature flag `refactored_services_enabled` must be available

### Infrastructure Dependencies
- Existing DiscussionService initialization in Phase2Manager
- Logging infrastructure through Logger protocol
- Language manager for localized messages

## Implementation Files Checklist

1. **Update `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/discussion_service.py`**:
   - Add imports
   - Add protocols
   - Implement `get_participant_statement_with_retry`
   - Add helper methods

2. **Update `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase2_manager.py`**:
   - Modify `_get_participant_statement` for service delegation
   - Ensure service initialization

3. **Add Tests**:
   - Unit tests for DiscussionService
   - Integration tests for Phase2Manager
   - Error scenario tests

This implementation plan provides a comprehensive strategy for moving statement retrieval logic from Phase2Manager to DiscussionService with proper retry/backoff functionality, following established patterns in the codebase while maintaining backward compatibility and robust error handling.