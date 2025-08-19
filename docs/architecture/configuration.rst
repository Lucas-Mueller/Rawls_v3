Configuration Deep Dive
========================

This section provides comprehensive documentation of the Frohlich Experiment configuration system, covering all parameters, validation rules, and advanced configuration patterns.

Configuration Architecture
---------------------------

YAML-Based Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

The system uses YAML for human-readable experiment configuration with Pydantic models for type safety and validation:

.. code-block:: python

   # Configuration loading process
   config = ExperimentConfiguration.from_yaml("config.yaml")
   
   # Automatic validation and type conversion
   validated_config = ExperimentConfiguration.model_validate(config)

**Benefits of this approach:**
- Human-readable configuration files
- Strong type safety and validation  
- Automatic documentation generation
- IDE support with auto-completion
- Clear error messages for invalid configurations

Configuration Hierarchy
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   ExperimentConfiguration
   ├── language: str
   ├── agents: List[AgentConfiguration] 
   ├── utility_agent_model: str
   ├── utility_agent_temperature: float
   ├── phase2_rounds: int
   ├── distribution_range_phase2: List[float]
   ├── income_class_probabilities: Dict[str, float]
   └── original_values_mode: OriginalValuesModeConfig

Core Configuration Parameters
-----------------------------

Language Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   language: "english"    # Options: "english", "spanish", "mandarin"

**Supported Languages:**

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Language
     - Code
     - Translation Files
   * - English
     - "english"
     - ``translations/english_prompts.json``
   * - Spanish
     - "spanish" 
     - ``translations/spanish_prompts.json``
   * - Mandarin
     - "mandarin"
     - ``translations/mandarin_prompts.json``

**Language Impact:**
- All agent prompts translated to target language
- Agent discussions conducted in target language
- Justice principle names localized
- Results logging remains in English for analysis consistency

Agent Configuration
~~~~~~~~~~~~~~~~~~~

Each agent is configured with comprehensive parameters:

.. code-block:: yaml

   agents:
     - name: "Agent_1"                          # Required: Unique identifier
       personality: "Descriptive text..."      # Required: Agent personality
       model: "gpt-4.1-mini"                  # Required: Model identifier
       temperature: 0.3                       # Optional: 0.0-1.0, default varies
       memory_character_limit: 50000          # Optional: Memory limit in characters
       reasoning_enabled: true                # Optional: Enable detailed reasoning

**Parameter Details:**

``name`` (required, string)
   - Unique identifier for the agent in the experiment
   - Used in logging, results, and inter-agent communication
   - Should be descriptive but concise
   - Examples: "Alice", "Economist_Agent", "Agent_1"

``personality`` (required, string)  
   - Detailed description of agent's personality and approach
   - Influences agent decision-making and discussion style
   - Can include role-based, cultural, or cognitive style elements
   - Length: Typically 50-200 words for effectiveness

``model`` (required, string)
   - Model identifier for the AI model to use
   - OpenAI models: Direct model name (e.g., "gpt-4.1-mini")
   - OpenRouter models: Provider/model format (e.g., "google/gemini-2.5-flash")
   - System automatically detects provider based on format

``temperature`` (optional, float, 0.0-1.0)
   - Controls randomness in agent responses
   - 0.0: Deterministic, highly consistent responses
   - 0.5: Balanced creativity and consistency
   - 1.0: Maximum creativity and randomness
   - Default: 0.3 for most agent types

``memory_character_limit`` (optional, integer)
   - Maximum characters agent can store in memory
   - Default: 50,000 characters
   - Agent manages memory content independently
   - Experiment aborts if limit consistently exceeded
   - Range: 10,000 - 1,000,000 characters recommended

``reasoning_enabled`` (optional, boolean)  
   - Whether to enable detailed reasoning in agent responses
   - true: Agents provide detailed explanations for choices
   - false: Agents give simpler, more direct responses
   - Default: true
   - Affects response length and token costs

Model Provider Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**OpenAI Models:**

.. code-block:: yaml

   agents:
     - model: "gpt-4.1-mini"        # Fast, cost-effective
     - model: "gpt-4-turbo"         # More capable, higher cost
     - model: "gpt-3.5-turbo"       # Budget option

**OpenRouter Models:**

