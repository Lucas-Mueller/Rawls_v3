# Migration Plan: Removing Structured Output for LiteLLM Compatibility

## Executive Summary

This plan outlines the systematic removal of OpenAI-specific structured output features from the Frohlich Experiment system to enable compatibility with various LLM providers via LiteLLM. The migration will transition from structured Pydantic models to enhanced text parsing while maintaining data integrity and experimental validity.

## Current State Analysis

### Structured Output Usage Points
1. **Phase 1 Manager** (`core/phase1_manager.py`):
   - Initial principle ranking: `PrincipleRankingResponse`
   - Principle application choices: `PrincipleChoiceResponse` 
   - Final principle ranking: `PrincipleRankingResponse`

2. **Phase 2 Manager** (`core/phase2_manager.py`):
   - Group statements: `GroupStatementResponse` (conditional on `reasoning_enabled`)
   - Voting responses: `VotingResponse`
   - Final rankings: `PrincipleRankingResponse`

3. **Configuration Dependencies**:
   - `reasoning_enabled` flag controls structured output usage in Phase 2
   - `create_agent_with_output_type()` function creates agents with Pydantic models

4. **Response Types** (`models/response_types.py`):
   - All structured response models currently used by OpenAI SDK
   - Utility agent parsing exists as fallback for unstructured responses

## Migration Strategy

### Phase 1: Enhanced Prompt Engineering (2-3 days)

#### 1.1 Create Standardized Response Templates
**File**: `core/prompt_templates.py` (new)
```python
# Standardized templates for reliable text parsing
RANKING_RESPONSE_TEMPLATE = """
Please provide your response in the following format:

RANKING:
1. [principle_name] - [certainty_level]
2. [principle_name] - [certainty_level]  
3. [principle_name] - [certainty_level]
4. [principle_name] - [certainty_level]

OVERALL_CERTAINTY: [very_unsure/unsure/no_opinion/sure/very_sure]

EXPLANATION:
[your detailed reasoning here]
"""
```

#### 1.2 Update Phase-Specific Instructions
**Files**: `experiment_agents/participant_agent.py`
- Modify `_get_phase_specific_instructions()` to include format requirements
- Add clear response structure guidance for each interaction type
- Remove reliance on structured output assumptions

#### 1.3 Enhance Utility Agent Parsing Capabilities
**File**: `experiment_agents/utility_agent.py`
- Strengthen regex patterns for data extraction
- Add format validation before parsing
- Implement multi-attempt parsing with progressive prompting
- Create format-specific parsing methods for each response type

### Phase 2: Remove Structured Output Dependencies (3-4 days)

#### 2.1 Update Agent Creation Pattern
**File**: `experiment_agents/participant_agent.py`
- Remove `create_agent_with_output_type()` function
- Modify `ParticipantAgent` to always use text responses
- Update agent creation to use standard OpenAI Agents without output types

#### 2.2 Update Phase Managers
**Files**: `core/phase1_manager.py` and `core/phase2_manager.py`

**Phase 1 Changes**:
```python
# Replace this pattern:
ranking_agent = create_agent_with_output_type(agent_config, PrincipleRankingResponse)
result = await Runner.run(ranking_agent, ranking_prompt, context=context)
ranking_response = result.final_output

# With this pattern:
participant_agent = create_participant_agent(agent_config)
result = await Runner.run(participant_agent.agent, ranking_prompt, context=context)
text_response = result.final_output
ranking_response = await self.utility_agent.parse_principle_ranking(text_response)
```

**Phase 2 Changes**:
- Remove `reasoning_enabled` conditional logic
- Always use text-based responses parsed by utility agent
- Update discussion flow to handle text parsing errors gracefully

#### 2.3 Enhanced Error Handling and Retry Logic
**File**: `experiment_agents/utility_agent.py`
```python
async def parse_with_retry(self, response: str, parse_method: str, max_retries: int = 3):
    """Parse response with retry logic and progressive prompting."""
    for attempt in range(max_retries):
        try:
            return await getattr(self, parse_method)(response)
        except ParseError as e:
            if attempt == max_retries - 1:
                # Final attempt with clarification request
                return await self._request_clarification(response, e, parse_method)
            # Progressive re-prompting for better format compliance
            response = await self._improve_format(response, e)
```

### Phase 3: Configuration System Updates (1-2 days)

#### 3.1 Remove `reasoning_enabled` Configuration
**File**: `config/models.py`
- Remove `reasoning_enabled` field from `AgentConfiguration`
- Update default configuration files
- Remove conditional logic throughout system

#### 3.2 Add Parsing Configuration Options
**File**: `config/models.py`
```python
class ParsingConfiguration(BaseModel):
    """Configuration for text parsing behavior."""
    max_parse_retries: int = Field(3, description="Maximum parsing retry attempts")
    strict_format_validation: bool = Field(True, description="Enforce strict response formats")
    progressive_prompting: bool = Field(True, description="Use progressive prompting for failures")
```

### Phase 4: Response Type System Refactoring (2-3 days)

#### 4.1 Convert Pydantic Models to Data Classes
**File**: `models/response_types.py`
- Keep existing models as data containers (remove BaseModel inheritance)
- Create factory functions for creating response objects from parsed text
- Maintain type safety for internal data handling

#### 4.2 Update Memory Management
**File**: `utils/memory_manager.py`
- Ensure memory updates work with text responses
- Update memory prompts to encourage structured self-documentation
- Test memory persistence across phase transitions

### Phase 5: Testing and Validation (2-3 days)

#### 5.1 Enhanced Integration Tests
**File**: `tests/integration/test_text_parsing.py` (new)
- Test all parsing scenarios with various response formats
- Validate error handling and retry mechanisms
- Test LiteLLM compatibility with different providers

