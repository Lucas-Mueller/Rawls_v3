Running Experiments
==================

This guide provides comprehensive instructions for running Frohlich Experiments with different configurations, model providers, and execution modes.

Basic Execution
---------------

Default Configuration
~~~~~~~~~~~~~~~~~~~~~

Run an experiment with the default settings:

.. code-block:: bash

   python main.py

This executes using ``config/default_config.yaml`` with these defaults:
- 5 participant agents running ``gpt-4.1-nano``
- English language prompts
- 10 rounds available for Phase 2 discussion
- Original Values Mode enabled for Phase 1 examples

Custom Configuration Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify a custom configuration file:

.. code-block:: bash

   python main.py path/to/your/config.yaml

**Available Example Configurations:**

The ``config/`` directory contains ready-made scenarios, for example:

.. code-block:: bash

   # Faster runs with shorter prompts
   python main.py config/fast.yaml

   # Alternative language prompts
   python main.py config/cheap_spanish.yaml
   python main.py config/cheap_mandarin.yaml

   # Your own scenarios
   python main.py path/to/custom.yaml

Output Control
~~~~~~~~~~~~~~

Control where results are saved:

.. code-block:: bash

   # Default: experiment_results_YYYYMMDD_HHMMSS.json
   python main.py config.yaml

   # Custom output file (agent log + summary saved side-by-side)
   python main.py config.yaml results/my_experiment.json

   # Organize results by date
   python main.py config.yaml results/2025-08-19/experiment_01.json

Execution Modes
---------------

Standard Mode
~~~~~~~~~~~~~

Standard sequential execution (default):

.. code-block:: bash

   python main.py

**Process Flow:**
1. Load and validate configuration
2. Initialize agents (parallel for Phase 1 efficiency)
3. Execute Phase 1: Individual familiarization (parallel)
4. Execute Phase 2: Group discussion (sequential)
5. Persist agent-centric logs and summary metrics

Jupyter Notebook Mode
~~~~~~~~~~~~~~~~~~~~~

For interactive experimentation and analysis:

.. code-block:: python

   from utils.experiment_runner import (
       generate_random_config, 
       run_experiment, 
       run_experiments_parallel,
       generate_and_save_configs
   )

   # Single experiment with random configuration
   config = generate_random_config(num_agents=3, num_rounds=20)
   results = run_experiment(config)
   print(f"Consensus reached: {results.phase2_results.consensus_reached}")

**Batch Experiment Generation:**

.. code-block:: python

   # Generate multiple config files for systematic studies
   generate_and_save_configs(
       num_configs=10, 
       save_path="hypothesis_2_&_4/configs/condition_1"
   )

**Parallel Execution:**

.. code-block:: python

   # Run multiple experiments simultaneously
   config_files = [
       "config/experiment_1.yaml",
       "config/experiment_2.yaml", 
       "config/experiment_3.yaml"
   ]
   
   results = run_experiments_parallel(
       config_files, 
       max_parallel=5  # Adjust based on system resources
   )

Output Artefacts
----------------

Each run emits two JSON files side-by-side in the chosen output directory:

**Agent-Centric Log** (``experiment_results_<timestamp>.json``)
   - Experiment metadata and seed information
   - Detailed Phase 1 and Phase 2 transcripts per participant
   - Voting history and payoff calculations

Use the full log when you need to audit the conversation, memory updates, or analyze detailed agent interactions.

Model Provider Configuration
----------------------------

OpenAI Models
~~~~~~~~~~~~~

Use standard OpenAI models:

.. code-block:: yaml

   agents:
     - name: "Alice"
       model: "gpt-4.1-mini"        # Standard OpenAI choice

   utility_agent_model: "gpt-4.1-mini"

**Environment Setup:**

.. code-block:: bash

   export OPENAI_API_KEY="your-openai-key"

OpenRouter Models
~~~~~~~~~~~~~~~~~

Access alternative model providers via OpenRouter:

.. code-block:: yaml

   agents:
     - name: "Bob"
       model: "gemini-2.5-flash"              # Google
     - name: "Carol"
       model: "anthropic/claude-3-5-sonnet-20241022" # Anthropic
     - name: "Diego"
       model: "meta-llama/llama-3.1-70b-instruct"   # Meta
     - name: "Elena"
       model: "mistralai/mistral-large"              # Mistral

   utility_agent_model: "gemini-2.5-flash"

**Environment Setup:**

.. code-block:: bash

   export OPENROUTER_API_KEY="your-openrouter-key"

Mixed Model Experiments
~~~~~~~~~~~~~~~~~~~~~~~

Combine different model providers in a single experiment:

.. code-block:: yaml

   agents:
     - name: "Alice"
       model: "gpt-4.1-mini"                    # OpenAI
     - name: "Bob"  
       model: "gemini-2.5-flash"        # OpenRouter
     - name: "Carol"
       model: "anthropic/claude-3-5-sonnet"    # OpenRouter

   utility_agent_model: "gpt-4.1-mini"         # OpenAI for parsing

Language Configuration
----------------------

