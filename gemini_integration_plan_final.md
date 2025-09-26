# Gemini API Integration - Final Simplified Plan

## Executive Summary
Add native Gemini API support with explicit behavior, clear errors, and NO automatic retries or fallbacks.

## Core Principles
1. **Explicit Over Implicit**: What you specify is what you get
2. **Fail Fast**: Clear, actionable error messages
3. **No Hidden Magic**: No retries, no fallbacks, no surprises
4. **Maintain Conventions**: "/" forces OpenRouter as originally requested

## Model Detection Logic (No Retries, No Rule 4)

```python
def detect_model_provider(model_string: str) -> Tuple[str, str]:
    """
    Simple, explicit provider detection.

    Rules:
    1. Models with "/" → Always OpenRouter (explicit selection)
    2. gemini/gemma models → Gemini API if key exists, else error
    3. gpt/o1/o3 models → OpenAI API if key exists, else error
    4. Unknown models → Clear error (no defaults)
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

    # Unknown models - explicit error
    raise ValueError(
        f"Unknown model '{model_string}'.\n"
        f"Solutions:\n"
        f"  1. Use explicit provider prefix (e.g., 'anthropic/{model_string}')\n"
        f"  2. Check model name spelling\n"
        f"  3. Use OpenRouter format with provider prefix"
    )
```

## Simple Model Creation (No Retries)

```python
async def create_model_config(model_string: str, temperature: float = 0.7):
    """
    Create model configuration - NO RETRIES.

    Explicit behavior: fails immediately with clear error if anything goes wrong.
    """
    from utils.model_provider import detect_model_provider
    from utils.gemini_client import GeminiChatCompletionsModel
    from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
    from utils.openrouter_client import get_openrouter_client

    # Get provider (raises clear error if API key missing)
    processed_model, provider = detect_model_provider(model_string)

    # Create appropriate model config
    if provider == "gemini":
        return GeminiChatCompletionsModel(
            model=processed_model
        )
    elif provider == "openrouter":
        return OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_openrouter_client()
        )
    else:  # openai
        return model_string  # OpenAI Agents SDK handles string directly
```

## Minimal Gemini Client

```python
# utils/gemini_client.py
"""Minimal Gemini API adapter for OpenAI Agents SDK compatibility."""

import os
import asyncio
from functools import lru_cache
from typing import List, Dict, Any

from google import genai

@lru_cache(maxsize=1)
def get_gemini_client():
    """Get singleton Gemini client using GEMINI_API_KEY."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    return genai.Client()  # Uses GEMINI_API_KEY from env

class GeminiChatCompletionsModel:
    """Minimal adapter for OpenAI Agents SDK compatibility."""

    def __init__(self, model: str):
        self.model = model
        self.client = get_gemini_client()

    def _format_messages(self, messages: List[Dict]) -> str:
        """Convert OpenAI messages to Gemini format."""
        parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                parts.append(f"Instructions: {content}")
            elif role == 'assistant':
                parts.append(f"Assistant: {content}")
            else:
                parts.append(f"User: {content}")
        return "\n\n".join(parts)

    async def create(self, messages: List[Dict], **kwargs):
        """Create completion via Gemini API."""
        # Format messages
        content = self._format_messages(messages)

        # Build config
        config = {}
        if 'temperature' in kwargs:
            config['temperature'] = kwargs['temperature']
        if 'max_tokens' in kwargs:
            config['max_output_tokens'] = kwargs['max_tokens']

        # Call Gemini (sync call in executor for async compatibility)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=content,
                config=config if config else None
            )
        )

        # Return OpenAI-compatible format
        return {
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': response.text
                },
                'finish_reason': 'stop'
            }]
        }
```

## Clear User Documentation

```markdown
# Model Configuration Guide

## Simple, Explicit Rules

### Native APIs (Fastest)
```yaml
# Requires GEMINI_API_KEY
agents:
  - model: gemini-2.5-flash

# Requires OPENAI_API_KEY
agents:
  - model: gpt-4o