#### 5.2 Response Format Validation Tests
**File**: `tests/unit/test_prompt_templates.py` (new)
- Test prompt template generation
- Validate response format guidance
- Test parsing reliability with edge cases

#### 5.3 End-to-End Experiment Validation
- Run complete experiments with text-only responses
- Compare results with structured output baseline
- Validate experimental data integrity

## System Component Impact Analysis

### 🔴 **High Impact Components (Major Changes Required)**

#### Core Experiment Management
- **`core/phase1_manager.py`**: All agent interactions need parsing layer
- **`core/phase2_manager.py`**: Remove conditional structured output logic
- **`experiment_agents/participant_agent.py`**: Complete agent creation refactor

#### Response Processing
- **`experiment_agents/utility_agent.py`**: Major parsing enhancement required
- **`models/response_types.py`**: Convert from Pydantic to data classes
- **`config/models.py`**: Remove reasoning_enabled, add parsing config

### 🟡 **Medium Impact Components (Moderate Changes)**

#### Testing Infrastructure
- **`tests/integration/`**: Update for text parsing validation
- **`tests/unit/`**: Add parsing-specific test suites
- **`run_tests.py`**: Include new parsing tests

#### Configuration System
- **`config/default_config.yaml`**: Remove reasoning_enabled settings
- **Configuration validation**: Update for new parsing parameters

### 🟢 **Low Impact Components (Minimal Changes)**

#### Utilities and Logging
- **`utils/logging_utils.py`**: No changes required - handles any data structure
- **`utils/memory_manager.py`**: Minor updates for text response handling
- **`core/distribution_generator.py`**: No changes required
- **`core/experiment_manager.py`**: No changes required - orchestrates other components

#### Data Models  
- **`models/experiment_types.py`**: No changes required
- **`models/principle_types.py`**: No changes required

## Risk Mitigation Strategies

### Data Integrity Risks
**Risk**: Parsing failures leading to data loss
**Mitigation**: 
- Implement robust retry mechanisms with progressive prompting
- Create parsing confidence scores
- Add manual intervention points for critical failures
- Maintain parsing audit logs

### Performance Risks
**Risk**: Increased latency from parsing overhead
**Mitigation**:
- Optimize parsing algorithms with efficient regex patterns
- Implement caching for repeated parsing patterns
- Use async parsing for parallel operations
- Profile parsing performance and optimize bottlenecks

### Experimental Validity Risks
**Risk**: Changed response patterns affecting experimental outcomes
**Mitigation**:
- A/B test structured vs text responses on subset of experiments
- Validate response quality metrics (completeness, accuracy)
- Monitor parsing success rates and error patterns
- Create fallback to human coding for critical parsing failures

### LiteLLM Integration Risks
**Risk**: Compatibility issues with different LLM providers
**Mitigation**:
- Test with multiple LiteLLM providers early in development
- Create provider-specific parsing adjustments if needed
- Implement provider capability detection
- Maintain OpenAI compatibility as baseline

## Success Metrics

### Technical Metrics
- **Parsing Success Rate**: >95% successful parsing on first attempt
- **Data Completeness**: >99% of required fields extracted correctly
- **Performance Impact**: <20% increase in response processing time
- **Error Recovery**: >90% of parsing failures recovered through retry logic

### Experimental Validity Metrics
- **Response Quality**: No degradation in response depth or reasoning quality
- **Data Consistency**: Parsed data matches manual validation >98% accuracy
- **Experiment Reproducibility**: Consistent results across multiple runs
- **Cross-Provider Consistency**: Results consistent across different LLM providers

## Timeline and Dependencies

### Week 1: Prompt Engineering and Parsing Enhancement
- Days 1-2: Create prompt templates and response format specifications
- Days 3-4: Enhance utility agent parsing capabilities
- Day 5: Testing and validation of parsing improvements

### Week 2: Core System Refactoring  
- Days 1-2: Remove structured output from Phase 1 Manager
- Days 3-4: Remove structured output from Phase 2 Manager
- Day 5: Update configuration system and remove reasoning_enabled

### Week 3: Response System and Testing
- Days 1-2: Convert response types and update memory management
- Days 3-4: Create comprehensive test suites
- Day 5: End-to-end validation and performance testing

### Week 4: LiteLLM Integration and Validation
- Days 1-2: Integrate LiteLLM and test multiple providers
- Days 3-4: Cross-provider validation and optimization
- Day 5: Documentation updates and deployment preparation

## Implementation Priority Order

1. **Critical Path**: Utility agent parsing enhancements → Core manager updates → Response type conversion
2. **Parallel Development**: Prompt template creation can occur alongside parsing development  
3. **Testing Integration**: Test development should occur parallel to implementation
4. **Final Validation**: LiteLLM integration testing should be the final step

## Post-Migration Benefits

### Technical Benefits
- **Provider Flexibility**: Support for any LiteLLM-compatible provider
- **Cost Optimization**: Access to cheaper LLM providers for large-scale experiments
- **Reliability**: Reduced dependency on provider-specific features
- **Maintainability**: Simplified agent creation without output type management

### Experimental Benefits
- **Broader Reach**: Ability to run experiments with different LLM capabilities
- **Comparative Studies**: Direct provider comparison within same experimental framework
- **Scalability**: Access to providers with different rate limits and pricing models
- **Research Flexibility**: Provider-specific behavior analysis opportunities

This migration plan provides a systematic approach to removing structured output dependencies while maintaining system reliability and experimental validity. The phased approach allows for incremental validation and risk mitigation throughout the transition.