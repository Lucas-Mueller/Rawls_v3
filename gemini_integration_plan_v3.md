# Gemini API Native Integration Plan v3
## Universal OpenRouter Fallback Support

## Executive Summary
Integrate Google's Gemini API as a native provider while ensuring OpenRouter serves as a universal fallback for users who only have OpenRouter API keys. Maintain the "/" convention for explicit OpenRouter selection as originally requested.

## Core Design Principles
1. **Universal OpenRouter Support**: System works with ONLY OpenRouter API key
2. **Native API Preference**: Use native APIs when available for better performance
3. **Explicit Provider Control**: "/" prefix forces OpenRouter usage
4. **Smart Fallbacks**: Automatic routing to best available provider

## Model Detection Logic (Updated)

```python
def detect_model_provider(model_string: str) -> Tuple[str, str]:
    """
    Smart provider detection with universal OpenRouter fallback.

    Priority order:
    1. Explicit OpenRouter selection (models with "/")
    2. Native API if available (Gemini or OpenAI)
    3. OpenRouter as universal fallback

    This ensures the system works even if users only have OpenRouter API key.
    """
    # Rule 1: Explicit OpenRouter selection with "/" (as originally requested)
    if "/" in model_string:
        return model_string, "openrouter"

    # Rule 2: Try native APIs first, then OpenRouter
    model_lower = model_string.lower()

    # Gemini/Gemma models
    if model_lower.startswith(("gemini", "gemma")):
        if os.getenv("GEMINI_API_KEY"):
            return model_string, "gemini"
        # Fallback to OpenRouter with auto-prefix
        if os.getenv("OPENROUTER_API_KEY"):
            return f"google/{model_string}", "openrouter"
        # No API keys available
        raise ValueError(f"No API key found for {model_string}. Set GEMINI_API_KEY or OPENROUTER_API_KEY")

    # OpenAI models (gpt, o1, o3, etc.)
    if model_lower.startswith(("gpt", "o1", "o3")):
        if os.getenv("OPENAI_API_KEY"):
            return model_string, "openai"
        # Fallback to OpenRouter with auto-prefix
        if os.getenv("OPENROUTER_API_KEY"):
            return f"openai/{model_string}", "openrouter"
        # No API keys available
        raise ValueError(f"No API key found for {model_string}. Set OPENAI_API_KEY or OPENROUTER_API_KEY")

    # Unknown models - try in order: OpenAI, OpenRouter
    if os.getenv("OPENAI_API_KEY"):
        return model_string, "openai"
    if os.getenv("OPENROUTER_API_KEY"):
        # Attempt without prefix for unknown models
        return model_string, "openrouter"

    raise ValueError(f"No API keys found. Set OPENAI_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY")
```

## Intelligent Retry Mechanism (Updated)

```python
async def create_model_with_intelligent_retry(
    model_string: str,
    temperature: float = 0.7
) -> Tuple[Any, dict]:
    """
    Create model with intelligent retry across providers.

    Retry chain ensures maximum compatibility:
    1. Primary provider (native if available)
    2. Alternative native provider (for cross-provider models)
    3. OpenRouter as universal fallback (always attempted last)
    """
    attempts = []
    base_model = model_string.split("/")[-1]  # Remove any provider prefix

    # Get primary provider
    try:
        processed_model, primary_provider = detect_model_provider(model_string)
    except ValueError as e:
        # No API keys available at all
        raise RuntimeError(f"Cannot create model {model_string}: {e}")

    # Try primary provider
    try:
        model_config = await create_for_provider(processed_model, primary_provider, temperature)
        logger.info(f"Successfully loaded {model_string} from {primary_provider}")
        return model_config, {"provider": primary_provider, "attempts": attempts}
    except Exception as e:
        attempts.append({"provider": primary_provider, "error": str(e)})
        logger.info(f"Failed to load {model_string} from {primary_provider}: {e}")

    # If primary failed and wasn't OpenRouter, try OpenRouter as fallback
    if primary_provider != "openrouter" and os.getenv("OPENROUTER_API_KEY"):
        # Determine correct prefix for OpenRouter
        if base_model.lower().startswith(("gemini", "gemma")):
            openrouter_model = f"google/{base_model}"
        elif base_model.lower().startswith(("gpt", "o1", "o3")):
            openrouter_model = f"openai/{base_model}"
        else:
            # Try without prefix for unknown models
            openrouter_model = base_model

        try:
            logger.info(f"Retrying {model_string} with OpenRouter as {openrouter_model}...")
            model_config = await create_for_provider(openrouter_model, "openrouter", temperature)
            logger.info(f"Successfully loaded {model_string} from OpenRouter (fallback)")
            return model_config, {"provider": "openrouter", "attempts": attempts, "fallback": True}
        except Exception as e:
            attempts.append({"provider": "openrouter", "error": str(e)})

    # Try cross-provider retry (e.g., GPT model name used but only Gemini API available)
    if "gpt" in model_string.lower() and os.getenv("GEMINI_API_KEY"):
        try:
            # Map GPT to equivalent Gemini model
            gemini_equivalent = map_to_gemini_equivalent(model_string)
            if gemini_equivalent:
                logger.info(f"Attempting cross-provider mapping: {model_string} -> {gemini_equivalent}")
                model_config = await create_for_provider(gemini_equivalent, "gemini", temperature)
                return model_config, {"provider": "gemini", "mapped_from": model_string, "attempts": attempts}
        except Exception as e:
            attempts.append({"provider": "gemini-mapped", "error": str(e)})

    # All retries failed
    raise RuntimeError(f"Failed to load model {model_string} from any provider. Attempts: {attempts}")
```