.. code-block:: yaml

   agents:
     - model: "google/gemini-2.5-flash"              # Fast Google model
     - model: "google/gemini-2.5-pro"                # Capable Google model  
     - model: "anthropic/claude-3-5-sonnet-20241022" # Anthropic model
     - model: "meta-llama/llama-3.1-70b-instruct"    # Meta model
     - model: "mistralai/mistral-large"              # Mistral model

**Mixed Model Experiments:**

.. code-block:: yaml

   agents:
     - name: "OpenAI_Agent"
       model: "gpt-4.1-mini"              # OpenAI
     - name: "Google_Agent"  
       model: "google/gemini-2.5-flash"   # OpenRouter
     - name: "Anthropic_Agent"
       model: "anthropic/claude-3-5-sonnet" # OpenRouter

Utility Agent Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   utility_agent_model: "gpt-4.1-mini"      # Model for response parsing
   utility_agent_temperature: 0.0           # Usually deterministic

**Utility Agent Role:**
- Validates and parses participant agent responses
- Ensures constraint specifications are valid
- Processes responses in appropriate language
- Should be deterministic (temperature 0.0) for consistency

Phase Configuration
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   phase2_rounds: 10                     # Number of discussion rounds
   distribution_range_phase2: [4, 8]     # Income multiplier range

**Phase 2 Rounds:**
- Controls length of group discussion
- Range: 3-50 rounds typical
- 3-5: Quick pilot studies
- 8-15: Standard research studies  
- 20+: In-depth discussion analysis

**Distribution Range Phase 2:**
- Controls income variation in Phase 2 scenarios
- Format: [minimum_multiplier, maximum_multiplier]
- Examples:
  - ``[1, 2]``: Low variation (50-100% income differences)
  - ``[0.5, 2.0]``: Standard variation 
  - ``[0.1, 10]``: High variation (extreme inequality scenarios)

Income Class Probabilities
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   income_class_probabilities:
     high: 0.05          # 5% probability of high income
     medium_high: 0.10   # 10% probability  
     medium: 0.50        # 50% probability (most common)
     medium_low: 0.25    # 25% probability
     low: 0.10           # 10% probability of low income

**Requirements:**
- All probabilities must be between 0.0 and 1.0
- Total must sum to 1.0 (validated automatically)
- Used for income class assignment after principle selection

**Common Patterns:**

.. code-block:: yaml

   # Standard distribution (default)
   income_class_probabilities:
     high: 0.05, medium_high: 0.10, medium: 0.50, medium_low: 0.25, low: 0.10
   
   # High inequality scenario
   income_class_probabilities:
     high: 0.20, medium_high: 0.10, medium: 0.20, medium_low: 0.30, low: 0.20
   
   # Middle-class focused
   income_class_probabilities:
     high: 0.05, medium_high: 0.25, medium: 0.40, medium_low: 0.25, low: 0.05

Original Values Mode
~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   original_values_mode:
     enabled: true                    # Use predefined distributions
     situation: "sample"              # Situation identifier

**Available Situations:**

.. list-table::
   :header-rows: 1
   :widths: 15 25 60

   * - Situation
     - Probability Weighting
     - Description
   * - "sample"
     - 5/10/50/25/10
     - Standard baseline distributions  
   * - "a"
     - 10/20/40/20/10
     - Higher upper-class probability
   * - "b"  
     - 6.3/20.8/28.3/34.5/10
     - Higher medium-low probability
   * - "c"
     - 1.3/4.3/58.3/26/10
     - Extreme high-income outlier
   * - "d"
     - 5/20.8/28.3/35.8/10
     - Graduated middle-class focus

**When to Use Original Values Mode:**
- Experimental replication and comparison
- Controlled studies requiring identical distributions
- Validation against previous research
- Systematic hypothesis testing

Configuration Validation
-------------------------

Automatic Validation Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~

The system performs comprehensive validation on configuration loading:

**Agent Validation:**

.. code-block:: python

   # Automatic checks performed
   class AgentConfiguration(BaseModel):
       name: str                           # Must be non-empty string
       personality: str                    # Must be non-empty string  
       model: str                         # Must be valid model format
       temperature: float = 0.3           # Must be 0.0 <= temp <= 1.0
       memory_character_limit: int = 50000 # Must be > 0
       reasoning_enabled: bool = True      # Must be boolean

