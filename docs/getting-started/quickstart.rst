Quickstart
==========

This guide will get you running your first Frohlich Experiment in minutes.

Your First Experiment
----------------------

1. **Run the Default Configuration**

   .. code-block:: bash

      python main.py

   This executes the default experiment with five ``gpt-4.1-nano`` agents and up to ten Phase 2 rounds.

2. **Watch the Output**

   You'll see real-time progress as agents work through the experiment:

   .. code-block:: text

      Starting Frohlich Experiment...
      Phase 1: Individual agent familiarization (parallel execution)
      Phase 2: Group discussion and consensus building
      Experiment completed successfully!
      Results saved to: experiment_results_20250819_105130.json

3. **View Your Results**

   The system generates:

   - ``experiment_results_<timestamp>.json`` — the full agent-centric log
   
   - Complete agent interactions and reasoning
   - Phase 1 individual responses
   - Phase 2 group discussion transcripts
   - Final consensus outcomes
   - OpenAI trace links for debugging (when tracing is enabled)

Running with Custom Configuration
---------------------------------

**Spanish Language Experiment**

.. code-block:: bash

   python main.py config/spanish_config.yaml

**Alternative Model Providers**

.. code-block:: bash

   python main.py config/mixed_models_example.yaml

**Custom Output Location**

.. code-block:: bash

   python main.py config/custom_config.yaml results/my_experiment.json

Understanding the Output
------------------------

Each experiment produces a timestamped JSON file containing:

**Experiment Metadata**
   - Unique experiment ID
   - Configuration settings used
   - Execution timestamps
   - Model provider information

**Phase 1 Results**
   - Individual agent responses to each justice principle
   - Agent reasoning and memory updates
   - Principle rankings and constraint specifications

**Phase 2 Results**
   - Complete group discussion transcript
   - Voting rounds and consensus building
   - Final payoff calculations for each agent

**Error Statistics**
   - Any recoverable errors encountered
   - Retry attempts and success rates
   - Performance metrics

Jupyter Notebook Usage
----------------------

For interactive experimentation, use the utility functions:

.. code-block:: python

   from utils.experiment_runner import (
       generate_random_config, 
       run_experiment, 
       run_experiments_parallel
   )

   # Generate and run a single experiment
   config = generate_random_config(num_agents=3, num_rounds=20)
   results = run_experiment(config)

   # Run multiple experiments in parallel
   config_files = ["config1.yaml", "config2.yaml"]
   results = run_experiments_parallel(config_files, max_parallel=5)

Model Provider Options
----------------------

**OpenAI Models** (standard)
   .. code-block:: yaml

      model: "gpt-4.1-mini"
      model: "gpt-4-turbo"

**OpenRouter Models** (via LiteLLM)
   .. code-block:: yaml

      model: "gemini-2.5-flash"
      model: "anthropic/claude-3-5-sonnet-20241022"
      model: "meta-llama/llama-3.1-70b-instruct"

**Mixed Model Experiments**
   Different agents can use different model providers within the same experiment.

Configuration Essentials
-------------------------

Key parameters you can customize:

.. code-block:: yaml

   agents:
     - name: "Alice"
       personality: "Analytical and methodical"
       model: "gpt-4.1-mini"
       temperature: 0.0

   phase2_rounds: 3
   distribution_range_phase1: [0.5, 2.0]
   language: "english"

Memory System
~~~~~~~~~~~~~

Agents automatically manage their own memory:

- **Default Limit**: 25,000 characters (see agent config)
- **Agent-Controlled**: Agents decide what to remember
- **Persistent**: Memory carries across both phases
- **Configurable**: Adjust via ``memory_character_limit``

Viewing Traces
--------------

Each experiment includes OpenAI tracing links:

1. Find the trace URL in your experiment results JSON
2. Visit ``https://platform.openai.com/traces``
3. Explore agent interactions and debugging information

Common Commands
---------------

.. code-block:: bash

   # Run with default settings
   python main.py

   # Use specific config file
   python main.py my_config.yaml

   # Specify output location
   python main.py config.yaml results/output.json

   # Run tests to verify system health
   pytest --mode=dev

   # View available config examples
   ls config/

Common Issues
-------------

**Manager Not Initialized Error**

If you see ``RuntimeError: Manager not initialized``, you forgot to call ``async_init()``:

.. code-block:: python

   # ❌ Wrong - will fail
   manager = FrohlichExperimentManager(config)
   results = await manager.run_complete_experiment()

   # ✅ Correct
   manager = FrohlichExperimentManager(config)
   await manager.async_init()  # Don't forget this!
   results = await manager.run_complete_experiment()

**Missing Language Manager**

When creating managers programmatically, include the language_manager parameter:

.. code-block:: python

   from utils.language_manager import create_language_manager, SupportedLanguage

   # Create language manager first
   language_manager = create_language_manager(
       SupportedLanguage.ENGLISH,
       config.get_effective_seed()
   )

   manager = FrohlichExperimentManager(
       config=config,
       config_file_path="config.yaml",
       language_manager=language_manager  # Required!
   )
   await manager.async_init()

What's Next?
------------

Now that you've run your first experiment:

- :doc:`../user-guide/running-experiments` - Learn advanced execution options
- :doc:`../user-guide/designing-experiments` - Create custom configurations  
- :doc:`../user-guide/analyzing-results` - Interpret and visualize results
- :doc:`../architecture/system-overview` - Understand the system architecture
