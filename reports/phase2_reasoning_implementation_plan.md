# Phase 2 Internal Reasoning System: Implementation Plan

## Executive Summary

This plan outlines the focused implementation to restore the two-step reasoning functionality in Phase 2 discussions. The system allows agents to engage in private internal reasoning before making public statements, enhancing the authenticity of deliberation. All required infrastructure exists but is dormant due to a simple return value bug and missing configuration.

## Current State Analysis

### ✅ Infrastructure Already Present
- **Translation Support**: Complete reasoning prompts in English, Spanish, and Mandarin
- **Method Implementation**: `build_internal_reasoning_prompt()` exists and is fully functional
- **Memory Handling**: MemoryService supports `internal_reasoning` parameter with `include_internal_reasoning` flag
- **Logging Infrastructure**: Expects reasoning content in agent logs
- **Service Architecture**: DiscussionService has all required methods

### ❌ Critical Issues Identified

1. **Return Value Bug** (Line 316 in discussion_service.py):
   ```python
   # Current (BROKEN):
   return statement, round_content
   
   # Expected by Phase2Manager (Line 288):
   statement, internal_reasoning = await self.discussion_service.get_participant_statement_with_retry(...)
   ```

2. **Missing Configuration**: Phase2Settings lacks reasoning control fields

3. **Unused Methods**: `build_internal_reasoning_prompt()` is never called

4. **Single-Step Flow**: Only one LLM call per participant instead of two

## Implementation Strategy

### Phase 1: Fix Return Value Bug (2 hours)
**Priority**: Critical - Blocks all other functionality

#### Current Problem
```python
# In DiscussionService.get_participant_statement_with_retry() - Line 316
return statement, round_content  # round_content is memory content, not reasoning
```

#### Solution
```python
# Fix return value to match expected interface
return statement, internal_reasoning  # where internal_reasoning is initially ""
```

#### Files to Modify
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/discussion_service.py`
  - Method: `get_participant_statement_with_retry()` (Line 242-329)
  - Change: Line 316 return statement

### Phase 2: Add Reasoning Configuration (4 hours)
**Priority**: High - Enables feature control

#### Configuration Fields to Add
Add to `Phase2Settings` class in `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/config/phase2_settings.py`:

```python
# Internal reasoning settings
reasoning_enabled: bool = Field(
    default=True,
    description="Enable two-step internal reasoning before public statements"
)
reasoning_timeout_seconds: int = Field(
    default=180,
    ge=10,
    le=300,
    description="Timeout for internal reasoning responses"
)
reasoning_max_retries: int = Field(
    default=2,
    ge=1,
    le=5,
    description="Maximum retry attempts for internal reasoning"
)
```

#### Helper Method to Add
```python
def should_use_reasoning(self) -> bool:
    """Determine if internal reasoning should be used."""
    return self.reasoning_enabled
```

### Phase 3: Implement Two-Step Reasoning Flow (6 hours)
**Priority**: High - Core functionality restoration

#### Method Modifications in DiscussionService

##### 3.1 Update `get_participant_statement_with_retry()` Method

**Current Method Signature** (Line 242):
```python
async def get_participant_statement_with_retry(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    discussion_state: GroupDiscussionState,
    agent_config: AgentConfiguration,
    participant_names: List[str],
    max_rounds: int,
    max_retries: Optional[int] = None
) -> Tuple[str, str]:
```

**Implementation Strategy**:
Replace the single-step flow (Lines 273-329) with two-step logic:

```python
async def get_participant_statement_with_retry(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    discussion_state: GroupDiscussionState,
    agent_config: AgentConfiguration,
    participant_names: List[str],
    max_rounds: int,
    max_retries: Optional[int] = None
) -> Tuple[str, str]:
    """
    Get participant statement with optional internal reasoning step.
    
    Returns:
        Tuple of (statement, internal_reasoning)
    """
    max_attempts = max_retries or self.settings.max_statement_retries
    timeout_seconds = self.settings.statement_timeout_seconds
    
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                self._log_info(f"Statement retry {attempt + 1}/{max_attempts} for {participant.name}")
                backoff_time = self.settings.retry_backoff_factor ** (attempt - 1)
                await asyncio.sleep(backoff_time)
            
            internal_reasoning = ""
            
            # Step 1: Internal Reasoning (if enabled)
            if self.settings.should_use_reasoning():
                internal_reasoning = await self._get_internal_reasoning(
                    participant, context, discussion_state, max_rounds
                )
            
            # Step 2: Public Statement (enhanced with reasoning)
            statement = await self._get_public_statement(
                participant, context, discussion_state, participant_names, 
                max_rounds, internal_reasoning
            )
            
            # Validate statement
            agent_language = self._get_agent_language(agent_config)
            if not self.validate_statement(statement, participant.name, agent_language):
                if attempt < max_attempts - 1:
                    self._log_warning(f"Invalid statement from {participant.name}, retrying...")
                    continue
                else:
                    raise ValueError(f"Invalid statement after {max_attempts} attempts")
            
            self._log_info(f"Successfully retrieved statement from {participant.name}")
            return statement, internal_reasoning
            
        except asyncio.TimeoutError:
            self._log_warning(f"Statement timeout for {participant.name} (attempt {attempt + 1})")
            if attempt == max_attempts - 1:
                raise
        except Exception as e:
            self._log_warning(f"Statement error for {participant.name} (attempt {attempt + 1}): {str(e)}")
            if attempt == max_attempts - 1:
                raise
    
    raise RuntimeError("Unexpected end of retry loop")
