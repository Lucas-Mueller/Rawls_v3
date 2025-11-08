Core Modules
============

The core modules form the backbone of the Frohlich Experiment system, handling experiment orchestration, phase management, and fundamental experimental logic. This comprehensive guide provides practical examples and usage patterns for each component.

.. contents:: Table of Contents
   :local:
   :depth: 2

Experiment Manager
------------------

The ``FrohlichExperimentManager`` is the central orchestrator that coordinates the complete experimental flow, from initialization to results generation.

.. autoclass:: core.experiment_manager.FrohlichExperimentManager
   :members:
   :undoc-members:
   :show-inheritance:

Basic Usage
~~~~~~~~~~~

The experiment manager handles the complete lifecycle of an experiment:

.. tabs::

   .. tab:: Basic Experiment

      .. code-block:: python

         import asyncio
         from config import ExperimentConfiguration
         from core.experiment_manager import FrohlichExperimentManager

         async def run_basic_experiment():
             # Load configuration
             config = ExperimentConfiguration.from_yaml("config/default_config.yaml")

             # Create language manager
             from utils.language_manager import create_language_manager, SupportedLanguage
             language_manager = create_language_manager(
                 SupportedLanguage.ENGLISH,
                 config.get_effective_seed()
             )

             # Initialize experiment manager
             manager = FrohlichExperimentManager(
                 config=config,
                 config_file_path="config/default_config.yaml",
                 language_manager=language_manager
             )
             await manager.async_init()  # Required async initialization

             # Run complete experiment
             results = await manager.run_complete_experiment()

             # Save results
             manager.save_results(results, "my_experiment.json")

             return results

         # Execute
         results = asyncio.run(run_basic_experiment())

   .. tab:: Custom Configuration

      .. code-block:: python

         from config import ExperimentConfiguration, AgentConfiguration
         from utils.language_manager import create_language_manager, SupportedLanguage

         # Create custom configuration
         config = ExperimentConfiguration(
             language="English",
             agents=[
                 AgentConfiguration(
                     name="Alice",
                     personality="Analytical and methodical",
                     model="gpt-4o-mini",
                     temperature=0.0,
                     memory_character_limit=50000,
                     reasoning_enabled=True
                 ),
                 AgentConfiguration(
                     name="Bob",
                     personality="Empathetic and community-focused",
                     model="gemini-2.5-flash",
                     temperature=0.3
                 )
             ],
             phase2_rounds=15,
             utility_agent_model="gpt-4o-mini"
         )

         # Create language manager
         language_manager = create_language_manager(
             SupportedLanguage.ENGLISH,
             config.get_effective_seed()
         )

         manager = FrohlichExperimentManager(
             config=config,
             config_file_path="custom_config.yaml",
             language_manager=language_manager
         )
         await manager.async_init()  # Required async initialization

   .. tab:: Error Handling

      .. code-block:: python

         async def robust_experiment():
             try:
                 config = ExperimentConfiguration.from_yaml("config.yaml")

                 # Create language manager
                 from utils.language_manager import create_language_manager, SupportedLanguage
                 language_manager = create_language_manager(
                     SupportedLanguage.ENGLISH,
                     config.get_effective_seed()
                 )

                 manager = FrohlichExperimentManager(
                     config=config,
                     config_file_path="config.yaml",
                     language_manager=language_manager
                 )
                 await manager.async_init()  # Required async initialization

                 # Run with error handling
                 results = await manager.run_complete_experiment()
                 
                 # Check for errors in results
                 if results.get('error_statistics'):
                     errors = results['error_statistics']
                     if sum(errors.values()) > 10:
                         print(f"High error rate: {errors}")
                 
                 return results
                 
             except FileNotFoundError:
                 print("Configuration file not found")
             except ValueError as e:
                 print(f"Configuration error: {e}")
             except Exception as e:
                 print(f"Experiment failed: {e}")

Advanced Features
~~~~~~~~~~~~~~~~~