Multi-Language Support
~~~~~~~~~~~~~~~~~~~~~~~

The system supports full experimental execution in multiple languages:

.. code-block:: yaml

   language: "english"   # Default
   language: "spanish"   # Full Spanish interface
   language: "mandarin"  # Full Mandarin interface

**Language-Specific Files:**
- ``config/spanish_config.yaml`` - Pre-configured Spanish experiment
- ``config/mandarin_config.yaml`` - Pre-configured Mandarin experiment  
- ``translations/`` - Complete translation files for all languages

**Key Features:**
- All agent prompts translated to target language
- Justice principle names in target language
- Agent discussions conducted in target language
- Results logging remains in English for consistency

Advanced Configuration
----------------------

Agent Personality Tuning
~~~~~~~~~~~~~~~~~~~~~~~~~

Customize agent behavior through personality descriptions:

.. code-block:: yaml

   agents:
     - name: "Analytical_Alice"
       personality: "You are analytical and methodical. You value systematic approaches to fairness and carefully weigh evidence before making decisions."
       
     - name: "Empathetic_Bob"
       personality: "You are empathetic and community-focused. You prioritize social welfare and consider the human impact of distribution decisions."
       
     - name: "Pragmatic_Carol"
       personality: "You are pragmatic and results-oriented. You focus on practical solutions that can actually be implemented effectively."

Temperature and Reasoning Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Fine-tune agent decision-making:

.. code-block:: yaml

   agents:
     - name: "Consistent_Agent"
       temperature: 0.0              # Deterministic responses
       reasoning_enabled: true       # Detailed reasoning
       
     - name: "Creative_Agent"
       temperature: 0.8              # More creative responses
       reasoning_enabled: true
       
     - name: "Simple_Agent"
       temperature: 0.3              # Moderate creativity
       reasoning_enabled: false      # Simpler responses

Memory Configuration
~~~~~~~~~~~~~~~~~~~~

Control agent memory management:

.. code-block:: yaml

   agents:
     - name: "Standard_Agent"
       memory_character_limit: 50000    # Default limit
       
     - name: "Extended_Agent"  
       memory_character_limit: 100000   # Larger memory for complex discussions
       
     - name: "Focused_Agent"
       memory_character_limit: 25000    # Smaller memory for focused responses

Phase Configuration
~~~~~~~~~~~~~~~~~~~

Customize experiment phases:

.. code-block:: yaml

   # Phase 2 discussion rounds
   phase2_rounds: 5                    # Quick experiment
   phase2_rounds: 10                   # Standard  
   phase2_rounds: 20                   # Extended discussion

   # Income distribution ranges for Phase 2
   distribution_range_phase2: [2, 6]   # Narrow range
   distribution_range_phase2: [4, 8]   # Standard
   distribution_range_phase2: [1, 10]  # Wide range

Original Values Mode
~~~~~~~~~~~~~~~~~~~~

Use predefined distribution sets for consistency:

.. code-block:: yaml

   original_values_mode:
     enabled: true
     situation: "sample"    # Options: sample, a, b, c, d

**Situations:**
- ``sample``: Standard baseline distributions
- ``a``: Higher upper-class probability (10%)
- ``b``: Higher medium-low probability  
- ``c``: Extreme high-income outlier
- ``d``: Graduated middle-class focus

Memory Optimization & Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure advanced memory management and performance features:

.. code-block:: yaml

   # Memory guidance and optimization
   memory_guidance_style: "structured"          # "narrative" or "structured"
   include_experiment_explanation: true          # Include experiment context
   include_experiment_explanation_each_turn: false  # Per-turn context (performance impact)
   phase2_include_internal_reasoning_in_memory: true  # Include reasoning in Phase 2 memory

   # Selective memory updates (reduces API calls)
   selective_memory_updates: true               # Enable selective updates
   memory_update_threshold: "moderate"          # "minimal", "moderate", "comprehensive"
   batch_simple_events: false                   # Batch simple memory events

   # Intelligent retry mechanism
   enable_intelligent_retries: true             # Enable retry on parsing failures
   max_participant_retries: 2                   # Max retries (0-5 range)
   enable_progressive_guidance: true            # More specific guidance on retries
   memory_update_on_retry: true                 # Update memory with retry experiences
   retry_feedback_detail: "concise"             # "concise" or "detailed"

   # Enhanced transparency (Phase 2 results)
   phase2_enhanced_transparency:
     enabled: true
     detail_level: "full"                      # "basic", "enhanced", "full"
     include_counterfactuals: true              # Show alternative outcomes
     include_class_assignment: true             # Show income class assignments
     include_insights: true                     # Best/worst alternative insights

   # Logging and transcript configuration
   logging:
     verbosity_level: "standard"                # "minimal", "standard", "detailed", "debug"
     use_colors: true                           # Colored terminal output
     show_progress_bars: true                   # Progress bars during execution

   transcript_logging:
     enabled: true                              # Enable transcript logging
     output_path: "custom_transcripts/"         # Custom output directory
     include_memory_updates: false              # Include memory operations
     include_instructions: false                # Include system instructions
     include_input_prompts: true                # Include user prompts
     include_agent_responses: true              # Include agent responses

   # Manipulator configuration (Hypothesis 3)
   manipulator:
     enabled: false                             # Enable experimental manipulation
     type: "disruptive"                         # Manipulation strategy
     intervention_round: 5                      # When to intervene