```

##### 3.2 Add New Helper Methods

```python
async def _get_internal_reasoning(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    discussion_state: GroupDiscussionState,
    max_rounds: int
) -> str:
    """
    Get internal reasoning from participant with error handling.
    
    Returns:
        Internal reasoning text, or empty string if failed/disabled
    """
    try:
        # Build reasoning prompt using existing method
        reasoning_prompt = self.build_internal_reasoning_prompt(
            discussion_state, context.round_number, max_rounds
        )
        
        # Set interaction type
        context.interaction_type = "internal_reasoning"
        
        # Execute with timeout
        result = await asyncio.wait_for(
            Runner.run(participant.agent, reasoning_prompt, context=context),
            timeout=self.settings.reasoning_timeout_seconds
        )
        
        reasoning = result.final_output.strip()
        self._log_info(f"Internal reasoning retrieved from {participant.name} ({len(reasoning)} chars)")
        return reasoning
        
    except asyncio.TimeoutError:
        self._log_warning(f"Internal reasoning timeout for {participant.name}")
        return ""
    except Exception as e:
        self._log_warning(f"Internal reasoning error for {participant.name}: {str(e)}")
        return ""

async def _get_public_statement(
    self,
    participant: ParticipantAgent,
    context: ParticipantContext,
    discussion_state: GroupDiscussionState,
    participant_names: List[str],
    max_rounds: int,
    internal_reasoning: str
) -> str:
    """
    Get public statement from participant, optionally informed by reasoning.
    
    Args:
        internal_reasoning: Internal reasoning to inform the statement (can be empty)
        
    Returns:
        Public statement text
    """
    # Build discussion prompt with reasoning (existing method handles empty reasoning)
    discussion_prompt = self.build_discussion_prompt(
        discussion_state=discussion_state,
        round_num=context.round_number,
        max_rounds=max_rounds,
        participant_names=participant_names,
        internal_reasoning=internal_reasoning
    )
    
    # Set interaction type
    context.interaction_type = "statement"
    
    # Execute with timeout
    result = await asyncio.wait_for(
        Runner.run(participant.agent, discussion_prompt, context=context),
        timeout=self.settings.statement_timeout_seconds
    )
    
    return result.final_output
```

##### 3.3 Update `build_discussion_prompt()` Method

Verify the existing method signature and ensure it properly handles the `internal_reasoning` parameter:

```python
def build_discussion_prompt(self, discussion_state: GroupDiscussionState, round_num: int, 
                          max_rounds: int, participant_names: List[str], 
                          internal_reasoning: str = "") -> str:
```

### Phase 4: Integration Points (2 hours)

#### 4.1 Update Phase2Manager Memory Updates

**File**: `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/phase2_manager.py`

**Method**: `_process_participant_statement()` (around Line 288)

Verify that the method properly passes `internal_reasoning` to MemoryService:

```python
# Line 288: This should now work correctly after fixing return values
statement, internal_reasoning = await self.discussion_service.get_participant_statement_with_retry(...)

# Ensure memory updates include reasoning when available
# (This likely already works correctly - verify integration)
```

#### 4.2 Translation Key Verification

**Files**: 
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/english_prompts.json`
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/spanish_prompts.json`
- `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/translations/mandarin_prompts.json`

**Action**: Verify all languages have `phase2_internal_reasoning` key (English confirmed present)

### Phase 5: Testing Strategy (4 hours)

#### 5.1 Unit Tests

**File**: Create `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/tests/unit/test_phase2_reasoning_restoration.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from core.services.discussion_service import DiscussionService
from config.phase2_settings import Phase2Settings
from core.models import GroupDiscussionState