**Experiment Tracing Integration**

Every experiment includes OpenAI SDK tracing for detailed debugging:

.. code-block:: python

   # Access trace information
   results = await manager.run_complete_experiment()
   trace_url = results.get('trace_links', {}).get('main_trace')
   print(f"View detailed trace: {trace_url}")

**Memory Management**

The experiment manager handles agent memory automatically:

.. code-block:: python

   # Memory usage is tracked in results
   memory_stats = results.get('agent_logs', {})
   for agent_name, logs in memory_stats.items():
       memory_usage = logs.get('memory_usage', {})
       print(f"{agent_name}: {memory_usage}")

**Parallel vs Sequential Execution**

.. code-block:: python

   # Phase 1 runs in parallel for efficiency
   phase1_results = await manager.run_phase1()
   
   # Phase 2 runs sequentially to capture interactions
   phase2_results = await manager.run_phase2()

Phase Managers
--------------

Phase 1 Manager
~~~~~~~~~~~~~~~

The ``Phase1Manager`` handles individual agent familiarization with justice principles in parallel.

.. autoclass:: core.phase1_manager.Phase1Manager
   :members:
   :undoc-members:
   :show-inheritance:

**Practical Usage Examples**

.. tabs::

   .. tab:: Standard Phase 1

      .. code-block:: python

         from core.phase1_manager import Phase1Manager
         from experiment_agents import create_participant_agent

         async def run_phase1():
             # Initialize agents
             agents = []
             for agent_config in config.agents:
                 agent = create_participant_agent(agent_config)
                 agents.append(agent)
             
             # Create phase 1 manager
             phase1_manager = Phase1Manager(agents, config, language_manager)
             
             # Run parallel familiarization
             results = await phase1_manager.run_phase1()
             
             return results

   .. tab:: Custom Distribution Mode

      .. code-block:: python

         # Using original values mode
         config_with_original = ExperimentConfiguration(
             # ... other config ...
             original_values_mode=OriginalValuesModeConfig(
                 enabled=True,
                 situation="sample"  # or "a", "b", "c", "d"
             )
         )
         
         phase1_manager = Phase1Manager(agents, config_with_original, language_manager)

   .. tab:: Memory Optimization

      .. code-block:: python

         # Configure memory-optimized agents
         memory_config = ExperimentConfiguration(
             agents=[
                 AgentConfiguration(
                     name="Agent1",
                     memory_character_limit=25000,  # Smaller memory footprint
                     personality="Concise and focused"
                 )
             ],
             memory_guidance_style="structured"  # vs "narrative"
         )

**Phase 1 Process Flow**

.. mermaid::

   graph TD
       A[Initialize Agents] --> B[Load Justice Principles]
       B --> C[Generate Distributions] 
       C --> D[Parallel Agent Processing]
       D --> E[Agent 1: Principle Applications]
       D --> F[Agent 2: Principle Applications] 
       D --> G[Agent 3: Principle Applications]
       E --> H[Memory Updates]
       F --> H
       G --> H
       H --> I[Validation & Results]
       I --> J[Phase 1 Complete]

Phase 2 Manager
~~~~~~~~~~~~~~~

The ``Phase2Manager`` orchestrates group discussions and consensus building through sequential agent interactions.

.. autoclass:: core.phase2_manager.Phase2Manager
   :members:
   :undoc-members:
   :show-inheritance:

**Implementation Examples**