**Performance Optimization Tips:**

- **For Speed**: Set ``selective_memory_updates: true`` and ``max_participant_retries: 0``
- **For Quality**: Use ``memory_guidance_style: "structured"`` and enable enhanced transparency
- **For Research**: Enable transcript logging and manipulator features
- **For Large Experiments**: Use ``memory_character_limit: 25000`` to reduce memory usage

Transcript Logging & Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable detailed logging of agent interactions:

.. code-block:: yaml

   transcript_logging:
     enabled: true
     output_path: "experiment_transcripts/"
     include_memory_updates: false      # Skip memory operations for cleaner logs
     include_instructions: false        # Skip system prompts (performance impact)
     include_input_prompts: true        # Include all agent prompts
     include_agent_responses: true      # Include all agent responses

**Transcript Features:**
- Complete conversation history
- Memory update operations (optional)
- System instructions (optional, performance impact)
- Structured JSON format for analysis
- Automatic timestamping and organization

Monitoring and Debugging
------------------------

Real-Time Monitoring
~~~~~~~~~~~~~~~~~~~~

Monitor experiment progress through console output:

.. code-block:: text

   Starting Frohlich Experiment...
   ? Experiment manager initialized with 3 participants
   Phase 1: Individual agent familiarization (parallel execution)
   ? Alice completed principle applications
   ? Bob completed principle applications  
   ? Carol completed principle applications
   Phase 2: Group discussion and consensus building
   Round 1: Discussion and voting...
   ? Consensus reached on principle: Maximizing floor income
   Experiment completed successfully!
   Results saved to: experiment_results_20250819_105130.json

OpenAI Tracing
~~~~~~~~~~~~~~~

Each experiment includes detailed tracing links:

1. **Find Trace URL**: Located in experiment results JSON
2. **Access Platform**: Visit https://platform.openai.com/traces
3. **Debug Interactions**: View complete agent conversation flows
4. **Analyze Performance**: Review response times and token usage

Error Handling
~~~~~~~~~~~~~~

The system includes comprehensive error recovery:

**Memory Errors**: Automatic retry with memory cleanup
**API Errors**: Exponential backoff and retry mechanisms  
**Validation Errors**: Detailed error messages with suggested fixes
**Network Errors**: Automatic retries with graceful fallback

**Error Reporting**: All errors are categorized and logged with:
- Error type classification
- Retry attempt counts
- Recovery success rates
- Performance impact metrics

Performance Optimization
------------------------

Resource Management
~~~~~~~~~~~~~~~~~~~

Optimize system performance:

.. code-block:: yaml

   # Reduce memory usage
   agents:
     - memory_character_limit: 25000    # Smaller memory footprint
       
   # Reduce discussion complexity  
   phase2_rounds: 5                     # Fewer rounds
   
   # Use faster models
   agents:
     - model: "gpt-4.1-mini"            # Fast OpenAI model
     - model: "gemini-2.5-flash" # Fast OpenRouter model

Parallel Execution Tips
~~~~~~~~~~~~~~~~~~~~~~~

For Jupyter batch processing:

.. code-block:: python

   # Optimize parallel execution
   results = run_experiments_parallel(
       config_files,
       max_parallel=3  # Start conservative, increase based on API limits
   )

**Best Practices:**
- Monitor API rate limits
- Start with lower parallelism and scale up
- Use different model providers to distribute load
- Consider time-based batching for large studies

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Configuration Errors:**

.. code-block:: text

   Error: Agent configuration invalid
   ? Check YAML syntax and required fields
   
**API Key Issues:**

.. code-block:: text

   Error: Authentication failed  
   ? Verify API keys in environment variables
   
**Memory Limit Exceeded:**

.. code-block:: text

   Error: Agent memory exceeded limit
   ? Reduce memory_character_limit or enable memory cleanup

**Model Not Available:**

.. code-block:: text

   Error: Model not supported
   ? Check model name spelling and provider availability

Getting Help
~~~~~~~~~~~~

1. **Check Error Messages**: Read detailed error output for specific guidance
2. **Review Configuration**: Validate YAML syntax and parameter values  
3. **Test Basic Setup**: Run default configuration to verify system health
4. **Check API Status**: Verify model provider service availability
5. **Examine Traces**: Use OpenAI platform traces for detailed debugging

See Also
--------

* :doc:`designing-experiments` - Learn to design custom experimental conditions
* :doc:`analyzing-results` - Understand how to analyze and interpret experiment results
* :doc:`../architecture/system-overview` - Deep dive into system architecture
* :doc:`../contributing/testing` - Testing and validation procedures
* :doc:`../getting-started/quickstart` - Quick start guide for first experiments

For additional support, refer to :doc:`../contributing/testing` for diagnostic procedures.
