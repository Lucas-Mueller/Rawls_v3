Designing Experiments
=====================

This guide shows you how to design and configure custom experiments for the Frohlich system, from simple parameter adjustments to complex multi-condition research studies.

Configuration Fundamentals
---------------------------

YAML Structure
~~~~~~~~~~~~~~

All experiments are configured using YAML files with this basic structure:

.. code-block:: yaml

   # Language and basic settings
   language: "english"
   
   # Agent definitions
   agents:
     - name: "Agent_Name"
       personality: "Personality description"
       model: "model_identifier"
       temperature: 0.0
       memory_character_limit: 50000
       reasoning_enabled: true
   
   # Utility agent configuration  
   utility_agent_model: "model_identifier"
   utility_agent_temperature: 0.0
   
   # Phase parameters
   phase2_rounds: 10
   distribution_range_phase2: [4, 8]
   
   # Income class probabilities
   income_class_probabilities:
     high: 0.05
     medium_high: 0.10  
     medium: 0.50
     medium_low: 0.25
     low: 0.10
   
   # Original values mode
   original_values_mode:
     enabled: false
     situation: "sample"

Required vs Optional Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Required Parameters:**

.. code-block:: yaml

   agents:              # At least one agent required
   utility_agent_model: # Model for response parsing

**Optional Parameters (with defaults):**

.. code-block:: yaml

   language: "english"                    # Language interface
   utility_agent_temperature: 0.0        # Deterministic parsing
   phase2_rounds: 3                      # Discussion rounds
   distribution_range_phase2: [0.5, 2.0] # Income multiplier range
   original_values_mode:                 # Use predefined distributions
     enabled: false
   
   # Default income probabilities
   income_class_probabilities:
     high: 0.05
     medium_high: 0.10
     medium: 0.50
     medium_low: 0.25
     low: 0.10

Agent Design Patterns
----------------------

Basic Agent Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Standard Research Agent:**

.. code-block:: yaml

   - name: "Standard_Participant"
     personality: "You are a thoughtful participant who carefully considers different perspectives on fairness and justice."
     model: "gpt-4.1-mini"
     temperature: 0.3
     memory_character_limit: 50000
     reasoning_enabled: true

**Deterministic Agent:**

.. code-block:: yaml

   - name: "Consistent_Participant"
     personality: "You are analytical and systematic in your approach to justice principles."
     model: "gpt-4.1-mini"
     temperature: 0.0          # Deterministic responses
     memory_character_limit: 50000
     reasoning_enabled: true

**High-Creativity Agent:**

.. code-block:: yaml

   - name: "Creative_Participant"
     personality: "You approach problems creatively and think outside conventional frameworks."
     model: "gpt-4.1-mini"
     temperature: 0.8          # High creativity
     memory_character_limit: 75000
     reasoning_enabled: true

Personality Design Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Role-Based Personalities:**

.. code-block:: yaml

   agents:
     - name: "Economist"
       personality: "You are an economics professor who focuses on efficiency and utility maximization. You analyze distribution problems through the lens of economic theory."
       
     - name: "Ethicist"  
       personality: "You are a moral philosopher who prioritizes fairness and considers the ethical implications of different distribution principles."
       
     - name: "Activist"
       personality: "You are a social justice advocate who focuses on helping the most disadvantaged members of society."

**Cultural Perspective Personalities:**

.. code-block:: yaml

   agents:
     - name: "Individualist"
       personality: "You believe in individual merit and that people should be rewarded based on their contributions and efforts."
       
     - name: "Communitarian"
       personality: "You prioritize community welfare and believe society should work together to ensure everyone's basic needs are met."
       
     - name: "Utilitarian"
       personality: "You focus on achieving the greatest good for the greatest number of people overall."

**Cognitive Style Personalities:**

