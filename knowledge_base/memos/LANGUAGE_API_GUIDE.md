# Language Manager API Guide

## Overview

The simplified Language Manager now provides a unified dot-notation API for accessing translations. This makes the codebase more maintainable and easier to use.

## Quick Start

```python
from utils.language_manager import get_language_manager, SupportedLanguage

# Get the global language manager
lm = get_language_manager()

# Set language (English, Spanish, or Mandarin)
lm.set_language(SupportedLanguage.MANDARIN)

# Access translations using dot notation
principle_name = lm.get("common.principle_names.maximizing_floor")
experiment_text = lm.get("prompts.experiment_explanation")
error_msg = lm.get("prompts.system_error_messages_memory_limit_exceeded")
```

## API Methods

### Primary Method: `get(path, **kwargs)`

The main method for accessing any translation:

```python
# Basic usage
text = lm.get("common.principle_names.maximizing_average")

# With formatting parameters
prompt = lm.get("prompts.phase1_rounds1_4_principle_application", round_number=3)
message = lm.get("prompts.system_status_messages_earnings_update", amount=150.75)
```

### Translation Structure

All translations follow a flattened two-section structure:

```
common/                          # Shared terms and labels
  ├── principle_names/           # Justice principle names
  ├── income_classes/           # Income class names  
  └── certainty_levels/         # Certainty level names

prompts/                         # All prompts and messages
  ├── experiment_explanation    # Main experiment text
  ├── phase1_*                 # Phase 1 prompts
  ├── phase2_*                 # Phase 2 prompts
  ├── utility_*                # Utility agent prompts
  ├── system_*                 # System messages
  ├── memory_*                 # Memory-related prompts
  ├── distribution_*           # Distribution formatting
  ├── context_*                # Context formatting
  └── format_*                 # Display formatting
```

### Legacy Methods (Still Supported)

The old methods still work but internally use the new API:

```python
# These still work but are verbose
text = lm.get_prompt("category", "key")
msg = lm.get_message("category", "group", "key")

# Convenience methods still available
explanation = lm.get_experiment_explanation()
instructions = lm.get_phase1_instructions(round_number=1)
```

## Usage Patterns

### Common Translations
```python
# Principle names
floor_principle = lm.get("common.principle_names.maximizing_floor")
average_principle = lm.get("common.principle_names.maximizing_average")

# Income classes  
high_class = lm.get("common.income_classes.high")
low_class = lm.get("common.income_classes.low")

# Certainty levels
very_sure = lm.get("common.certainty_levels.very_sure")
```

### Prompts and Instructions
```python
# Experiment explanation
intro = lm.get("prompts.experiment_explanation")

# Phase-specific instructions
initial_ranking = lm.get("prompts.phase1_round0_initial_ranking")
group_discussion = lm.get("prompts.phase2_group_discussion", round_number=3)

# Application prompts with parameters
application_prompt = lm.get("prompts.phase1_rounds1_4_principle_application", 
                           round_number=2)
```

### System Messages
```python
# Error messages
memory_limit_error = lm.get("prompts.system_error_messages_memory_limit_exceeded")
invalid_choice_error = lm.get("prompts.system_error_messages_invalid_principle_choice")

# Success messages
choice_accepted = lm.get("prompts.system_success_messages_choice_accepted")

# Status messages
phase1_starting = lm.get("prompts.system_status_messages_phase1_starting")
earnings_update = lm.get("prompts.system_status_messages_earnings_update", amount=75.50)
```

### Utility Agent Prompts
```python
# Parser and validator instructions
parser_instructions = lm.get("prompts.utility_parser_instructions")
validator_instructions = lm.get("prompts.utility_validator_instructions")

# Parsing prompts with parameters
parse_choice = lm.get("prompts.utility_parse_principle_choice", 
                     response=user_response)
parse_ranking = lm.get("prompts.utility_parse_principle_ranking", 
                      response=user_response)
```

## Error Handling

```python
try:
    text = lm.get("invalid.path.here")
except KeyError as e:
    print(f"Translation not found: {e}")
except ValueError as e:
    print(f"Formatting error: {e}")
```

## Parameter Validation

Use the validation script to ensure parameter consistency:

```bash
python validate_translation_parameters.py
```

This will check that all `{parameter}` names in translation files match the English versions exactly.

## Benefits of the New API

1. **Simpler**: One method (`get`) instead of multiple methods
2. **Consistent**: Same pattern for all translations  
3. **Maintainable**: Clear hierarchy in dot notation
4. **Validated**: Parameter validation script catches issues
5. **Flexible**: Easy to add new translations without code changes

## Migration Guide

### Old Code
```python
# Old verbose approach
lm.get_prompt("phase1_instructions", "round0_initial_ranking")
lm.get_message("system_messages", "error_messages", "memory_limit_exceeded")
lm.get_justice_principle_name("maximizing_floor")
```

### New Code
```python
# New simplified approach
lm.get("prompts.phase1_round0_initial_ranking")
lm.get("prompts.system_error_messages_memory_limit_exceeded")
lm.get("common.principle_names.maximizing_floor")
```

The old methods still work, so migration can be gradual.