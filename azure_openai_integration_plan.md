# Azure OpenAI Integration Plan

## Executive Summary

This document outlines the comprehensive plan for integrating Azure OpenAI services into the Frohlich Experiment repository. The integration will support the `azure/model_id` format (e.g., `azure/gpt-4o`) following established patterns in the codebase while providing flexible authentication and deployment name mapping.

## Current Architecture Analysis

### Existing Model Provider System

The repository currently supports two model providers:

1. **OpenAI**: Direct string format (e.g., `gpt-4o`, `gpt-4.1-nano`)
2. **OpenRouter**: Slash format (e.g., `google/gemini-2.0-flash-lite-001`)

**Provider Detection Logic**: Uses presence of `/` in model string to determine if it's a non-OpenAI provider.

### Key Integration Points

- **`utils/model_provider.py`**: Main provider detection and configuration
- **`utils/openrouter_client.py`**: OpenRouter-specific client creation
- **`utils/dynamic_model_capabilities.py`**: Temperature capability testing
- **Agent classes**: `participant_agent.py` and `utility_agent.py`
- **`config/models.py`**: Configuration validation and parsing

## Azure OpenAI Integration Design

### 1. Model String Format

**New Format**: `azure/model_id`

**Examples**:
- `azure/gpt-4o`
- `azure/gpt-3.5-turbo`
- `azure/gpt-4.1-mini`
- `azure/text-embedding-ada-002`

**Benefits**:
- Consistent with existing OpenRouter pattern
- Clear provider identification
- Backward compatible with current detection logic

### 2. Authentication Methods

The integration will support both Azure OpenAI authentication methods:

#### Method A: API Key Authentication (Recommended for Development)
```python
# Environment Variables
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
```

#### Method B: Microsoft Entra ID Authentication (Recommended for Production)
```python
# Uses DefaultAzureCredential from azure-identity package
# Supports managed identity, service principal, etc.
```

### 3. Deployment Name Mapping

Azure OpenAI requires deployment names instead of model names. The system will support:

#### Default Mapping Strategy
- `azure/gpt-4o` → Uses deployment name `gpt-4o` (model_id = deployment_name)
- `azure/gpt-3.5-turbo` → Uses deployment name `gpt-3.5-turbo`

#### Custom Deployment Mapping (Optional Enhancement)
```yaml
# In configuration file
azure_deployment_mappings:
  gpt-4o: "my-custom-gpt4o-deployment"
  gpt-3.5-turbo: "production-gpt35-turbo"
```

### 4. Client Creation Architecture

#### New Azure Client Module: `utils/azure_openai_client.py`

```python
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import os

@lru_cache(maxsize=1)
def get_azure_openai_client(auth_method: str = "auto") -> OpenAI:
    """Create Azure OpenAI client using 2025 v1 API approach."""

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable required")

    # Use modern v1 API endpoint format
    base_url = f"{endpoint.rstrip('/')}/openai/v1/"

    if auth_method == "api_key" or os.getenv("AZURE_OPENAI_API_KEY"):
        return OpenAI(
            base_url=base_url,
            api_key=os.getenv("AZURE_OPENAI_API_KEY")
        )
    else:
        # Use Entra ID authentication
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )
        return OpenAI(
            base_url=base_url,
            api_key=token_provider
        )
```

### 5. Model Provider Detection Updates

#### Enhanced `detect_model_provider()` Function

```python
def detect_model_provider(model_string: str) -> Tuple[str, str]:
    """
    Detect model provider and return (model_string, provider_type).

    Returns:
        - ("gpt-4o", "openai") for OpenAI models
        - ("google/gemini-2.0-flash", "openrouter") for OpenRouter
        - ("gpt-4o", "azure") for Azure OpenAI
    """
    if model_string.startswith("azure/"):
        azure_model = model_string[6:]  # Remove "azure/" prefix
        return azure_model, "azure"
    elif "/" in model_string:
        return model_string, "openrouter"
    else:
        return model_string, "openai"
```

#### Enhanced `create_model_config()` Function

```python
def create_model_config(model_string: str, temperature: float = 0.7) -> Union[str, OpenAIChatCompletionsModel]:
    """Create appropriate model configuration based on provider."""
    processed_model, provider = detect_model_provider(model_string)

    if provider == "azure":
        from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
        from utils.azure_openai_client import get_azure_openai_client

        return OpenAIChatCompletionsModel(
            model=processed_model,  # Use deployment name
            openai_client=get_azure_openai_client()
        )
    elif provider == "openrouter":
        return OpenAIChatCompletionsModel(
            model=_append_nitro_suffix(processed_model, True),
            openai_client=get_openrouter_client()
        )
    else:  # openai
        return model_string
```

