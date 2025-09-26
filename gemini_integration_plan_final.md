# Gemini API Integration - Final Simplified Plan

## Executive Summary
Add native Gemini API support with minimal complexity, explicit behavior, and a single OpenRouter fallback for resilience.

## Core Principles (Revised)
1. **Explicit Over Implicit**: No hidden conversions or auto-prefixing
2. **Clear Errors**: Tell users exactly what's wrong and how to fix it
3. **Simple Retry**: Only retry on "model not found" → OpenRouter fallback
4. **Maintain Conventions**: "/" still forces OpenRouter as originally requested

## Simplified Model Detection

```python
def detect_model_provider(model_string: str) -> Tuple[str, str]:
    """
    Simple, explicit provider detection.

    Rules:
    1. Models with "/" → Always OpenRouter (explicit selection)
    2. gemini/gemma models → Gemini API if key exists, else error
    3. gpt/o1/o3 models → OpenAI API if key exists, else error
    4. Unknown models → Try OpenAI (existing behavior)
    """
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

    # Rule 4: Unknown models - default to OpenAI
    if os.getenv("OPENAI_API_KEY"):
        return model_string, "openai"

    raise ValueError(
        f"Unknown model '{model_string}' requires OPENAI_API_KEY.\n"
        f"Solutions:\n"
        f"  1. Set OPENAI_API_KEY environment variable\n"
        f"  2. Use explicit provider prefix (e.g., 'anthropic/{model_string}') with OPENROUTER_API_KEY"
    )
```

## Minimal Retry Logic

```python
async def create_model_with_simple_retry(
    model_string: str,
    temperature: float = 0.7
) -> Tuple[Any, dict]:
    """
    Create model with simple OpenRouter fallback on "model not found" ONLY.

    NO cross-provider mapping.
    NO complex retry chains.
    Just a simple fallback to OpenRouter if the exact model isn't found.
    """
    # Get primary provider (will raise clear error if API key missing)
    processed_model, primary_provider = detect_model_provider(model_string)

    # Try primary provider
    try:
        model_config = await create_for_provider(processed_model, primary_provider, temperature)
        logger.info(f"✅ Loaded {model_string} from {primary_provider}")
        return model_config, {"provider": primary_provider}

    except ModelNotFoundError as e:
        # ONLY retry on "model not found" - not other errors
        logger.warning(f"Model {model_string} not found in {primary_provider}: {e}")

        # Simple fallback to OpenRouter if available
        if primary_provider != "openrouter" and os.getenv("OPENROUTER_API_KEY"):
            # Determine OpenRouter format
            base_model = model_string.split("/")[-1]
            if base_model.lower().startswith(("gemini", "gemma")):
                openrouter_model = f"google/{base_model}"
            elif base_model.lower().startswith(("gpt", "o1", "o3")):
                openrouter_model = f"openai/{base_model}"
            else:
                openrouter_model = base_model  # Try as-is for unknown models

            logger.info(f"🔄 Retrying with OpenRouter as {openrouter_model}...")

            try:
                model_config = await create_for_provider(openrouter_model, "openrouter", temperature)
                logger.info(f"✅ Loaded {model_string} from OpenRouter (fallback)")
                return model_config, {"provider": "openrouter", "fallback": True}
            except Exception as retry_error:
                logger.error(f"❌ OpenRouter fallback also failed: {retry_error}")
                raise  # Re-raise original error

        # No fallback available or fallback failed
        raise

    except Exception as e:
        # Any other error - don't retry, just fail with clear message
        logger.error(f"❌ Failed to load {model_string} from {primary_provider}: {e}")
        raise
```

## Gemini Client (Minimal)

```python
# utils/gemini_client.py - Only essential code
from google import genai
from functools import lru_cache

@lru_cache(maxsize=1)
def get_gemini_client():
    """Get singleton Gemini client using GEMINI_API_KEY."""
    return genai.Client()  # Uses GEMINI_API_KEY from env

class GeminiChatCompletionsModel:
    """Minimal adapter for OpenAI Agents SDK compatibility."""

    def __init__(self, model: str):
        self.model = model
        self.client = get_gemini_client()

    async def create(self, messages, **kwargs):
        # Simple message conversion (no complex mapping)
        content = self._format_messages(messages)

        # Basic parameter mapping
        config = {}
        if 'temperature' in kwargs:
            config['temperature'] = kwargs['temperature']

        # Call Gemini API
        response = await self._call_gemini(content, config)

        # Return OpenAI-compatible format
        return self._format_response(response)
```

## Clear User Documentation

```markdown
# Model Configuration Guide

## Simple Rules

### Native API (Best Performance)
```yaml
# Requires GEMINI_API_KEY
model: gemini-2.5-flash

# Requires OPENAI_API_KEY
model: gpt-4o
```

### OpenRouter (Universal)
```yaml
# Requires OPENROUTER_API_KEY
model: google/gemini-2.5-flash
model: openai/gpt-4o
model: anthropic/claude-3
```

## What Happens When

| Your Config | Available Keys | Result |
|-------------|----------------|---------|
| `gemini-2.5-flash` | GEMINI_API_KEY | ✅ Uses native Gemini |
| `gemini-2.5-flash` | Only OPENROUTER_API_KEY | ❌ Error: Set GEMINI_API_KEY or use `google/gemini-2.5-flash` |
| `gpt-4o` | OPENAI_API_KEY | ✅ Uses native OpenAI |
| `gpt-4o` | Only OPENROUTER_API_KEY | ❌ Error: Set OPENAI_API_KEY or use `openai/gpt-4o` |
| `google/gemini-2.5-flash` | OPENROUTER_API_KEY | ✅ Uses OpenRouter |

## Simple Retry Behavior

**ONLY on "model not found" errors:**
- If `gemini-2.5-flash` not found in Gemini → tries `google/gemini-2.5-flash` via OpenRouter
- If `gpt-4o` not found in OpenAI → tries `openai/gpt-4o` via OpenRouter
- Other errors → Fail immediately with clear message

## No Hidden Magic
- No automatic conversions
- No cross-provider model mapping
- Clear errors tell you exactly what to do
```

## Implementation Checklist

### Phase 1: Core (2-3 hours)
- [ ] Add `google-generativeai` to requirements.txt
- [ ] Create minimal `utils/gemini_client.py` (~50 lines)
- [ ] Update `detect_model_provider()` in `model_provider.py` (~30 lines change)

### Phase 2: Retry (1-2 hours)
- [ ] Add simple retry logic for "model not found" only
- [ ] Clear logging of retry attempts

### Phase 3: Testing (2-3 hours)
- [ ] Test with GEMINI_API_KEY only
- [ ] Test with OPENROUTER_API_KEY only
- [ ] Test retry on model not found
- [ ] Test clear error messages

### Phase 4: Documentation (1 hour)
- [ ] Update README with examples
- [ ] Create example configs
- [ ] Document environment variables

## What We're NOT Doing
❌ Cross-provider model mapping (GPT → Gemini equivalents)
❌ Hidden auto-prefixing behavior
❌ Complex retry chains
❌ Automatic fallbacks for all errors
❌ Breaking existing configurations

## Success Metrics
✅ Native Gemini works when API key present
✅ Clear errors guide users to solutions
✅ Simple retry ONLY for "model not found"
✅ "/" convention preserved for explicit OpenRouter
✅ Total new code < 150 lines

## Complexity Analysis
- **Previous Plan**: 7/10 complexity
- **This Plan**: 3/10 complexity
- **Value Delivered**: 7/10 (native Gemini performance when needed)
- **Code Changes**: ~100 lines total
- **Risk**: Low (explicit behavior, clear errors)