**Experiment-Level Validation:**

.. code-block:: python

   def validate_configuration(config):
       """Comprehensive configuration validation."""
       
       # Agent requirements
       assert len(config.agents) >= 1, "At least one agent required"
       assert len(set(agent.name for agent in config.agents)) == len(config.agents), \
              "Agent names must be unique"
       
       # Probability validation
       prob_sum = sum(config.income_class_probabilities.values())
       assert abs(prob_sum - 1.0) < 0.001, f"Probabilities must sum to 1.0, got {prob_sum}"
       
       # Model validation
       for agent in config.agents:
           assert agent.temperature >= 0.0 and agent.temperature <= 1.0, \
                  f"Temperature must be 0.0-1.0, got {agent.temperature}"

Custom Validation Errors
~~~~~~~~~~~~~~~~~~~~~~~~

Common validation errors and solutions:

**Invalid Temperature:**

.. code-block:: text

   Error: Temperature must be between 0.0 and 1.0, got 2.5
   Solution: Set temperature: 0.5  # or other value in valid range

**Duplicate Agent Names:**

.. code-block:: text

   Error: Agent names must be unique, found duplicate: 'Agent_1'  
   Solution: Rename agents with unique identifiers

**Invalid Probability Sum:**

.. code-block:: text

   Error: Income class probabilities sum to 1.2, must equal 1.0
   Solution: Adjust probabilities to sum exactly to 1.0

**Missing Required Field:**

.. code-block:: text

   Error: Field 'personality' is required but missing
   Solution: Add personality: "Your personality description here"

Advanced Configuration Patterns
-------------------------------

Experimental Design Patterns
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Systematic Parameter Sweeps:**

.. code-block:: python

   # Generate configs for temperature study
   base_config = load_base_configuration()
   
   temperatures = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
   
   for temp in temperatures:
       config = base_config.copy()
       for agent in config.agents:
           agent.temperature = temp
       
       save_configuration(config, f"temperature_{temp:.1f}.yaml")

**Factorial Designs:**

.. code-block:: yaml

   # 2x2 design: personality × temperature
   configs:
     - name: "analytical_low"
       agents:
         - personality: "Analytical and systematic"
           temperature: 0.1
     
     - name: "analytical_high"  
       agents:
         - personality: "Analytical and systematic"
           temperature: 0.8
     
     - name: "intuitive_low"
       agents:
         - personality: "Intuitive and empathetic"  
           temperature: 0.1
     
     - name: "intuitive_high"
       agents:
         - personality: "Intuitive and empathetic"
           temperature: 0.8

**Replication Studies:**

.. code-block:: yaml

   # Multiple identical configs for replication
   experiment_metadata:
     study_name: "Personality Replication Study"
     condition: "empathy_high" 
     replication_number: 5     # This is replication 5 of 10
   
   agents:
     - name: "Empathetic_Agent_1"
       personality: "Highly empathetic and caring"
     - name: "Empathetic_Agent_2"  
       personality: "Highly empathetic and caring"
     - name: "Empathetic_Agent_3"
       personality: "Highly empathetic and caring"

Configuration Management
------------------------

Version Control Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Directory Structure:**

.. code-block:: text

   configs/
   ├── experiments/
   │   ├── pilot_studies/
   │   │   ├── pilot_01.yaml
   │   │   └── pilot_02.yaml
   │   ├── main_studies/  
   │   │   ├── study_1_condition_a.yaml
   │   │   └── study_1_condition_b.yaml
   │   └── replications/
   │       ├── replication_1.yaml
   │       └── replication_2.yaml
   ├── templates/
   │   ├── three_agent_template.yaml
   │   └── mixed_models_template.yaml
   └── archived/
       └── old_study_configs/

**Configuration Metadata:**

.. code-block:: yaml

   # Include metadata in all configs
   _metadata:
     study_name: "Justice Principle Preference Study"
     researcher: "Your Name"
     date_created: "2025-08-19"
     version: "1.2"
     description: "Testing personality effects on justice preferences"
     hypothesis: "Empathetic agents prefer redistributive principles"
     
   # Actual configuration follows...
   language: "english"
   agents: [...]

Environment-Specific Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Development vs Production:**

