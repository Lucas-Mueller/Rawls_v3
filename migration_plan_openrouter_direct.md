# Migration Plan: LiteLLM → Direct OpenRouter Integration

## Overview

Replace LiteLLM-based OpenRouter integration with direct OpenRouter API calls while maintaining direct OpenAI API support and all existing functionality. This revision adopts a lower‑risk, minimal‑change approach by injecting an OpenRouter AsyncOpenAI client at agent/model construction time and removing the legacy "openrouter/" prefixing, avoiding widespread `Runner.run(..., run_config=...)` changes.

## Current Architecture Analysis

### Current Implementation
- **Provider Detection**: `"/"` in model string → treated as OpenRouter; current code prepends `"openrouter/"` and builds `LitellmModel`.
- **Model Construction Paths**:
  - `utils/model_provider.py`: returns `LitellmModel` for OpenRouter and plain `str` for OpenAI.
  - `utils/dynamic_model_capabilities.py`: constructs `LitellmModel` in temperature tests and `create_agent_with_temperature_retry(...)`.
  - Multiple call sites directly call `Runner.run(...)` without `RunConfig`.
- **Tests**: `tests/unit/test_model_provider.py` asserts `openrouter/...` prefix and mocks `LitellmModel` construction.
- **Temperature Detection**: Uses both conservative assumptions and on‑demand probes.
- **Integration Point**: `Runner.run()` everywhere; no `RunConfig` passed today.

### Dependencies
- Remove `openai-agents[litellm]` usage in favor of direct client with `openai-agents`.
- Remove all `LitellmModel` imports and usages.

## Migration Strategy

### Phase 1: Core Switch (Minimal‑Change, Recommended)

Goal: remove LiteLLM usage and prefixing, inject OpenRouter client at model/agent construction, leave all `Runner.run(...)` call sites unchanged.

#### 1.1 Add OpenRouter client helper
**File**: `utils/openrouter_client.py` (new)

```python
from __future__ import annotations
import os
from functools import lru_cache
from openai import AsyncOpenAI

@lru_cache(maxsize=1)
def get_openrouter_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
```

#### 1.2 Update provider detection (stop prefixing)
**File**: `utils/model_provider.py`

Changes:
- Remove `LitellmModel` imports/usages.
- `detect_model_provider(model_string)` should:
  - Return `(model_string, True)` if it contains `"/"` (OpenRouter), else `(model_string, False)`.
  - Do not prepend `"openrouter/"`.

#### 1.3 Update model config creation
**File**: `utils/model_provider.py`

Changes:
- `create_model_config(...)` (and async variants) should:
  - For OpenAI: return the plain `str` model name.
  - For OpenRouter: return `OpenAIChatCompletionsModel(model=model_string, openai_client=get_openrouter_client())`.
- Maintain existing temperature info computation; temperature handling continues via `ModelSettings` when constructing agents.

#### 1.4 Update dynamic capability paths
**File**: `utils/dynamic_model_capabilities.py`

Changes:
- Remove `LitellmModel` imports/usages.
- In `test_temperature_support(...)` and `create_agent_with_temperature_retry(...)`, when model is OpenRouter, pass `OpenAIChatCompletionsModel(model=..., openai_client=get_openrouter_client())` instead of `LitellmModel`.
- No `RunConfig` needed; `Runner.run(...)` continues unchanged.

#### 1.5 Agents
**Files**: `experiment_agents/participant_agent.py`, `experiment_agents/utility_agent.py`

Changes:
- None to call sites; these already rely on agent construction via the dynamic capability helpers. After 1.3/1.4, they automatically use the OpenRouter client when needed.

### Phase 2: Optional Path (Provider + RunConfig)

If you prefer centralizing transport via `RunConfig` instead of injecting the client at construction time, add an `OpenRouterProvider` that returns `OpenAIChatCompletionsModel` with the cached client. Then, pass `run_config=RunConfig(model_provider=OpenRouterProvider())` at all `Runner.run(...)` call sites. This requires touching many files (`core/phase1_manager.py`, `core/two_stage_voting_manager.py`, services, agents) and is higher risk. Recommended only if you need runtime provider switching per call.

### Phase 3: Dynamic Capabilities Enhancement

#### 3.1 Update Temperature Detection
**File**: `utils/dynamic_model_capabilities.py`

**Changes**:
- Test agents now use `OpenAIChatCompletionsModel(..., openai_client=get_openrouter_client())` for OpenRouter models.
- Maintain/cache temperature results as today; error detection paths remain the same.

```python
async def test_temperature_support(model_string: str, cache: Optional[TemperatureCache] = None) -> Tuple[bool, str, Optional[Exception]]:
    """Test temperature support with provider-specific logic."""
    
    # Create appropriate provider config
    _, is_openrouter = detect_model_provider(model_string)
    run_config = None
    
    if is_openrouter:
        from utils.openrouter_provider import get_openrouter_provider  
        run_config = RunConfig(model_provider=get_openrouter_provider())
    
    # Create test agent with provider config
    test_agent = Agent(name="TempTest", instructions="Reply with 'OK'")
    
    try:
        # Test with temperature
        result = await _run_without_tracing(
            test_agent, 
            "Say OK", 
            run_config=run_config
        )
        # ... rest of testing logic
```

### Phase 4: Service Layer Updates