.. tabs::

   .. tab:: Basic Group Discussion

      .. code-block:: python

         from core.phase2_manager import Phase2Manager

         async def run_group_discussion():
             phase2_manager = Phase2Manager(
                 agents=agents,
                 config=config,
                 language_manager=language_manager,
                 phase1_results=phase1_results
             )
             
             # Run sequential group discussion
             results = await phase2_manager.run_phase2()
             
             # Check consensus
             if results['voting_results']['consensus_reached']:
                 chosen_principle = results['voting_results']['chosen_principle']
                 print(f"Consensus achieved: {chosen_principle}")
             
             return results

   .. tab:: Advanced Discussion Control

      .. code-block:: python

         # Custom discussion parameters
         advanced_config = ExperimentConfiguration(
             phase2_rounds=20,  # Extended discussion
             randomize_speaking_order=True,
             speaking_order_strategy="conversational",
             agents=[
                 AgentConfiguration(
                     name="Moderator",
                     personality="Focused on building consensus",
                     reasoning_enabled=True  # Enable internal reasoning
                 )
             ]
         )

   .. tab:: Voting Mechanism

      .. code-block:: python

         # Access detailed voting results
         voting_results = results['voting_results']
         
         print(f"Consensus: {voting_results['consensus_reached']}")
         print(f"Final votes: {voting_results['final_vote_counts']}")
         print(f"Voting rounds: {voting_results['total_voting_rounds']}")
         
         # Analyze vote progression
         for round_num, vote_data in enumerate(voting_results['vote_history']):
             print(f"Round {round_num + 1}: {vote_data}")

**Phase 2 Interaction Flow**

.. mermaid::

   sequenceDiagram
       participant A1 as Agent 1
       participant A2 as Agent 2  
       participant A3 as Agent 3
       participant VM as Voting Manager
       
       Note over A1,A3: Discussion Round 1
       A1->>A2: Opening statement
       A2->>A3: Response & reasoning
       A3->>A1: Counter-argument
       
       Note over A1,A3: Voting Round 1
       A1->>VM: Vote: Principle A
       A2->>VM: Vote: Principle B
       A3->>VM: Vote: Principle A
       VM-->>A1: No consensus, continue
       
       Note over A1,A3: Discussion Round 2  
       A2->>A1: Revised argument
       A1->>A3: Compromise proposal
       A3->>A2: Agreement consideration
       
       Note over A1,A3: Voting Round 2
       A1->>VM: Vote: Principle A
       A2->>VM: Vote: Principle A  
       A3->>VM: Vote: Principle A
       VM-->>A1: Consensus achieved!

Distribution Generator
----------------------

The ``DistributionGenerator`` creates income distributions for experimental scenarios, supporting both dynamic generation and original values mode.

.. autoclass:: core.distribution_generator.DistributionGenerator
   :members:
   :undoc-members:
   :show-inheritance:

**Usage Patterns**

.. tabs::

   .. tab:: Dynamic Generation

      .. code-block:: python

         from core.distribution_generator import DistributionGenerator
         
         # Create generator
         generator = DistributionGenerator()
         
         # Generate distribution set for Phase 1
         distributions = generator.generate_distribution_set(
             multiplier_range=(0.5, 2.0),
             base_distributions=None  # Use defaults
         )
         
         print(f"Generated {len(distributions)} distributions")
         for i, dist in enumerate(distributions):
             print(f"Distribution {i+1}: {dist}")

   .. tab:: Original Values Mode

      .. code-block:: python

         # Load predefined distributions
         from core.original_values_data import get_situation_data
         
         # Get situation-specific distributions
         situation_data = get_situation_data("sample")
         distributions = situation_data['distributions']
         probabilities = situation_data['probabilities']
         
         print(f"Using predefined situation with {len(distributions)} distributions")

   .. tab:: Custom Base Distributions

      .. code-block:: python

         from models.experiment_types import IncomeDistribution
         
         # Define custom base distributions
         custom_bases = [
             IncomeDistribution(
                 high=40000, medium_high=30000, medium=25000, 
                 medium_low=15000, low=10000
             ),
             IncomeDistribution(
                 high=35000, medium_high=28000, medium=22000,
                 medium_low=18000, low=12000  
             )
         ]
         
         # Generate variations
         distributions = generator.generate_distribution_set(
             multiplier_range=(0.8, 1.5),
             base_distributions=custom_bases
         )

**Distribution Analysis**

