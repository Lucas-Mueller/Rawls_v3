# Configuration Guide

This document explains the core fields required to run a Frohlich Experiment configuration and notes common overrides.

## Top-Level Settings
- `language` (str): Display language for prompts. Supported values: `English`, `Spanish`, `Mandarin`.
- `seed` (int, optional): Seed for deterministic runs. If omitted, a stable seed is derived from configuration parameters.
- `selective_memory_updates` (bool): Enables legacy verbose memory tracking when `true`.
- `memory_guidance_style` (str): Controls memory prompt style (`structured`, `narrative`, `concise`).
- `phase2_include_internal_reasoning_in_memory` (bool): Whether Phase 2 internal reasoning is persisted to agent memory.
- `include_experiment_explanation_each_turn` (bool): Toggles the per-turn explanation scaffold used in prompts.
- `memory_update_threshold` (str): Threshold for memory updates (`minimal`, `moderate`, `comprehensive`).

## Transcript Logging
- `transcript_logging.enabled` (bool): Enables capture of prompt transcripts for participant agents.
- `transcript_logging.include_instructions` (bool): Also record system instructions (adds noticeable overhead).
- `transcript_logging.include_input_prompts` (bool): Include user-visible prompts in the transcript payload (default: `true`).
- `transcript_logging.include_memory_updates` (bool): Log memory maintenance calls alongside interactive prompts.
- `transcript_logging.output_path` (str, optional): Override the default `transcript_<experiment_id>.json` save location.

## Agent Definitions (`agents`)
Each entry must provide:
- `name` (str): Unique display name.
- `personality` (str): Persona description injected into prompts.
- `model` (str): Model identifier, e.g., `gpt-4.1-nano`.
- `temperature` (float): Preferred sampling temperature (0.0–2.0).
- `memory_character_limit` (int): Maximum characters maintained in memory.
- `reasoning_enabled` (bool): Enables internal reasoning segments.
- Optional: `language` (str) for per-agent overrides when not matching experiment language.

## Utility Agent
- `utility_agent_model` (str): Model used for parsing and validation helpers.
- `utility_agent_temperature` (float): Temperature used for the utility agent.

## Phase & Distribution Controls
- `phase2_rounds` (int): Maximum number of deliberation rounds.
- `distribution_range_phase1` (list[float, float]): Multiplier range for Phase 1 distributions.
- `distribution_range_phase2` (list[float, float]): Multiplier range for Phase 2.
- `income_class_probabilities` (mapping): Probabilities for class assignments when not using original values.
- `original_values_mode.enabled` (bool): Opt into canonical Frohlich distributions.

Optional advanced settings include `phase2_enhanced_transparency`, `logging`, and `phase2_settings`. Refer to inline docstrings in `config/models.py` for detailed descriptions.

## Validation Hints
- Agent names must be unique.
- Temperatures must be within 0.0–2.0; memory limits must be positive.
- Distribution ranges must contain two positive floats where min < max.
- Income class probabilities must sum to 1.0.

## Usage Tips
1. Start from `config/default_config.yaml` and create scenario-specific copies under `config/`.
2. Validate changes by importing them in a Python REPL:
   ```python
   from config import ExperimentConfiguration
   ExperimentConfiguration.from_yaml("config/your_config.yaml")
   ```
3. Track custom configs in version control to capture experiment provenance.
