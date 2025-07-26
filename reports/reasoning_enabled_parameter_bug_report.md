# Reasoning Enabled Parameter Bug Report

## Issue Summary

The system is failing to start with an AttributeError: `'AgentConfiguration' object has no attribute 'reasoning_enabled'`. This error occurs when the system attempts to initialize the experiment and log agent configurations.

## Error Details

**Error Message:**
```
AttributeError: 'AgentConfiguration' object has no attribute 'reasoning_enabled'
```

**Stack Trace Location:**
- File: `/utils/agent_centric_logger.py:49`
- Function: `initialize_experiment`
- Specific line: `reasoning_enabled=agent_config.reasoning_enabled`

## Root Cause Analysis

### 1. Configuration Model Missing Field
The `AgentConfiguration` model in `config/models.py` does not include the `reasoning_enabled` field:

```python
class AgentConfiguration(BaseModel):
    name: str = Field(..., description="Agent name")
    personality: str = Field(..., description="Agent personality description")
    model: str = Field("o3-mini", description="LLM model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    memory_character_limit: int = Field(50000, gt=0, description="Maximum memory length in characters")
    # MISSING: reasoning_enabled field
```

### 2. Master Plan Requirements
According to `master_plan.md`, the reasoning feature is explicitly required:

> **Agent Specifications:** For each participant agent:
> - v) Reasoning (enable/disable the internal Chain-of-Thought sub-prompt in 2.1.3.ii)

> **Note for Claude Code:** The "reasoning" step (step 2.1.3.ii) is optional and can be disabled via a parameter in the config file. By default, it is enabled.

### 3. Current Usage in Codebase
Multiple files expect the `reasoning_enabled` parameter:
- `utils/agent_centric_logger.py` - logging agent configuration
- `core/phase2_manager.py` - controlling reasoning in Phase 2 discussions
- Test files expecting this configuration

### 4. Configuration File Missing Field
The `config/default_config.yaml` does not include `reasoning_enabled` settings for agents.

## Impact Assessment

### Critical Impact
- **System Startup**: Complete failure to run experiments
- **Configuration Validation**: Invalid agent configurations
- **Phase 2 Functionality**: Cannot control reasoning behavior as specified in master plan

### Affected Components
1. **Agent Configuration System** - Missing core field
2. **Logging System** - Cannot log complete agent configurations
3. **Phase 2 Manager** - Cannot access reasoning control parameter
4. **Experiment Manager** - Cannot initialize with proper agent configurations

## Required Fixes

### 1. Add reasoning_enabled to AgentConfiguration Model
```python
class AgentConfiguration(BaseModel):
    name: str = Field(..., description="Agent name")
    personality: str = Field(..., description="Agent personality description")
    model: str = Field("o3-mini", description="LLM model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Model temperature")
    memory_character_limit: int = Field(50000, gt=0, description="Maximum memory length in characters")
    reasoning_enabled: bool = Field(True, description="Enable/disable internal reasoning in Phase 2")
```

### 2. Update Configuration Files
Add `reasoning_enabled: true` to each agent in `config/default_config.yaml`:
```yaml
agents:
  - name: "Alice"
    personality: "..."
    model: "gpt-4.1-nano"
    temperature: 0
    memory_character_limit: 50000
    reasoning_enabled: true
```

### 3. Update Tests
Ensure all test configurations include the `reasoning_enabled` parameter.

## Verification Steps

1. Add `reasoning_enabled` field to `AgentConfiguration`
2. Update configuration files with the new parameter
3. Run `python main.py` to verify system starts
4. Run `python run_tests.py` to ensure no test failures
5. Verify Phase 2 reasoning behavior is controllable

## Priority

**HIGH** - This is a blocking issue preventing any experiment execution.

## Notes

This appears to be an inconsistency between the master plan requirements and the actual implementation. The reasoning feature is a core requirement for Phase 2 agent behavior control but was not properly implemented in the configuration system.