.. code-block:: python

   # Analyze distribution properties
   for dist in distributions:
       floor_income = dist.get_floor_income()
       avg_income = dist.get_average_income() 
       range_income = dist.get_range()
       
       print(f"Floor: ${floor_income:,}")
       print(f"Average: ${avg_income:,}")
       print(f"Range: ${range_income:,}")
       print(f"Gini coefficient: {dist.calculate_gini():.3f}")

Original Values Data
--------------------

The ``OriginalValuesData`` module provides predefined distribution sets for experimental consistency and comparison studies.

.. automodule:: core.original_values_data
   :members:
   :undoc-members:
   :show-inheritance:

**Available Situations**

.. tabs::

   .. tab:: Sample Situation

      .. code-block:: python

         from core.original_values_data import get_situation_data
         
         # Get baseline sample situation
         sample_data = get_situation_data("sample")
         
         print("Sample Situation:")
         print(f"Distributions: {len(sample_data['distributions'])}")
         print(f"Probabilities: {sample_data['probabilities']}")
         
         # Income class probabilities: 5/10/50/25/10

   .. tab:: Situation A - High Upper Class

      .. code-block:: python

         # Higher upper-class probability scenario
         situation_a = get_situation_data("a")
         
         print("Situation A - Higher upper-class probability:")
         print(f"Upper class probability: 10% (vs 5% in sample)")
         print(f"Probability distribution: {situation_a['probabilities']}")
         
         # Income class probabilities: 10/20/40/20/10

   .. tab:: All Situations Comparison

      .. code-block:: python

         situations = ["sample", "a", "b", "c", "d"]
         
         for situation in situations:
             data = get_situation_data(situation)
             probs = data['probabilities']
             
             print(f"Situation {situation.upper()}:")
             print(f"  High: {probs['high']*100:.1f}%")
             print(f"  Med-High: {probs['medium_high']*100:.1f}%") 
             print(f"  Medium: {probs['medium']*100:.1f}%")
             print(f"  Med-Low: {probs['medium_low']*100:.1f}%")
             print(f"  Low: {probs['low']*100:.1f}%")

**Experimental Consistency**

.. code-block:: python

   # Use original values for reproducible experiments
   config = ExperimentConfiguration(
       original_values_mode=OriginalValuesModeConfig(
           enabled=True,
           situation="sample"  
       ),
       # Fixed seed for full reproducibility
       seed=42
   )

Error Handling and Recovery
---------------------------

The core modules implement comprehensive error handling with automatic recovery mechanisms.

**Error Categories**

.. code-block:: python

   from utils.error_handling import ErrorCategory, handle_with_retry
   
   # Error types handled by core modules:
   # - MEMORY_ERROR: Agent memory limit exceeded
   # - VALIDATION_ERROR: Response validation failed
   # - COMMUNICATION_ERROR: API call failed
   # - SYSTEM_ERROR: Internal system error
   # - EXPERIMENT_LOGIC_ERROR: Experimental flow error

**Retry Mechanisms**

.. code-block:: python

   # Automatic retry with exponential backoff
   @handle_with_retry(max_attempts=3, backoff_factor=2.0)
   async def robust_agent_interaction():
       # Your agent interaction code here
       pass

**Error Statistics**

.. code-block:: python

   # Access error statistics from results
   error_stats = results.get('error_statistics', {})
   
   total_errors = sum(error_stats.values())
   if total_errors > 0:
       print(f"Experiment completed with {total_errors} recoverable errors:")
       for error_type, count in error_stats.items():
           if count > 0:
               print(f"  {error_type}: {count}")

Performance Optimization
------------------------

**Memory Management**

.. code-block:: python

   # Monitor memory usage
   def check_memory_usage(results):
       agent_logs = results.get('agent_logs', {})
       
       for agent_name, logs in agent_logs.items():
           memory_info = logs.get('memory_usage', {})
           current_usage = memory_info.get('current_characters', 0)
           limit = memory_info.get('character_limit', 50000)
           
           usage_percent = (current_usage / limit) * 100
           if usage_percent > 80:
               print(f"Warning: {agent_name} memory usage at {usage_percent:.1f}%")