class TestPhase2ReasoningRestoration:
    """Test reasoning functionality restoration."""
    
    @pytest.fixture
    def discussion_service(self):
        """Create DiscussionService with reasoning enabled."""
        settings = Phase2Settings(reasoning_enabled=True)
        return DiscussionService(
            language_manager=Mock(),
            settings=settings,
            logger=Mock()
        )
    
    @pytest.mark.asyncio
    async def test_two_step_flow_enabled(self):
        """Test that reasoning enabled produces two LLM calls."""
        # Test implementation here
        pass
    
    @pytest.mark.asyncio  
    async def test_reasoning_disabled_single_step(self):
        """Test that reasoning disabled produces one LLM call."""
        # Test implementation here
        pass
    
    @pytest.mark.asyncio
    async def test_reasoning_timeout_fallback(self):
        """Test graceful fallback when reasoning times out."""
        # Test implementation here
        pass
    
    @pytest.mark.asyncio
    async def test_return_value_format(self):
        """Test that method returns (statement, reasoning) tuple."""
        # Test implementation here
        pass
    
    def test_configuration_integration(self):
        """Test Phase2Settings reasoning configuration."""
        # Test implementation here
        pass
```

#### 5.2 Integration Tests

**File**: Create `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/tests/integration/test_phase2_reasoning_integration.py`

```python
class TestPhase2ReasoningIntegration:
    """Test reasoning integration with Phase2Manager."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_reasoning_flow(self):
        """Test complete reasoning flow in Phase2Manager."""
        # Test implementation here
        pass
    
    @pytest.mark.asyncio
    async def test_memory_service_integration(self):
        """Test reasoning appears in agent memory correctly."""
        # Test implementation here
        pass
```

## Error Handling Strategy

### Timeout Handling
- **Reasoning Timeout**: Fallback to empty reasoning, continue with statement
- **Statement Timeout**: Use existing retry logic with exponential backoff

### Validation Errors
- **Invalid Reasoning**: Log warning, use empty reasoning
- **Invalid Statement**: Use existing validation and retry logic

### Configuration Errors
- **Invalid Settings**: Use defaults with warning logs
- **Missing Translation Keys**: Graceful fallback to English

## Risk Assessment

### Low Risk
- **Backward Compatibility**: Default `reasoning_enabled=True` maintains expected behavior
- **Translation Support**: All required keys already exist
- **Memory Integration**: MemoryService already handles reasoning parameter

### Moderate Risk  
- **Performance Impact**: Double LLM calls when enabled (mitigated by configuration toggle)
- **Error Propagation**: Reasoning failures could disrupt flow (mitigated by fallback logic)

### Minimal Risk
- **Service Architecture**: Changes isolated to DiscussionService
- **Configuration**: Simple extension of existing Phase2Settings pattern

## Implementation Timeline

### Day 1 (2 hours): Critical Bug Fix
- [ ] Fix return value in `get_participant_statement_with_retry()`
- [ ] Test basic functionality restoration

### Day 2 (4 hours): Configuration  
- [ ] Add reasoning fields to Phase2Settings
- [ ] Add helper methods for configuration checks
- [ ] Verify backward compatibility

### Day 3 (6 hours): Two-Step Flow
- [ ] Implement `_get_internal_reasoning()` method
- [ ] Implement `_get_public_statement()` method  
- [ ] Update main flow logic
- [ ] Test error handling

### Day 4 (4 hours): Testing & Validation
- [ ] Create unit tests
- [ ] Create integration tests
- [ ] Verify multilingual support
- [ ] Performance testing

**Total Effort**: 16 hours over 4 days

## Configuration Examples

### Enable Reasoning (Default)
```yaml
phase2_settings:
  reasoning_enabled: true
  reasoning_timeout_seconds: 180
  reasoning_max_retries: 2
```

### Disable Reasoning (Fast Mode)
```yaml
phase2_settings:
  reasoning_enabled: false
```

## Success Metrics

1. **Functional**: Two-step flow executes correctly when enabled
2. **Performance**: Single-step flow maintains current performance when disabled  
3. **Compatibility**: Existing configurations work unchanged
4. **Quality**: Agent logs show internal reasoning when enabled
5. **Reliability**: Graceful fallback on reasoning failures

## Files to Modify

### Core Changes
1. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/core/services/discussion_service.py`
   - Method: `get_participant_statement_with_retry()` (Lines 242-329)
   - Add: `_get_internal_reasoning()` and `_get_public_statement()` methods

2. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/config/phase2_settings.py`
   - Add: Reasoning configuration fields (Lines after 165)

### Testing Files (New)
3. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/tests/unit/test_phase2_reasoning_restoration.py`
4. `/Users/lucasmuller/Desktop/Githubg/Rawls_v3/tests/integration/test_phase2_reasoning_integration.py`

## Conclusion

This implementation plan provides a focused, low-risk approach to restoring the two-step reasoning functionality. The plan leverages existing infrastructure and follows established patterns in the codebase. The critical return value bug fix enables immediate progress, while the configuration and flow restoration complete the functionality within the services-first architecture.

The implementation maintains backward compatibility, provides configurable control, and includes robust error handling. Testing ensures reliability and performance across different usage scenarios.