## Implementation Plan

### Phase 1: Core Infrastructure (Priority: High)

#### 1.1 Create Azure OpenAI Client Module
- **File**: `utils/azure_openai_client.py`
- **Dependencies**: `openai`, `azure-identity`
- **Features**:
  - Support both API key and Entra ID authentication
  - Use 2025 v1 API format
  - Environment variable configuration
  - Error handling for missing credentials

#### 1.2 Update Model Provider Detection
- **File**: `utils/model_provider.py`
- **Changes**:
  - Modify `detect_model_provider()` to support "azure" provider
  - Update `create_model_config()` for Azure OpenAI integration
  - Add Azure-specific model configuration logic
  - Update `get_model_provider_info()` for Azure support

#### 1.3 Update Dependencies
- **File**: `requirements.txt`
- **Add**: `azure-identity>=1.15.0`
- **Ensure**: `openai>=1.0.0` (for v1 API support)

### Phase 2: Configuration and Validation (Priority: High)

#### 2.1 Configuration Model Updates
- **File**: `config/models.py`
- **Changes**:
  - Add validation for `azure/` model format
  - Add optional Azure deployment mapping configuration
  - Update field validators to accept Azure model strings

#### 2.2 Environment Validation
- **File**: `utils/model_provider.py`
- **Changes**:
  - Update `validate_environment_for_models()`
  - Check for required Azure environment variables
  - Provide clear error messages for missing Azure configuration

### Phase 3: Dynamic Capabilities Integration (Priority: Medium)

#### 3.1 Temperature Testing for Azure Models
- **File**: `utils/dynamic_model_capabilities.py`
- **Changes**:
  - Extend `test_temperature_support()` for Azure models
  - Add Azure-specific temperature testing logic
  - Update caching system for Azure model capabilities

#### 3.2 Batch Testing Support
- **File**: `utils/dynamic_model_capabilities.py`
- **Changes**:
  - Update `batch_test_model_temperatures_for_experiment()`
  - Support Azure model strings in batch operations

### Phase 4: Enhanced Features (Priority: Low)

#### 4.1 Custom Deployment Mapping
- **File**: `config/models.py`
- **Feature**: Optional deployment name mapping in configuration
- **Benefit**: Support for custom Azure OpenAI deployment names

#### 4.2 Azure-Specific Model Information
- **File**: `utils/model_provider.py`
- **Feature**: Enhanced model provider info for Azure
- **Include**: Endpoint information, deployment details, authentication method

## Configuration Examples

### Basic Azure OpenAI Configuration

```yaml
# config/azure_example.yaml
language: English

agents:
  - name: "Alice"
    personality: "You are a helpful assistant."
    model: azure/gpt-4o
    temperature: 0.7
    memory_character_limit: 25000
    reasoning_enabled: true

  - name: "Bob"
    personality: "You are a thoughtful advisor."
    model: azure/gpt-3.5-turbo
    temperature: 0.3
    memory_character_limit: 25000
    reasoning_enabled: true

utility_agent_model: azure/gpt-4o-mini
utility_agent_temperature: 0.0

phase2_rounds: 10
```

### Environment Variables Setup

```bash
# API Key Authentication
export AZURE_OPENAI_API_KEY="your-api-key-here"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"

# Optional: Force authentication method
export AZURE_OPENAI_AUTH_METHOD="api_key"  # or "entra_id"
```

### Advanced Configuration with Custom Deployments

```yaml
# Optional: Custom deployment mapping
azure_deployment_mappings:
  gpt-4o: "production-gpt4o-deployment"
  gpt-3.5-turbo: "fast-gpt35-deployment"
  gpt-4o-mini: "utility-mini-deployment"

agents:
  - name: "Alice"
    model: azure/gpt-4o  # Uses "production-gpt4o-deployment"
    temperature: 0.7
```

## Testing Strategy

### Unit Tests

#### 1. Model Provider Detection Tests
- **File**: `tests/unit/test_azure_model_provider.py`
- **Coverage**:
  - Azure model string detection
  - Deployment name extraction
  - Provider type identification

#### 2. Azure Client Creation Tests
- **File**: `tests/unit/test_azure_openai_client.py`
- **Coverage**:
  - API key authentication
  - Entra ID authentication
  - Error handling for missing credentials
  - Environment variable configuration

### Integration Tests