.. code-block:: yaml

   agents:
     - name: "Analytical_Thinker"
       personality: "You are methodical and data-driven. You prefer to analyze problems systematically and base decisions on logical reasoning."
       
     - name: "Intuitive_Thinker" 
       personality: "You rely on intuition and gut feelings. You consider the human and emotional aspects of decisions."
       
     - name: "Pragmatic_Thinker"
       personality: "You focus on practical solutions that can actually be implemented. You consider real-world constraints and feasibility."

Multi-Agent Dynamics
~~~~~~~~~~~~~~~~~~~~~

**Balanced Perspectives (3 agents):**

.. code-block:: yaml

   agents:
     - name: "Moderate"
       personality: "You seek balanced solutions and try to find middle ground between different viewpoints."
       temperature: 0.3
       
     - name: "Progressive"  
       personality: "You advocate for policies that reduce inequality and support those most in need."
       temperature: 0.4
       
     - name: "Conservative"
       personality: "You value stability and believe in rewarding merit and individual responsibility."  
       temperature: 0.2

**Diverse Reasoning Styles (4 agents):**

.. code-block:: yaml

   agents:
     - name: "Logical"
       personality: "You use formal logical reasoning and prefer clear, systematic arguments."
       reasoning_enabled: true
       memory_character_limit: 60000
       
     - name: "Emotional"
       personality: "You consider the emotional and human impact of decisions on real people's lives."
       reasoning_enabled: true
       memory_character_limit: 60000
       
     - name: "Historical"
       personality: "You draw on historical examples and precedents when making decisions about justice."
       reasoning_enabled: true  
       memory_character_limit: 80000
       
     - name: "Practical"
       personality: "You focus on what can realistically be implemented and maintained in practice."
       reasoning_enabled: true
       memory_character_limit: 40000

Experimental Design Patterns
-----------------------------

Single-Variable Studies
~~~~~~~~~~~~~~~~~~~~~~~

**Temperature Variation Study:**

Create multiple config files testing different temperature settings:

.. code-block:: yaml

   # config/temp_low.yaml
   agents:
     - name: "Agent_1"
       temperature: 0.1
     - name: "Agent_2"  
       temperature: 0.1
     - name: "Agent_3"
       temperature: 0.1

   # config/temp_medium.yaml  
   agents:
     - name: "Agent_1"
       temperature: 0.5
     - name: "Agent_2"
       temperature: 0.5
     - name: "Agent_3" 
       temperature: 0.5

   # config/temp_high.yaml
   agents:
     - name: "Agent_1"
       temperature: 0.9
     - name: "Agent_2"
       temperature: 0.9
     - name: "Agent_3"
       temperature: 0.9

**Model Provider Comparison:**

.. code-block:: yaml

   # config/openai_only.yaml
   agents:
     - model: "gpt-4.1-mini"
     - model: "gpt-4.1-mini"
     - model: "gpt-4.1-mini"
   
   # config/openrouter_only.yaml  
   agents:
     - model: "gemini-2.5-flash"
     - model: "gemini-2.5-flash" 
     - model: "gemini-2.5-flash"
     
   # config/mixed_providers.yaml
   agents:
     - model: "gpt-4.1-mini"
     - model: "gemini-2.5-flash"
     - model: "anthropic/claude-3-5-sonnet"

Multi-Variable Studies
~~~~~~~~~~~~~~~~~~~~~~

**Personality × Temperature Interaction:**

.. code-block:: yaml

   # Systematic 2x2 design
   agents:
     - name: "Analytical_Low_Temp"
       personality: "Analytical and systematic approach"
       temperature: 0.1
       
     - name: "Analytical_High_Temp"  
       personality: "Analytical and systematic approach"
       temperature: 0.7
       
     - name: "Intuitive_Low_Temp"
       personality: "Intuitive and empathetic approach"
       temperature: 0.1
       
     - name: "Intuitive_High_Temp"
       personality: "Intuitive and empathetic approach"  
       temperature: 0.7