```

### OpenRouter (Universal)
```yaml
# Requires OPENROUTER_API_KEY
agents:
  - model: google/gemini-2.5-flash
  - model: openai/gpt-4o
  - model: anthropic/claude-3
```

## What Happens - No Surprises

| Your Config | Available Keys | Result |
|-------------|----------------|---------|
| `gemini-2.5-flash` | ✅ GEMINI_API_KEY | Uses native Gemini |
| `gemini-2.5-flash` | ❌ No GEMINI_API_KEY | **Error**: Tells you to set key or use `google/gemini-2.5-flash` |
| `gpt-4o` | ✅ OPENAI_API_KEY | Uses native OpenAI |
| `gpt-4o` | ❌ No OPENAI_API_KEY | **Error**: Tells you to set key or use `openai/gpt-4o` |
| `google/gemini-2.5-flash` | ✅ OPENROUTER_API_KEY | Uses OpenRouter |
| `claude-3` | Any keys | **Error**: Unknown model, use `anthropic/claude-3` |

## NO Hidden Behavior
- ❌ No automatic retries
- ❌ No fallbacks to different providers
- ❌ No model substitutions
- ✅ Clear errors with exact solutions
- ✅ What you write is what you get

## Environment Variables
Set only what you need:
- `GEMINI_API_KEY`: For native Gemini models
- `OPENAI_API_KEY`: For native OpenAI models
- `OPENROUTER_API_KEY`: For any model via OpenRouter
```

## Implementation Checklist

### Phase 1: Core Implementation (2 hours)
- [ ] Add `google-generativeai` to requirements.txt
- [ ] Create minimal `utils/gemini_client.py` (~60 lines)
- [ ] Update `detect_model_provider()` in `model_provider.py` (~20 lines change)
- [ ] Update `create_model_config()` to handle Gemini (~10 lines)

### Phase 2: Integration (1 hour)
- [ ] Update `dynamic_model_capabilities.py` for Gemini temperature testing
- [ ] Ensure clean error messages propagate to users

### Phase 3: Testing (2 hours)
- [ ] Test with GEMINI_API_KEY only
- [ ] Test with no GEMINI_API_KEY (verify error message)
- [ ] Test with OPENROUTER_API_KEY fallback
- [ ] Test unknown models (verify clear error)

### Phase 4: Documentation (30 minutes)
- [ ] Update README examples
- [ ] Create example configs
- [ ] Document environment variables

## What We're NOT Implementing
❌ **NO retry logic** - If it fails, it fails with clear error
❌ **NO fallbacks** - Explicit provider selection only
❌ **NO Rule 4** - Unknown models get explicit error
❌ **NO auto-prefixing** - Users must be explicit
❌ **NO model mapping** - No GPT→Gemini equivalents

## Implementation Details

### File: `utils/model_provider.py`
```python
# Add to existing imports
from utils.gemini_client import GeminiChatCompletionsModel

# Replace detect_model_provider function
def detect_model_provider(model_string: str) -> Tuple[str, str]:
    # [Use code from Model Detection Logic section above]

# Update create_model_config
def create_model_config(model_string: str, temperature: float = 0.7):
    processed_model, provider = detect_model_provider(model_string)

    if provider == "gemini":
        return GeminiChatCompletionsModel(model=processed_model)
    elif provider == "openrouter":
        return OpenAIChatCompletionsModel(
            model=processed_model,
            openai_client=get_openrouter_client()
        )
    else:  # openai
        return model_string
```

### File: `requirements.txt`
```txt
# Add to existing requirements
google-generativeai>=0.8.0
```

## Success Metrics
✅ Native Gemini works when GEMINI_API_KEY present
✅ Clear errors guide users to solutions
✅ "/" convention preserved for OpenRouter
✅ No hidden behavior or surprises
✅ Total new code < 100 lines
✅ Zero breaking changes

## Complexity Analysis
- **Complexity**: 2/10 (very simple)
- **Value**: 7/10 (native Gemini performance)
- **Risk**: 1/10 (explicit behavior, no surprises)
- **Code Changes**: ~90 lines total
- **User Impact**: Positive (clear, predictable behavior)