## Key User Scenarios

### Scenario 1: User with ONLY OpenRouter API Key
```yaml
# .env
OPENROUTER_API_KEY=your_key
# No OPENAI_API_KEY or GEMINI_API_KEY

# config.yaml - ALL of these work!
agents:
  - name: Alice
    model: gpt-4o              # Auto-routes to openai/gpt-4o via OpenRouter
  - name: Bob
    model: gemini-2.5-flash    # Auto-routes to google/gemini-2.5-flash via OpenRouter
  - name: Charlie
    model: claude-3-opus       # Routes to OpenRouter (unknown model)
```

### Scenario 2: User with Native API Keys
```yaml
# .env
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_backup_key

# config.yaml
agents:
  - name: Alice
    model: gpt-4o              # Uses native OpenAI API
  - name: Bob
    model: gemini-2.5-flash    # Uses native Gemini API
  - name: Charlie
    model: openai/gpt-4o       # Forced to OpenRouter (due to "/")
```

### Scenario 3: Mixed Setup
```yaml
# .env
GEMINI_API_KEY=your_key
OPENROUTER_API_KEY=your_key
# No OPENAI_API_KEY

# config.yaml
agents:
  - name: Alice
    model: gpt-4o              # Falls back to openai/gpt-4o via OpenRouter
  - name: Bob
    model: gemini-2.5-flash    # Uses native Gemini API
```

## Documentation Updates

```markdown
# Model Provider Selection Guide

## Quick Start

The system automatically selects the best provider based on:
1. **Explicit selection**: Use "/" to force OpenRouter (e.g., `google/gemini-2.5-flash`)
2. **API key availability**: Uses native API if key exists, else OpenRouter
3. **Universal fallback**: OpenRouter works for ALL models

## Works with ANY Setup

### Only have OpenRouter? No problem!
```yaml
# Just set OPENROUTER_API_KEY and use any model
model: gpt-4o           # Automatically uses OpenRouter
model: gemini-2.5-flash # Automatically uses OpenRouter
```

### Have native API keys? Get better performance!
```yaml
# With OPENAI_API_KEY set
model: gpt-4o           # Uses native OpenAI (faster, cheaper)

# With GEMINI_API_KEY set
model: gemini-2.5-flash # Uses native Gemini (faster, cheaper)
```

### Want explicit control? Use "/"!
```yaml
# Force OpenRouter regardless of API keys
model: openai/gpt-4o         # Always OpenRouter
model: google/gemini-2.5-flash # Always OpenRouter
```

## Provider Selection Table

| Your Setup | Model Format | What Happens |
|------------|--------------|--------------|
| Only OPENROUTER_API_KEY | `gpt-4o` | Uses `openai/gpt-4o` via OpenRouter |
| Only OPENROUTER_API_KEY | `gemini-2.5-flash` | Uses `google/gemini-2.5-flash` via OpenRouter |
| OPENAI_API_KEY + OPENROUTER_API_KEY | `gpt-4o` | Uses native OpenAI API |
| OPENAI_API_KEY + OPENROUTER_API_KEY | `gpt-4o` fails | Auto-retries with OpenRouter |
| Any setup | `google/gemini-2.5-flash` | Always OpenRouter (explicit) |

## Retry Behavior

The system automatically handles failures:
1. Tries primary provider (native if available)
2. Falls back to OpenRouter if primary fails
3. Logs all attempts for debugging

## Environment Variables

You only need to set the API keys you have:
- `OPENROUTER_API_KEY`: Universal - works with ALL models
- `OPENAI_API_KEY`: Optional - enables native OpenAI
- `GEMINI_API_KEY`: Optional - enables native Gemini

## Recommendations

1. **Minimum setup**: Just set `OPENROUTER_API_KEY`
2. **Optimal setup**: Set native keys for models you use frequently
3. **Maximum flexibility**: Set all three API keys
```

## Implementation Changes Summary

### Key Changes from v2:
1. **OpenRouter Always Works**: System functions with ONLY OpenRouter API key
2. **Auto-Prefixing**: Automatically adds provider prefix for OpenRouter
3. **Preserve "/" Convention**: As originally requested, "/" forces OpenRouter
4. **Better Error Messages**: Clear guidance on which API keys to set

### Files to Modify:
1. `utils/model_provider.py`: Smart detection with OpenRouter fallback
2. `utils/gemini_client.py`: New Gemini adapter
3. `utils/dynamic_model_capabilities.py`: Extend for Gemini
4. `requirements.txt`: Add `google-generativeai`

## Testing Matrix

| Test Case | Setup | Expected Behavior |
|-----------|-------|-------------------|
| OpenRouter Only | Only OPENROUTER_API_KEY | All models work via OpenRouter |
| Native Preference | All API keys | Native APIs used first |
| Fallback | Native fails | Auto-retry with OpenRouter |
| Explicit Router | Use "/" prefix | Always OpenRouter |
| No Keys | No API keys | Clear error message |

## Success Criteria

- ✅ System works with ONLY OpenRouter API key
- ✅ "/" convention forces OpenRouter (as originally requested)
- ✅ Native APIs used when available for performance
- ✅ Automatic fallback ensures resilience
- ✅ Clear documentation prevents confusion
- ✅ No breaking changes to existing setups