Configuration Deep Dive
=======================

This page explains the configuration system that powers the Frohlich Experiment and highlights recent validation improvements.

Loading and Validation
----------------------

Configurations are written in YAML and loaded through ``ExperimentConfiguration.from_yaml``. Before Pydantic validation runs, the loader now performs two fast checks:

1. **Top-level keys** – unknown keys raise a ``ValueError`` with a helpful message.
2. **Agent definitions** – each agent entry must be a mapping containing only recognised fields.

This means configuration mistakes fail early with actionable diagnostics.

Core Settings
-------------

The top-level schema covers the following groups (see ``config/models.py`` for full detail):

- ``language`` – ``English``, ``Spanish``, or ``Mandarin`` determine localisation.
- ``agents`` – list of ``AgentConfiguration`` items.
- ``utility_agent_model`` / ``utility_agent_temperature`` – controls the parsing/validation helper agent.
- ``phase2_rounds`` – maximum number of deliberation rounds.
- ``distribution_range_phase1`` & ``distribution_range_phase2`` – multiplier ranges for dynamic distributions.
- ``income_class_probabilities`` – optional overrides when original values mode is disabled.
- ``original_values_mode`` – enable canonical Frohlich distributions for Phase 1.
- ``logging`` & other optional sections (memory guidance, transparency, etc.).

Agent Configuration
-------------------

Each agent entry supports:

.. code-block:: yaml

   - name: Alice
     personality: "You are a young American college student focused on fairness."
     model: gpt-4.1-nano
     temperature: 0.0
     memory_character_limit: 25000
     reasoning_enabled: true

Field notes:

- ``name`` must be unique.
- ``model`` is a plain string; provider detection happens automatically.
- ``temperature`` accepts values between 0.0 and 2.0 (defaults to 0.7 in the model class but the default config pins it to 0.0 for determinism).
- ``memory_character_limit`` defaults to 50,000 if unspecified, but the shipped configuration uses 25,000 for faster runs.
- ``reasoning_enabled`` toggles internal reasoning traces.

Utility Agent
-------------

The utility agent parses structured outputs and validates votes. Configure it using:

.. code-block:: yaml

   utility_agent_model: gpt-4.1-nano
   utility_agent_temperature: 0.0

Phase Settings
--------------

Key controls for both phases include:

- ``phase2_rounds`` – upper bound on deliberation rounds.
- ``distribution_range_phase1`` (tuple or list) – scaling range for practice distributions.
- ``distribution_range_phase2`` – scaling range for final phase counterfactuals.
- ``selective_memory_updates`` / ``memory_guidance_style`` / ``memory_update_threshold`` – govern memory prompts and thresholds.

Best Practices
--------------

- Keep configuration files under ``config/`` for discoverability.
- Version custom scenarios in Git so seeds and personas are traceable.
- Use the new validation errors as guardrails—if you see an unknown-key message, double-check spelling and indentation.
- Derive scenario variants by copying ``config/default_config.yaml`` and editing agent personas, language, or phase settings as needed.

Further Reading
---------------

- ``docs/configuration.md`` – quick reference created for contributors.
- ``docs/user-guide/designing-experiments.rst`` – strategies for building custom scenarios.
