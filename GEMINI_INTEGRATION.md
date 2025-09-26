# Gemini API Integration Guide

## Overview

The Frohlich Experiment framework now supports native Google Gemini API integration alongside OpenAI and OpenRouter. This allows you to use Gemini models directly for better performance and cost efficiency.

## Quick Start

### 1. Install Dependencies

```bash
pip install google-generativeai>=0.8.0
```

### 2. Set Environment Variables

```bash
export GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Use Gemini Models

```yaml
# config.yaml
agents:
  - name: Alice
    model: gemini-2.5-flash  # Native Gemini API
    temperature: 0.7
```

## Model Provider Selection

The system automatically detects and routes models to the appropriate provider:

### Detection Rules

| Model Format | Provider | Required API Key | Example |
|-------------|----------|------------------|---------|
| `gemini-*`, `gemma-*` | Gemini | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| `gpt-*`, `o1-*`, `o3-*` | OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `provider/model` | OpenRouter | `OPENROUTER_API_KEY` | `google/gemini-2.5-flash` |

### Explicit Provider Selection

Use the `/` prefix to force OpenRouter:

```yaml
# Force OpenRouter even if GEMINI_API_KEY is set
model: google/gemini-2.5-flash
```

## Configuration Examples

### Pure Gemini Configuration

```yaml
# config/gemini_only.yaml
language: English

agents:
  - name: Alice
    model: gemini-2.5-flash
    temperature: 0.7

  - name: Bob
    model: gemini-1.5-pro
    temperature: 0.5

utility_agent_model: gemini-2.5-flash
utility_agent_temperature: 0.0
```

### Mixed Provider Configuration

```yaml
# config/mixed_providers.yaml
agents:
  # Native OpenAI
  - name: Alice
    model: gpt-4o-mini

  # Native Gemini
  - name: Bob
    model: gemini-2.5-flash

  # OpenRouter (explicit)
  - name: Charlie
    model: anthropic/claude-3
```

### OpenRouter as Fallback

If you only have `OPENROUTER_API_KEY`:

```yaml
# Works automatically via OpenRouter
agents:
  - name: Alice
    model: gpt-4o  # Routes to openai/gpt-4o

  - name: Bob
    model: gemini-2.5-flash  # Routes to google/gemini-2.5-flash
```

## Error Handling

The system provides clear, actionable error messages:

```
Model 'gemini-2.5-flash' requires GEMINI_API_KEY.
Solutions:
  1. Set GEMINI_API_KEY environment variable
  2. Use 'google/gemini-2.5-flash' with OPENROUTER_API_KEY
```

## Supported Gemini Models

- `gemini-2.5-flash` - Fast, efficient model
- `gemini-2.5-flash-8b` - Smaller variant
- `gemini-2.5-pro` - More capable model
- `gemini-2.0-pro` - Previous generation
- `gemini-1.5-pro` - Stable production model
- `gemini-1.5-flash` - Fast variant
- `gemma-2b` - Small open model
- `gemma-7b` - Larger open model

## Technical Details

### Architecture

1. **Provider Detection** (`utils/model_provider.py`):
   - Smart routing based on model name patterns
   - API key availability checking
   - Clear error messages with solutions

2. **Gemini Client** (`utils/gemini_client.py`):
   - Adapter pattern for OpenAI SDK compatibility
   - Message format conversion
   - Async/await support

3. **No Automatic Retries**:
   - Explicit behavior - what you specify is what you get
   - No hidden fallbacks or provider switching
   - Clear errors if model/API key unavailable

### Temperature Support

Gemini models support temperature parameter:

```yaml
agents:
  - name: Creative
    model: gemini-2.5-flash
    temperature: 0.9  # High creativity

  - name: Precise
    model: gemini-2.5-flash
    temperature: 0.1  # Low randomness
```

## Testing

### Run Integration Tests

```bash
python test_gemini_integration.py
```

### Test Configurations

```bash
# Test pure Gemini setup
python main.py config/test_gemini.yaml

# Test mixed providers
python main.py config/test_mixed_providers.yaml
```

## Troubleshooting

### Common Issues

1. **Import Error**:
   ```
   google-generativeai not installed
   ```
   **Solution**: `pip install google-generativeai>=0.8.0`

2. **API Key Missing**:
   ```
   Model 'gemini-2.5-flash' requires GEMINI_API_KEY
   ```
   **Solution**: Set environment variable or use OpenRouter format

3. **Model Not Found**:
   ```
   Model 'gemini-experimental' not found in Gemini API
   ```
   **Solution**: Check model name spelling or availability

### Environment Variables

- `GEMINI_API_KEY` - Google AI API key for native Gemini
- `OPENAI_API_KEY` - OpenAI API key for GPT models
- `OPENROUTER_API_KEY` - OpenRouter API key (universal fallback)

## Best Practices

1. **Use Native APIs When Possible**: Better performance and cost
2. **Explicit Provider Selection**: Use `/` prefix when you want OpenRouter
3. **Set OpenRouter as Backup**: Provides universal fallback
4. **Test Configurations**: Use test configs before production

## Migration Guide

### From OpenRouter to Native Gemini

Before (OpenRouter):
```yaml
model: google/gemini-2.5-flash
```

After (Native):
```yaml
model: gemini-2.5-flash  # Requires GEMINI_API_KEY
```

### Maintaining Backward Compatibility

All existing configurations continue to work unchanged. Models with `/` always use OpenRouter:

```yaml
# These always use OpenRouter
model: google/gemini-2.5-flash
model: openai/gpt-4o
model: anthropic/claude-3
```

## Performance Comparison

| Aspect | Native Gemini | OpenRouter |
|--------|--------------|------------|
| Latency | Lower | Higher (proxy overhead) |
| Cost | Direct pricing | Markup added |
| Rate Limits | Google's limits | OpenRouter's limits |
| Reliability | Direct connection | Extra dependency |

## Further Reading

- [Google Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [Gemini Python SDK](https://googleapis.github.io/python-genai/)
- [OpenRouter Documentation](https://openrouter.ai/docs)