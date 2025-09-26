# Gemini API Native Integration Plan

## Executive Summary
Integrate Google's Gemini API as a native model provider alongside existing OpenAI and OpenRouter support, with intelligent model detection and automatic retry mechanisms.

## Requirements Overview

### 1. Model Detection Logic
- **Gemini Models** (without `/`): `gemini-*`, `gemma-*` → Use native Gemini API
- **OpenAI Models** (without `/`): `gpt-*`, `o1-*`, `o3-*` → Use native OpenAI API
- **Any Model with `/`**: → Use OpenRouter API (including `google/gemini-*`)

### 2. Intelligent Retry Mechanism
- If OpenAI API returns "model not found" → Retry with Gemini API
- If Gemini API returns "model not found" → Retry with OpenAI API
- Log retry attempts for debugging

### 3. Integration Points

#### Core Components to Modify:
1. **`utils/model_provider.py`**:
   - Extend `detect_model_provider()` to return provider type enum
   - Add `create_gemini_model_config()` function
   - Update `create_model_config()` with Gemini support

2. **`utils/gemini_client.py`** (NEW):
   - Create singleton Gemini client wrapper
   - Handle API key from `GEMINI_API_KEY` env var
   - Provide async interface compatible with OpenAI Agents SDK

3. **`utils/gemini_model_adapter.py`** (NEW):
   - Create adapter class implementing OpenAI ChatCompletions interface
   - Map Gemini API responses to expected format
   - Handle conversation history and system prompts

4. **`utils/dynamic_model_capabilities.py`**:
   - Extend temperature testing for Gemini models
   - Add Gemini-specific capability detection

5. **`utils/intelligent_retry.py`** (NEW):
   - Implement cross-provider retry logic
   - Track retry attempts and reasons
   - Provide fallback chain: Primary → Secondary → OpenRouter

## Implementation Strategy

### Phase 1: Foundation (Provider Detection)
```python
class ModelProvider(Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"

def detect_model_provider_v2(model_string: str) -> Tuple[str, ModelProvider]:
    if "/" in model_string:
        return model_string, ModelProvider.OPENROUTER

    # Gemini/Gemma models
    if model_string.lower().startswith(("gemini", "gemma")):
        return model_string, ModelProvider.GEMINI

    # OpenAI models (gpt, o1, o3, etc.)
    if model_string.lower().startswith(("gpt", "o1", "o3")):
        return model_string, ModelProvider.OPENAI

    # Default fallback to OpenAI for unknown models
    return model_string, ModelProvider.OPENAI
```

### Phase 2: Gemini Client Integration
```python
# utils/gemini_client.py
from google import genai
from functools import lru_cache

@lru_cache(maxsize=1)
def get_gemini_client():
    return genai.Client()  # Uses GEMINI_API_KEY env var

class GeminiChatCompletionsModel:
    """Adapter to make Gemini API compatible with OpenAI Agents SDK."""
    def __init__(self, model: str, client=None):
        self.model = model
        self.client = client or get_gemini_client()

    async def create(self, messages, **kwargs):
        # Convert OpenAI format to Gemini format
        # Handle system prompts, conversation history
        # Return OpenAI-compatible response
```

### Phase 3: Intelligent Retry Mechanism
```python
async def create_model_with_retry(model_string: str, temperature: float = 0.7):
    primary_provider = detect_model_provider_v2(model_string)

    try:
        return await create_model_for_provider(model_string, primary_provider, temperature)
    except ModelNotFoundError as e:
        # Intelligent retry logic
        if primary_provider == ModelProvider.OPENAI:
            logger.info(f"Model {model_string} not found in OpenAI, trying Gemini...")
            try:
                return await create_model_for_provider(model_string, ModelProvider.GEMINI, temperature)
            except:
                logger.info(f"Model {model_string} not found in Gemini, trying OpenRouter...")
                return await create_model_for_provider(model_string, ModelProvider.OPENROUTER, temperature)
        elif primary_provider == ModelProvider.GEMINI:
            logger.info(f"Model {model_string} not found in Gemini, trying OpenAI...")
            try:
                return await create_model_for_provider(model_string, ModelProvider.OPENAI, temperature)
            except:
                logger.info(f"Model {model_string} not found in OpenAI, trying OpenRouter...")
                return await create_model_for_provider(model_string, ModelProvider.OPENROUTER, temperature)
```

## Testing Strategy

### 1. Unit Tests
- Test provider detection for various model strings
- Test Gemini client initialization
- Test message format conversion

### 2. Integration Tests
- Test agent creation with Gemini models
- Test temperature support detection
- Test retry mechanism with mock responses

### 3. End-to-End Tests
- Run mini experiment with Gemini models
- Test mixed provider configuration (OpenAI + Gemini agents)
- Validate multilingual support

## Configuration Examples

### Pure Gemini Configuration
```yaml
agents:
  - name: Alice
    model: gemini-2.5-flash
    temperature: 0.7

utility_agent_model: gemini-2.5-flash
```

### Mixed Provider Configuration
```yaml
agents:
  - name: Alice
    model: gpt-4o           # OpenAI
  - name: Bob
    model: gemini-2.5-pro   # Gemini
  - name: Charlie
    model: anthropic/claude-3  # OpenRouter
```

### With Retry Fallback
```yaml
agents:
  - name: Alice
    model: gemini-experimental  # Will retry with OpenAI if not found

enable_cross_provider_retry: true
```

## Environment Variables

### Required:
- `GEMINI_API_KEY`: Google AI API key for Gemini models
- `OPENAI_API_KEY`: OpenAI API key (existing)
- `OPENROUTER_API_KEY`: OpenRouter API key (existing)

### Optional:
- `ENABLE_PROVIDER_RETRY`: Enable intelligent cross-provider retry (default: true)
- `PROVIDER_RETRY_LOG_LEVEL`: Logging verbosity for retry attempts

## Migration Path

1. **Backward Compatibility**: All existing configurations continue to work
2. **Gradual Adoption**: Users can mix providers in same experiment
3. **Explicit OpenRouter**: Users can force OpenRouter with `/` notation

## Success Criteria

- [x] Gemini models work with native API when specified without `/`
- [x] OpenAI models continue to work as before
- [x] OpenRouter handles all models with `/`
- [x] Intelligent retry finds models across providers
- [x] No breaking changes to existing experiments
- [x] Temperature detection works for Gemini models
- [x] Comprehensive test coverage

## Risks and Mitigations

### Risk 1: API Response Format Differences
- **Mitigation**: Create robust adapter layer with comprehensive mapping

### Risk 2: Feature Parity
- **Mitigation**: Document provider-specific limitations, graceful degradation

### Risk 3: Rate Limiting
- **Mitigation**: Implement per-provider rate limiting and backoff

## Timeline

1. **Day 1**: Foundation - Provider detection and client setup
2. **Day 2**: Integration - Adapter implementation and testing
3. **Day 3**: Retry mechanism and error handling
4. **Day 4**: Testing and documentation
5. **Day 5**: Review and deployment

## References

- [Google Generative AI Python SDK](https://googleapis.github.io/python-genai/)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [OpenAI Agents SDK](https://github.com/openai/agents-sdk)