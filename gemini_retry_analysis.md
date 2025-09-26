# Retry Logic Analysis

## Current System Retries

After examining the codebase, the system currently has retries for:

1. **Temperature Compatibility** (`utils/dynamic_model_capabilities.py`):
   - If a model fails with temperature parameter, retry without it
   - Clear and necessary - some models don't support temperature

2. **Parsing Failures** (Phase 1 rankings):
   - Retry with more specific guidance if parsing fails
   - Helps agents provide correct format

3. **Phase 2 Operations**:
   - Statement validation retries
   - Voting confirmation retries

**Notable**: There are NO retries for model provider failures currently.

## Proposed Retry Logic - Critical Analysis

### What the Retry Would Do:
```python
# User specifies:
model: gemini-2.5-flash

# If native Gemini API fails with "model not found":
# Automatically retry with:
model: google/gemini-2.5-flash  # via OpenRouter
```

### The Problem with This Approach:

1. **Hidden Behavior**: User specifies one thing, system does another
2. **Different Characteristics**:
   - Native Gemini API: Direct, potentially faster, specific pricing
   - OpenRouter: Proxy overhead, different rate limits, markup pricing
3. **Debugging Confusion**: Users won't understand why behavior changes
4. **Cost Surprise**: OpenRouter may cost more than native API

## Better Alternative: NO RETRY

### Remove Rule 4 (as requested):
```python
def detect_model_provider(model_string: str) -> Tuple[str, str]:
    # Rule 1: Explicit OpenRouter via "/"
    if "/" in model_string:
        return model_string, "openrouter"

    model_lower = model_string.lower()

    # Rule 2: Gemini/Gemma models
    if model_lower.startswith(("gemini", "gemma")):
        if os.getenv("GEMINI_API_KEY"):
            return model_string, "gemini"
        raise ValueError(
            f"Model '{model_string}' requires GEMINI_API_KEY.\n"
            f"Solutions:\n"
            f"  1. Set GEMINI_API_KEY environment variable\n"
            f"  2. Use 'google/{model_string}' with OPENROUTER_API_KEY"
        )

    # Rule 3: OpenAI models
    if model_lower.startswith(("gpt", "o1", "o3")):
        if os.getenv("OPENAI_API_KEY"):
            return model_string, "openai"
        raise ValueError(
            f"Model '{model_string}' requires OPENAI_API_KEY.\n"
            f"Solutions:\n"
            f"  1. Set OPENAI_API_KEY environment variable\n"
            f"  2. Use 'openai/{model_string}' with OPENROUTER_API_KEY"
        )

    # NO RULE 4 - Unknown models get explicit error
    raise ValueError(
        f"Unknown model '{model_string}'.\n"
        f"Solutions:\n"
        f"  1. Use explicit provider prefix (e.g., 'anthropic/{model_string}')\n"
        f"  2. Check model name spelling"
    )
```

### Remove Retry Logic Entirely:
```python
async def create_model_config(model_string: str, temperature: float = 0.7):
    """
    Create model configuration - NO RETRIES.

    If it fails, it fails with a clear error message.
    Users should be explicit about what they want.
    """
    processed_model, provider = detect_model_provider(model_string)

    if provider == "gemini":
        return GeminiChatCompletionsModel(processed_model)
    elif provider == "openrouter":
        return OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_openrouter_client()
        )
    else:  # openai
        return model_string
```

## Why This is Better:

1. **Explicit Behavior**: What you specify is what you get
2. **Clear Errors**: Tell users exactly what's wrong
3. **No Surprises**: No hidden fallbacks or cost changes
4. **Simpler Code**: Less complexity, easier to maintain
5. **User Control**: Users choose their provider explicitly

## Examples:

### Scenario 1: User wants native Gemini
```yaml
model: gemini-2.5-flash  # Requires GEMINI_API_KEY
# If fails: Clear error with solution
```

### Scenario 2: User wants OpenRouter
```yaml
model: google/gemini-2.5-flash  # Uses OpenRouter
# Always goes to OpenRouter, no ambiguity
```

### Scenario 3: User with only OpenRouter
```yaml
# User gets clear error for:
model: gemini-2.5-flash
# Error says: Use 'google/gemini-2.5-flash' instead

# User updates config to:
model: google/gemini-2.5-flash  # Works!
```

## Conclusion:

**NO RETRY LOGIC NEEDED**

The system should:
1. Be explicit about provider selection
2. Fail fast with clear, actionable errors
3. Let users make informed choices
4. Maintain simplicity

This aligns with the principle: "Explicit is better than implicit"