**Parallel Optimization**

.. code-block:: python

   import asyncio
   
   # Optimize Phase 1 parallel execution
   async def optimized_phase1():
       # Use semaphore to limit concurrent API calls
       semaphore = asyncio.Semaphore(5)  # Max 5 concurrent calls
       
       async def process_agent_with_limit(agent):
           async with semaphore:
               return await agent.process_principles()
       
       tasks = [process_agent_with_limit(agent) for agent in agents]
       results = await asyncio.gather(*tasks)
       
       return results

**Configuration Optimization**

.. code-block:: python

   # Performance-optimized configuration
   fast_config = ExperimentConfiguration(
       agents=[
           AgentConfiguration(
               name="FastAgent",
               model="gpt-4.1-mini",  # Faster model
               temperature=0.0,  # More deterministic
               memory_character_limit=25000,  # Smaller memory
               reasoning_enabled=False  # Skip internal reasoning
           )
       ],
       phase2_rounds=5,  # Fewer discussion rounds
       distribution_range_phase2=[1.0, 1.0]  # No random variation
   )

Integration Examples
--------------------

**Complete Workflow**

.. code-block:: python

   async def complete_experiment_workflow():
       """Complete experiment from configuration to analysis."""

       # 1. Load and validate configuration
       config = ExperimentConfiguration.from_yaml("config/my_experiment.yaml")

       # 2. Create language manager
       from utils.language_manager import create_language_manager, SupportedLanguage
       language_manager = create_language_manager(
           SupportedLanguage.ENGLISH,
           config.get_effective_seed()
       )

       # 3. Initialize experiment manager
       manager = FrohlichExperimentManager(
           config=config,
           config_file_path="config/my_experiment.yaml",
           language_manager=language_manager
       )
       await manager.async_init()  # Required async initialization
       
       # 3. Run experiment with error handling
       try:
           results = await manager.run_complete_experiment()
           
           # 4. Save results with timestamp
           from datetime import datetime
           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           output_path = f"results/experiment_{timestamp}.json"
           manager.save_results(results, output_path)
           
           # 5. Generate summary
           summary = manager.get_experiment_summary(results)
           print(summary)
           
           # 6. Check for issues
           error_stats = results.get('error_statistics', {})
           if sum(error_stats.values()) > 5:
               print("Warning: High error rate detected")
           
           return results, output_path
           
       except Exception as e:
           print(f"Experiment failed: {e}")
           return None, None

**Batch Processing**

.. code-block:: python

   async def run_batch_experiments(config_files):
       """Run multiple experiments in sequence."""

       results = []
       for config_file in config_files:
           try:
               config = ExperimentConfiguration.from_yaml(config_file)

               # Create language manager for each experiment
               from utils.language_manager import create_language_manager, SupportedLanguage
               language_manager = create_language_manager(
                   SupportedLanguage.ENGLISH,
                   config.get_effective_seed()
               )

               manager = FrohlichExperimentManager(
                   config=config,
                   config_file_path=config_file,
                   language_manager=language_manager
               )
               await manager.async_init()  # Required async initialization
               
               result = await manager.run_complete_experiment()
               results.append({
                   'config_file': config_file,
                   'result': result,
                   'success': True
               })
               
           except Exception as e:
               results.append({
                   'config_file': config_file,
                   'error': str(e),
                   'success': False
               })
       
       return results

See Also
--------

- :doc:`../user-guide/running-experiments` - Learn how to run experiments with different configurations
- :doc:`agents` - Understand the agent architecture and customization
- :doc:`models` - Explore the data models used throughout the system  
- :doc:`../user-guide/analyzing-results` - Analyze and visualize experiment results
- :doc:`../architecture/system-overview` - High-level system architecture