**Memory × Discussion Length:**

.. code-block:: yaml

   # Short memory, short discussion
   agents:
     - memory_character_limit: 25000
   phase2_rounds: 5
   
   # Long memory, long discussion  
   agents:
     - memory_character_limit: 100000
   phase2_rounds: 15

Language and Cultural Studies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cross-Cultural Comparison:**

.. code-block:: yaml

   # config/english_individualist.yaml
   language: "english"
   agents:
     - personality: "You value individual achievement and personal responsibility."
   
   # config/spanish_communitarian.yaml
   language: "spanish"  
   agents:
     - personality: "Valoras la comunidad y la responsabilidad colectiva."
     
   # config/mandarin_harmony.yaml
   language: "mandarin"
   agents:
     - personality: "你重视和谐与集体利益的平衡。"

Advanced Configuration
----------------------

Original Values Mode Studies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use predefined distribution sets for controlled comparisons:

.. code-block:: yaml

   # Baseline condition
   original_values_mode:
     enabled: true
     situation: "sample"      # Standard distributions
   
   # High inequality condition
   original_values_mode:
     enabled: true  
     situation: "c"           # Extreme outliers
   
   # Middle-class focused condition
   original_values_mode:
     enabled: true
     situation: "d"           # Graduated middle-class

Income Probability Manipulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adjust class probabilities to test specific hypotheses:

.. code-block:: yaml

   # High inequality scenario
   income_class_probabilities:
     high: 0.20        # 20% high income
     medium_high: 0.10
     medium: 0.30  
     medium_low: 0.20
     low: 0.20         # 20% low income
   
   # Middle-class scenario
   income_class_probabilities:
     high: 0.05
     medium_high: 0.20
     medium: 0.50      # 50% middle class
     medium_low: 0.20
     low: 0.05

Phase Parameter Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Quick Pilot Studies:**

.. code-block:: yaml

   phase2_rounds: 3                    # Fast iteration
   distribution_range_phase2: [1, 3]   # Simple multipliers

**Detailed Research Studies:**

.. code-block:: yaml

   phase2_rounds: 20                   # Thorough discussion
   distribution_range_phase2: [0.1, 5] # Wide range of scenarios

Batch Experiment Generation
---------------------------

Programmatic Config Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the experiment runner utilities to generate systematic studies:

.. code-block:: python

   from utils.experiment_runner import generate_and_save_configs

   # Generate 20 random configurations
   generate_and_save_configs(
       num_configs=20,
       save_path="studies/personality_study/configs"
   )

   # Parameters will be randomly varied:
   # - Agent personalities from predefined sets
   # - Temperature values between 0.0-0.8
   # - Memory limits between 25,000-75,000
   # - Discussion rounds between 5-15

Custom Generation Scripts
~~~~~~~~~~~~~~~~~~~~~~~~~

Create systematic parameter sweeps:

.. code-block:: python

   import yaml
   from pathlib import Path

   def create_temperature_study():
       """Generate configs for temperature sensitivity study."""
       temperatures = [0.0, 0.2, 0.4, 0.6, 0.8]
       
       base_config = {
           'language': 'english',
           'agents': [
               {
                   'name': f'Agent_{i}',
                   'personality': 'Standard research participant',
                   'model': 'gpt-4.1-mini',
                   'memory_character_limit': 50000,
                   'reasoning_enabled': True
               } for i in range(1, 4)
           ],
           'utility_agent_model': 'gpt-4.1-mini',
           'phase2_rounds': 10
       }
       
       for temp in temperatures:
           config = base_config.copy()
           for agent in config['agents']:
               agent['temperature'] = temp
               
           filename = f"temperature_study/temp_{temp:.1f}.yaml"
           Path(filename).parent.mkdir(exist_ok=True)
           
           with open(filename, 'w') as f:
               yaml.dump(config, f, default_flow_style=False)

Research Design Best Practices
------------------------------