.. code-block:: yaml

   # config/development.yaml
   agents:
     - memory_character_limit: 25000      # Reduced for faster testing
   phase2_rounds: 3                      # Quick testing
   utility_agent_model: "gpt-4.1-mini"   # Cost-effective
   
   # config/production.yaml  
   agents:
     - memory_character_limit: 75000      # Full memory for research
   phase2_rounds: 15                     # Comprehensive discussion
   utility_agent_model: "gpt-4-turbo"    # More capable parsing

**Multi-Environment Management:**

.. code-block:: python

   # config_manager.py
   def load_config_for_environment(base_config_path, environment="development"):
       """Load configuration with environment-specific overrides."""
       
       base_config = ExperimentConfiguration.from_yaml(base_config_path)
       
       env_overrides_path = f"config/overrides/{environment}.yaml"
       if Path(env_overrides_path).exists():
           overrides = yaml.safe_load(open(env_overrides_path))
           # Apply overrides to base config
           config = apply_overrides(base_config, overrides)
       else:
           config = base_config
           
       return config

Configuration Testing
---------------------

Validation Testing
~~~~~~~~~~~~~~~~~

Test configurations before running experiments:

.. code-block:: python

   # test_configurations.py
   def test_configuration_validity(config_path):
       """Test configuration loading and validation."""
       
       try:
           config = ExperimentConfiguration.from_yaml(config_path)
           print(f"✅ Configuration valid: {config_path}")
           return True
       except Exception as e:
           print(f"❌ Configuration error in {config_path}: {e}")
           return False

   def test_all_configurations(config_dir="configs/"):
       """Test all configurations in directory."""
       
       config_files = Path(config_dir).glob("**/*.yaml")
       results = {}
       
       for config_file in config_files:
           results[config_file] = test_configuration_validity(config_file)
       
       failed_configs = [path for path, valid in results.items() if not valid]
       
       if failed_configs:
           print(f"❌ {len(failed_configs)} configurations failed validation")
           for config in failed_configs:
               print(f"  - {config}")
       else:
           print(f"✅ All {len(results)} configurations valid")

Dry Run Testing
~~~~~~~~~~~~~~~

Test configurations without running full experiments:

.. code-block:: python

   # dry_run.py
   async def dry_run_configuration(config_path):
       """Test configuration by initializing agents without running experiment."""
       
       config = ExperimentConfiguration.from_yaml(config_path)
       
       try:
           # Test agent creation
           manager = FrohlichExperimentManager(config)
           await manager.async_init()
           
           print(f"✅ Dry run successful: {len(manager.participants)} agents initialized")
           
           # Test basic functionality
           test_distributions = generate_test_distributions()
           
           # Quick agent response test
           for agent in manager.participants:
               response = await agent.test_response(test_distributions[0])
               print(f"  Agent {agent.name}: Response length {len(str(response))}")
           
           return True
           
       except Exception as e:
           print(f"❌ Dry run failed: {e}")
           return False

Performance Testing
~~~~~~~~~~~~~~~~~~~

Test configuration performance characteristics:

.. code-block:: python

   def estimate_configuration_cost(config):
       """Estimate token costs for configuration."""
       
       # Rough token estimation
       agent_cost_per_round = {
           "gpt-4.1-mini": 100,      # tokens per round estimate
           "gpt-4-turbo": 150,
           "google/gemini-2.5-flash": 120,
           "anthropic/claude-3-5-sonnet": 200
       }
       
       total_cost_estimate = 0
       
       for agent in config.agents:
           base_model = agent.model.split("/")[-1] if "/" in agent.model else agent.model
           cost_per_round = agent_cost_per_round.get(base_model, 150)  # default
           
           # Phase 1: 4 principles × agent
           phase1_cost = 4 * cost_per_round
           
           # Phase 2: rounds × agent  
           phase2_cost = config.phase2_rounds * cost_per_round
           
           agent_total = phase1_cost + phase2_cost
           total_cost_estimate += agent_total
           
           print(f"Agent {agent.name} ({agent.model}): ~{agent_total} tokens")
       
       print(f"Total estimated tokens: ~{total_cost_estimate}")
       return total_cost_estimate

For complete configuration examples and templates, see the ``config/`` directory in the repository.