With the minimal‑change approach, services do not require modifications because provider selection is encapsulated in agent/model construction. If you take the Provider + RunConfig path, update every `Runner.run(...)` call to pass the appropriate `run_config` consistently across services and managers.

### Phase 5: Configuration & Environment

#### 5.1 Update Requirements
**File**: `requirements.txt`

```diff
- openai-agents[litellm]
+ openai-agents
```

#### 5.2 Environment Variables
**No Changes Required**:
- `OPENAI_API_KEY` - for OpenAI models
- `OPENROUTER_API_KEY` - for OpenRouter models

#### 5.3 Update Documentation
**Files**: `CLAUDE.md`, `docs/getting-started/installation.rst`

- Update architecture to reflect direct OpenRouter integration (no LiteLLM).
- Remove LiteLLM references in all docs.
- Document the OpenRouter client helper and environment variables.

### Phase 6: Testing & Validation

#### 6.1 Unit Tests Updates
**Files**: `tests/unit/test_model_provider.py`, etc.

- Remove `LitellmModel` imports and mocks; replace with `OpenAIChatCompletionsModel` mocks and client helper mocks.
- Update expectations: no `"openrouter/"` prefix in processed model strings.
- Update temperature detection tests to reflect the new construction path.
- If keeping feature flag (see below), add tests for both modes.

#### 6.2 Integration Tests  
**Files**: `tests/integration/test_mixed_model_experiment.py`, etc.

- Test mixed OpenAI/OpenRouter experiments
- Validate provider switching
- Test temperature detection across providers

#### 6.3 Validation Script
**File**: `validate_migration.py` (new)

```python
async def test_both_providers():
    """Test both OpenAI and OpenRouter integration."""
    
    # Test OpenAI model
    openai_result = await test_model("gpt-4")
    
    # Test OpenRouter model  
    openrouter_result = await test_model("anthropic/claude-3-sonnet")  # No prefixing
    
    # Validate both work correctly
    assert openai_result.success
    assert openrouter_result.success
```

## Implementation Checklist

### Core Implementation
- [ ] Create `utils/openrouter_client.py`
- [ ] Update `utils/model_provider.py` (remove LiteLLM; stop prefixing; construct `OpenAIChatCompletionsModel` with client)
- [ ] Update `utils/dynamic_model_capabilities.py` (remove LiteLLM usages; use client helper)
- [ ] Verify `experiment_agents/participant_agent.py` and `experiment_agents/utility_agent.py` require no changes

### Service Layer
- [ ] No changes required (minimal‑change path)
- [ ] If choosing Provider + RunConfig path, update all `Runner.run(...)` call sites across services and managers

### Infrastructure
- [ ] Update `requirements.txt` (remove `[litellm]` extra; dedupe)
- [ ] Update docs (`CLAUDE.md`, `docs/getting-started/installation.rst`)
- [ ] Create migration validation script
- [ ] Update unit tests
- [ ] Update integration tests

### Validation
- [ ] Test OpenAI model functionality (no regression)
- [ ] Test OpenRouter model functionality (feature parity)
- [ ] Test temperature detection for both providers
- [ ] Test mixed-model experiments
- [ ] Performance comparison (baseline vs migrated)

## Risk Mitigation

### Backward Compatibility
- Keep existing model string format (`"provider/model"`) but stop adding the `"openrouter/"` prefix.
- Maintain all existing configuration options.
- Preserve temperature detection behavior and cache usage.

### Rollback Strategy
- Feature flag: `USE_DIRECT_OPENROUTER` env var in `utils/model_provider.py` and `utils/dynamic_model_capabilities.py` to toggle between legacy `LitellmModel` and direct client.
- Keep a small compatibility shim until confidence is high; remove after bake‑in.
- Comprehensive test coverage before deployment.

### Performance Considerations
- Cache the OpenRouter `AsyncOpenAI` client (LRU singleton) to reuse connections.
- Maintain temperature detection cache and probe timeouts.

## Expected Benefits

### Reduced Dependencies
- Remove `openai-agents[litellm]` dependency
- Simpler dependency management
- Reduced bundle size

### Enhanced Control
- Direct API control over OpenRouter calls
- Better error handling and debugging
- Custom retry/timeout logic possibilities

### Improved Performance  
- Eliminate LiteLLM translation layer
- Direct OpenAI-compatible interface
- More predictable behavior

## Timeline Estimate

- **Phase 1-2**: Core provider implementation (2-3 days)
- **Phase 3-4**: Integration updates (2-3 days)  
- **Phase 5**: Configuration updates (1 day)
- **Phase 6**: Testing & validation (1-2 days)

**Total**: 4-7 days (minimal‑change path); add 2-3 days if adopting Provider + RunConfig across services

## Success Criteria

1. **Functional Parity**: All existing experiments work identically
2. **Provider Flexibility**: Seamless switching between OpenAI/OpenRouter
3. **Performance**: No regression in response times
4. **Maintainability**: Cleaner codebase without LiteLLM complexity
5. **Documentation**: Complete migration documentation

---

*This updated plan prioritizes a minimal‑change migration: remove LiteLLM and prefixing, inject an OpenRouter client at construction, and avoid widespread call‑site edits. A Provider + RunConfig option remains available if runtime provider switching per call is required.*