Experimental Validity
~~~~~~~~~~~~~~~~~~~~~~

**Control Variables:**
- Keep model providers consistent within conditions
- Use identical utility agent settings across experiments
- Maintain consistent phase2_rounds for comparison studies

**Random Assignment:**
- Randomize agent order in multi-agent studies
- Use different random seeds for replication
- Balance personality types across conditions

**Sample Size Planning:**
- Run multiple replications (5-10 per condition minimum)
- Account for API variability in planning
- Consider computational costs in design

Hypothesis Testing Framework
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Clear Research Questions:**

.. code-block:: yaml

   # Example: Do more empathetic personalities prefer principle 1?
   research_question: "Empathy and distributive justice preferences"
   
   conditions:
     - name: "high_empathy"
       agents:
         - personality: "You are highly empathetic and care deeply about others' welfare"
     
     - name: "low_empathy"  
       agents:
         - personality: "You are analytical and focus on logical efficiency"

**Measurable Outcomes:**
- Principle choice frequencies
- Consensus achievement rates
- Discussion length and complexity
- Constraint specification patterns

Replication and Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Configuration Documentation:**

.. code-block:: yaml

   # Always include metadata in configs
   experiment_metadata:
     study_name: "Personality and Justice Study"
     researcher: "Your Name"
     date: "2025-08-19"
     hypothesis: "Empathetic agents prefer redistributive principles"
     condition: "high_empathy"
     replication: 3

**Version Control:**
- Store all configuration files in version control
- Document parameter choices and rationale
- Maintain experiment logs and results systematically

Common Design Patterns
----------------------

Pilot Studies
~~~~~~~~~~~~~

Quick exploration with minimal resources:

.. code-block:: yaml

   # Fast pilot configuration
   agents: [3 agents]                  # Minimum viable group
   phase2_rounds: 5                    # Quick consensus testing
   temperature: 0.3                    # Moderate creativity
   memory_character_limit: 25000       # Reduced memory overhead

Full Research Studies
~~~~~~~~~~~~~~~~~~~~~

Comprehensive investigation with multiple conditions:

.. code-block:: yaml

   # Research-grade configuration
   agents: [4-6 agents]                # Rich group dynamics
   phase2_rounds: 15                   # Thorough discussion
   temperature: [varied]               # Systematic manipulation
   memory_character_limit: 75000       # Full memory capacity

Troubleshooting Configuration Issues
------------------------------------

Common Errors
~~~~~~~~~~~~~

**YAML Syntax Errors:**

.. code-block:: text

   Error: Invalid YAML syntax
   → Check indentation (use spaces, not tabs)
   → Verify quote matching
   → Ensure proper list formatting

**Validation Errors:**

.. code-block:: text

   Error: Agent configuration invalid
   → Verify all required fields present
   → Check model name spelling
   → Ensure temperature in valid range (0.0-1.0)

**Memory Issues:**

.. code-block:: text

   Warning: Memory limit exceeded frequently
   → Increase memory_character_limit
   → Reduce discussion complexity
   → Enable memory cleanup mechanisms

Testing Configurations
~~~~~~~~~~~~~~~~~~~~~~

Always validate new configurations before full studies:

.. code-block:: bash

   # Test configuration validity
   python main.py your_config.yaml

   # Run quick test with reduced parameters
   phase2_rounds: 2  # Override for testing

See Also
--------

* :doc:`running-experiments` - Learn to execute experiments with your custom designs
* :doc:`analyzing-results` - Understand how to analyze and interpret experiment results
* :doc:`../architecture/configuration` - Complete configuration reference
* :doc:`../contributing/testing` - Testing and validation procedures
* :doc:`../hypothesis-testing` - Hypothesis testing framework for batch experiments

For more advanced configuration patterns, see the example configurations in the ``config/`` directory and refer to :doc:`analyzing-results` for interpreting your experimental data.