#### 3. End-to-End Azure Integration Tests
- **File**: `tests/integration/test_azure_openai_integration.py`
- **Coverage**:
  - Agent creation with Azure models
  - Temperature detection for Azure models
  - Full experiment workflow with Azure OpenAI

### Live Tests

#### 4. Azure OpenAI Live Tests
- **File**: `tests/live/test_azure_openai_live.py`
- **Requirements**: Valid Azure OpenAI credentials
- **Coverage**:
  - Real API calls to Azure OpenAI
  - Authentication method validation
  - Model deployment verification

## Error Handling and Debugging

### Common Error Scenarios

1. **Missing Azure Credentials**
   ```
   Error: AZURE_OPENAI_ENDPOINT environment variable required
   Solution: Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY
   ```

2. **Invalid Deployment Name**
   ```
   Error: The API deployment for this resource does not exist
   Solution: Verify deployment name matches Azure OpenAI resource
   ```

3. **Authentication Failures**
   ```
   Error: Unauthorized access to Azure OpenAI resource
   Solution: Check API key or Entra ID permissions
   ```

### Debugging Features

- **Verbose Logging**: Enable detailed Azure OpenAI client logging
- **Provider Information**: Enhanced model provider info with Azure details
- **Configuration Validation**: Pre-flight checks for Azure setup

## Security Considerations

### Best Practices

1. **Credential Management**
   - Use Azure Key Vault for production API keys
   - Prefer Entra ID authentication over API keys
   - Rotate API keys regularly

2. **Network Security**
   - Use private endpoints for Azure OpenAI resources
   - Implement network access controls
   - Monitor API usage and access patterns

3. **Configuration Security**
   - Never commit API keys to version control
   - Use environment variables for sensitive configuration
   - Implement configuration validation

## Performance Considerations

### Optimization Strategies

1. **Client Caching**: LRU cache for Azure OpenAI client instances
2. **Connection Pooling**: Reuse HTTP connections where possible
3. **Temperature Caching**: Cache temperature capability results
4. **Batch Operations**: Support batch temperature testing for Azure models

## Migration Guide

### For Existing Users

#### Step 1: Update Dependencies
```bash
pip install azure-identity>=1.15.0
pip install --upgrade openai>=1.0.0
```

#### Step 2: Configure Azure Environment
```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_API_KEY="your-api-key"
```

#### Step 3: Update Configuration Files
```yaml
# Change from:
model: gpt-4o

# To:
model: azure/gpt-4o
```

#### Step 4: Verify Integration
```bash
python run_tests.py unit
python run_tests.py integration
```

## Future Enhancements

### Phase 2 Enhancements

1. **Multi-Region Support**: Support multiple Azure OpenAI endpoints
2. **Cost Optimization**: Usage tracking and cost management features
3. **Advanced Authentication**: Certificate-based authentication support
4. **Model Availability**: Dynamic model availability detection

### Phase 3 Enhancements

1. **Azure AI Services Integration**: Support for other Azure AI services
2. **Monitoring and Alerts**: Integration with Azure monitoring
3. **Compliance Features**: Support for Azure compliance requirements
4. **Performance Analytics**: Detailed performance metrics and optimization

## Conclusion

This integration plan provides a comprehensive, scalable approach to adding Azure OpenAI support to the Frohlich Experiment repository. The design follows established patterns, maintains backward compatibility, and provides flexibility for various deployment scenarios.

The phased implementation approach ensures that core functionality is delivered quickly while allowing for iterative enhancement of advanced features. The integration supports both development and production use cases with appropriate security and performance considerations.

## Appendix

### Required Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI resource endpoint | `https://myresource.openai.azure.com` |
| `AZURE_OPENAI_API_KEY` | Yes (if using API key auth) | Azure OpenAI API key | `abc123...` |
| `AZURE_OPENAI_AUTH_METHOD` | No | Force authentication method | `api_key` or `entra_id` |

### Model String Examples

| Configuration | Deployment Name | Description |
|---------------|-----------------|-------------|
| `azure/gpt-4o` | `gpt-4o` | GPT-4o model via Azure OpenAI |
| `azure/gpt-3.5-turbo` | `gpt-3.5-turbo` | GPT-3.5 Turbo via Azure OpenAI |
| `azure/gpt-4o-mini` | `gpt-4o-mini` | GPT-4o Mini via Azure OpenAI |
| `azure/text-embedding-ada-002` | `text-embedding-ada-002` | Text embedding model |

### Dependencies Added

```
azure-identity>=1.15.0
```

*Note: The `openai` package dependency already exists and supports Azure OpenAI as of version 1.0.0+*