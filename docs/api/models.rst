Data Models
===========

The models module provides type-safe data structures, configuration classes, and validation logic for the entire Frohlich Experiment system. This comprehensive guide covers all data models with practical usage examples and integration patterns.

.. contents:: Table of Contents
   :local:
   :depth: 2

Model Architecture Overview
---------------------------

The Frohlich Experiment uses Pydantic models for type safety, validation, and serialization across all system components.

.. mermaid::

   graph TD
       subgraph "Configuration Models"
           AC[AgentConfiguration]
           EC[ExperimentConfiguration]
           OV[OriginalValuesModeConfig]
       end
       
       subgraph "Experiment Data Models"
           ID[IncomeDistribution]
           ICP[IncomeClassProbabilities]
           ER[ExperimentResults]
       end
       
       subgraph "Justice Principle Models"
           JP[JusticePrinciple]
           PC[PrincipleChoice]
           CR[ConstraintRequirement]
       end
       
       subgraph "Response Models"
           PR[PrincipleResponse]
           DR[DiscussionResponse]
           VR[VotingResponse]
       end
       
       subgraph "Logging Models"
           AE[AgentEvent]
           ES[ErrorStatistics]
           TS[TraceSettings]
       end
       
       EC --> AC
       EC --> OV
       EC --> ICP
       ER --> ID
       JP --> PC
       JP --> CR
       PR --> PC
       DR --> VR
       AE --> ES

Configuration Models
--------------------

Configuration models define the structure and validation for experiment setup and agent properties.

.. automodule:: config.models
   :members:
   :undoc-members:
   :show-inheritance:

ExperimentConfiguration
~~~~~~~~~~~~~~~~~~~~~~~

The central configuration model that defines all experiment parameters.

.. tabs::

   .. tab:: Basic Configuration

      .. code-block:: python

         from config import ExperimentConfiguration, AgentConfiguration

         # Create basic experiment configuration
         config = ExperimentConfiguration(
             language="English",
             agents=[
                 AgentConfiguration(
                     name="Alice",
                     personality="Analytical and methodical",
                     model="gpt-4.1-mini",
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
             utility_agent_model="gpt-4.1-mini",
             utility_agent_temperature=0.0,
             phase2_rounds=10
         )
         
         # Configuration is automatically validated
         print(f"Experiment has {len(config.agents)} agents")
         print(f"Language: {config.language}")

   .. tab:: Advanced Configuration

      .. code-block:: python

         from models.experiment_types import IncomeClassProbabilities
         from config import (
             OriginalValuesModeConfig,
             Phase2TransparencyConfig,
             LoggingConfig,
             TranscriptLoggingConfig
         )
         from config.phase2_settings import Phase2Settings

         # Advanced configuration with all options
         advanced_config = ExperimentConfiguration(
             language="Spanish",
             agents=[
                 AgentConfiguration(
                     name="Especialista",
                     personality="Experto en teoría de justicia distributiva",
                     model="gpt-4-turbo",
                     temperature=0.2,
                     memory_character_limit=100000,
                     reasoning_enabled=True,
                     language="spanish"
                 ),
                 AgentConfiguration(
                     name="Pragmático",
                     personality="Enfocado en soluciones prácticas",
                     model="anthropic/claude-3-5-sonnet",
                     temperature=0.4,
                     memory_character_limit=75000,
                     language="spanish"
                 ),
                 AgentConfiguration(
                     name="Mediador",
                     personality="Hábil para construir consenso",
                     model="gemini-2.5-pro",
                     temperature=0.3,
                     language="spanish"
                 )
             ],

             # Utility agent configuration
             utility_agent_model="gpt-4.1-mini",
             utility_agent_temperature=0.0,

             # Phase 2 settings
             phase2_rounds=15,
             randomize_speaking_order=True,
             speaking_order_strategy="conversational",

             # Distribution settings
             distribution_range_phase1=(0.8, 1.5),
             distribution_range_phase2=(0.6, 2.0),

             # Income class probabilities
             income_class_probabilities=IncomeClassProbabilities(
                 high=0.08,
                 medium_high=0.12,
                 medium=0.45,
                 medium_low=0.25,
                 low=0.10
             ),

             # Original values mode
             original_values_mode=OriginalValuesModeConfig(
                 enabled=True,
                 situation="sample"
             ),

             # Phase 2 enhanced transparency
             phase2_enhanced_transparency=Phase2TransparencyConfig(
                 enabled=True,
                 detail_level="full",
                 include_counterfactuals=True,
                 include_class_assignment=True,
                 include_insights=True
             ),

             # Logging configuration
             logging=LoggingConfig(
                 verbosity_level="standard",
                 use_colors=True,
                 show_progress_bars=True
             ),

             # Transcript logging
             transcript_logging=TranscriptLoggingConfig(
                 enabled=True,
                 output_path="custom_transcripts/",
                 include_memory_updates=False,
                 include_instructions=False,
                 include_input_prompts=True,
                 include_agent_responses=True
             ),

             # Memory optimization
             memory_guidance_style="structured",
             include_experiment_explanation=True,
             include_experiment_explanation_each_turn=False,
             phase2_include_internal_reasoning_in_memory=True,

             # Selective memory updates
             selective_memory_updates=True,
             memory_update_threshold="moderate",
             batch_simple_events=False,

             # Intelligent retry mechanism
             enable_intelligent_retries=True,
             max_participant_retries=2,
             enable_progressive_guidance=True,
             memory_update_on_retry=True,
             retry_feedback_detail="concise",

             # Reproducibility
             seed=42,

             # Manipulator configuration (for Hypothesis 3)
             manipulator={
                 "enabled": False,
                 "type": "disruptive",
                 "intervention_round": 5
             },

             # Phase 2 specific settings (imported from phase2_settings.py)
             phase2_settings=None  # Use defaults or specify Phase2Settings object
         )

   .. tab:: Multi-Language Setup

      .. code-block:: python

         # Create configurations for different languages
         languages = ["English", "Spanish", "Mandarin"]
         
         configs = {}
         for lang in languages:
             configs[lang] = ExperimentConfiguration(
                 language=lang,
                 agents=[
                     AgentConfiguration(
                         name=f"Agent1_{lang}",
                         personality=get_personality_for_language(lang),
                         model=get_optimal_model_for_language(lang),
                         temperature=0.3
                     ),
                     AgentConfiguration(
                         name=f"Agent2_{lang}",
                         personality=get_personality_for_language(lang),
                         model=get_optimal_model_for_language(lang),
                         temperature=0.3
                     )
                 ],
                 phase2_rounds=12,
                 seed=get_language_seed(lang)
             )

**Configuration Validation**

.. code-block:: python

   # Validation examples
   try:
       # This will raise a validation error
       invalid_config = ExperimentConfiguration(
           language="InvalidLanguage",  # Not supported
           agents=[],  # Too few agents
           phase2_rounds=-5  # Negative value
       )
   except ValueError as e:
       print(f"Validation error: {e}")

   # Validate configuration from YAML
   try:
       config = ExperimentConfiguration.from_yaml("config/my_config.yaml")
       print("Configuration loaded successfully")
   except FileNotFoundError:
       print("Configuration file not found")
   except ValueError as e:
       print(f"Configuration validation failed: {e}")

AgentConfiguration
~~~~~~~~~~~~~~~~~~

Detailed agent configuration with validation and defaults.

.. code-block:: python

   # Comprehensive agent configuration examples
   agent_configs = {
       "minimal": AgentConfiguration(
           name="MinimalAgent",
           personality="Simple and direct",
           model="gpt-4.1-mini"
           # Other parameters use defaults
       ),
       
       "optimized": AgentConfiguration(
           name="OptimizedAgent",
           personality="Efficient and focused",
           model="gemini-2.5-flash",
           temperature=0.0,  # Deterministic
           memory_character_limit=30000,  # Smaller memory
           reasoning_enabled=False  # Skip reasoning for speed
       ),
       
       "research": AgentConfiguration(
           name="ResearchAgent",
           personality="""You are a research scientist studying distributive 
                         justice. You approach problems systematically and 
                         consider multiple theoretical frameworks.""",
           model="gpt-4-turbo",
           temperature=0.2,
           memory_character_limit=150000,  # Large memory
           reasoning_enabled=True
       )
   }

Experiment Types
----------------

Core data models for experiment execution and results.

.. automodule:: models.experiment_types
   :members:
   :undoc-members:
   :show-inheritance:

IncomeDistribution
~~~~~~~~~~~~~~~~~~

Represents income distributions used throughout experiments.

.. tabs::

   .. tab:: Basic Usage

      .. code-block:: python

         from models.experiment_types import IncomeDistribution

         # Create income distribution
         distribution = IncomeDistribution(
             high=32000,
             medium_high=27000,
             medium=24000,
             medium_low=13000,
             low=12000
         )
         
         # Access distribution properties
         print(f"Floor income: ${distribution.get_floor_income():,}")
         print(f"Average income: ${distribution.get_average_income():,.2f}")
         print(f"Income range: ${distribution.get_range():,}")
         print(f"Total income: ${distribution.get_total_income():,}")

   .. tab:: Analysis Methods

      .. code-block:: python

         # Advanced distribution analysis
         distribution = IncomeDistribution(
             high=45000, medium_high=35000, medium=28000,
             medium_low=18000, low=15000
         )
         
         # Statistical measures
         gini = distribution.calculate_gini_coefficient()
         percentile_90_10 = distribution.get_percentile_ratio(90, 10)
         median = distribution.get_median_income()
         
         print(f"Gini coefficient: {gini:.3f}")
         print(f"90/10 percentile ratio: {percentile_90_10:.2f}")
         print(f"Median income: ${median:,}")
         
         # Distribution categorization
         if distribution.is_highly_unequal():
             print("High inequality distribution")
         elif distribution.is_egalitarian():
             print("Egalitarian distribution")
         else:
             print("Moderate inequality distribution")

   .. tab:: Comparative Analysis

      .. code-block:: python

         # Compare multiple distributions
         distributions = [
             IncomeDistribution(high=50000, medium_high=40000, medium=30000, medium_low=20000, low=10000),
             IncomeDistribution(high=35000, medium_high=30000, medium=25000, medium_low=20000, low=15000),
             IncomeDistribution(high=60000, medium_high=25000, medium=20000, medium_low=15000, low=5000)
         ]
         
         # Analyze each distribution
         for i, dist in enumerate(distributions, 1):
             print(f"Distribution {i}:")
             print(f"  Average: ${dist.get_average_income():,.2f}")
             print(f"  Floor: ${dist.get_floor_income():,}")
             print(f"  Gini: {dist.calculate_gini_coefficient():.3f}")
             print(f"  Preferred by: {get_principle_preferences(dist)}")

**Distribution Validation**

.. code-block:: python

   # Validation and error handling
   try:
       # This will raise validation error
       invalid_dist = IncomeDistribution(
           high=-1000,  # Negative income
           medium_high=25000,
           medium=30000,  # Higher than medium_high
           medium_low=15000,
           low=10000
       )
   except ValueError as e:
       print(f"Distribution validation failed: {e}")

   # Valid distribution creation with checks
   def create_valid_distribution(values):
       """Create distribution with additional validation."""
       dist = IncomeDistribution(**values)
       
       # Custom business logic validation
       if dist.get_range() > 100000:
           raise ValueError("Income range too large for experiment")
       
       if dist.get_floor_income() < 5000:
           raise ValueError("Floor income below minimum living wage")
       
       return dist

IncomeClassProbabilities
~~~~~~~~~~~~~~~~~~~~~~~~

Defines probabilities for income class assignment in experiments.

.. code-block:: python

   from models.experiment_types import IncomeClassProbabilities

   # Standard probability distribution
   standard_probs = IncomeClassProbabilities(
       high=0.05,      # 5%
       medium_high=0.10, # 10%  
       medium=0.50,    # 50%
       medium_low=0.25, # 25%
       low=0.10        # 10%
   )
   
   # Verify probabilities sum to 1.0
   total = standard_probs.get_total_probability()
   assert abs(total - 1.0) < 0.001, f"Probabilities sum to {total}, not 1.0"
   
   # Different scenarios
   scenarios = {
       "equal": IncomeClassProbabilities(
           high=0.2, medium_high=0.2, medium=0.2, medium_low=0.2, low=0.2
       ),
       "bottom_heavy": IncomeClassProbabilities(
           high=0.02, medium_high=0.05, medium=0.23, medium_low=0.35, low=0.35
       ),
       "top_heavy": IncomeClassProbabilities(
           high=0.15, medium_high=0.25, medium=0.35, medium_low=0.15, low=0.10
       )
   }

Principle Types
---------------

Models representing justice principles and their applications.

.. automodule:: models.principle_types
   :members:
   :undoc-members:
   :show-inheritance:

JusticePrinciple
~~~~~~~~~~~~~~~~

Enumeration and data structures for justice principles.

.. tabs::

   .. tab:: Principle Types

      .. code-block:: python

         from models.principle_types import JusticePrinciple, PrincipleChoice

         # Available justice principles
         principles = [
             JusticePrinciple.MAXIMIZING_FLOOR,
             JusticePrinciple.MAXIMIZING_AVERAGE,
             JusticePrinciple.MAXIMIZING_AVERAGE_WITH_FLOOR,
             JusticePrinciple.MAXIMIZING_AVERAGE_WITH_RANGE
         ]
         
         # Create principle choices
         choices = [
             PrincipleChoice(
                 principle=JusticePrinciple.MAXIMIZING_FLOOR,
                 confidence_level="high",
                 reasoning="Protects the most vulnerable members of society"
             ),
             PrincipleChoice(
                 principle=JusticePrinciple.MAXIMIZING_AVERAGE_WITH_FLOOR,
                 constraint_amount=15000,  # Required for constrained principles
                 confidence_level="medium",
                 reasoning="Balances efficiency with fairness"
             )
         ]

   .. tab:: Constraint Handling

      .. code-block:: python

         from models.principle_types import ConstraintRequirement

         # Validate constraint requirements
         def validate_principle_choice(choice: PrincipleChoice) -> bool:
             """Validate that principle choice meets requirements."""
             
             constraint_req = ConstraintRequirement.get_requirement(choice.principle)
             
             if constraint_req.requires_constraint:
                 if choice.constraint_amount is None:
                     raise ValueError(f"{choice.principle} requires constraint amount")
                 
                 if choice.constraint_amount < constraint_req.min_amount:
                     raise ValueError(f"Constraint too low: {choice.constraint_amount}")
                 
                 if choice.constraint_amount > constraint_req.max_amount:
                     raise ValueError(f"Constraint too high: {choice.constraint_amount}")
             
             return True
         
         # Example validation
         try:
             choice = PrincipleChoice(
                 principle=JusticePrinciple.MAXIMIZING_AVERAGE_WITH_FLOOR,
                 constraint_amount=12000,
                 confidence_level="high"
             )
             validate_principle_choice(choice)
             print("Choice is valid")
         except ValueError as e:
             print(f"Invalid choice: {e}")

   .. tab:: Principle Analysis

      .. code-block:: python

         # Analyze principle applications
         def analyze_principle_application(principle: JusticePrinciple, 
                                         distributions: List[IncomeDistribution],
                                         constraint_amount: Optional[int] = None) -> IncomeDistribution:
             """Apply principle to choose best distribution."""
             
             if principle == JusticePrinciple.MAXIMIZING_FLOOR:
                 return max(distributions, key=lambda d: d.get_floor_income())
             
             elif principle == JusticePrinciple.MAXIMIZING_AVERAGE:
                 return max(distributions, key=lambda d: d.get_average_income())
             
             elif principle == JusticePrinciple.MAXIMIZING_AVERAGE_WITH_FLOOR:
                 # Filter distributions meeting floor constraint
                 valid_dists = [d for d in distributions 
                               if d.get_floor_income() >= constraint_amount]
                 if not valid_dists:
                     return None  # No valid distribution
                 return max(valid_dists, key=lambda d: d.get_average_income())
             
             elif principle == JusticePrinciple.MAXIMIZING_AVERAGE_WITH_RANGE:
                 # Filter distributions meeting range constraint
                 valid_dists = [d for d in distributions 
                               if d.get_range() <= constraint_amount]
                 if not valid_dists:
                     return None
                 return max(valid_dists, key=lambda d: d.get_average_income())

Response Types
--------------

Models for agent responses and experimental interactions.

.. automodule:: models.response_types
   :members:
   :undoc-members:
   :show-inheritance:

Agent Response Models
~~~~~~~~~~~~~~~~~~~~~

Structured responses from agents during different experimental phases.

.. tabs::

   .. tab:: Phase 1 Responses

      .. code-block:: python

         from models.response_types import PrincipleResponse, ConfidenceLevel

         # Phase 1 principle application response
         phase1_response = PrincipleResponse(
             chosen_principle=JusticePrinciple.MAXIMIZING_FLOOR,
             chosen_distribution_index=3,  # Index in provided distributions
             confidence_level=ConfidenceLevel.HIGH,
             reasoning="""I chose the maximizing floor principle because it ensures
                         that the most vulnerable members of society are protected.
                         This aligns with my values of social justice and fairness.""",
             constraint_amount=None,  # Not needed for this principle
             response_time_seconds=45.2,
             memory_update="Updated understanding of floor principle advantages"
         )
         
         # Validate response completeness
         if phase1_response.is_complete():
             print("Response is complete and valid")
         else:
             print("Response missing required fields")

   .. tab:: Phase 2 Discussion Responses

      .. code-block:: python

         from models.response_types import DiscussionResponse

         # Phase 2 discussion turn response
         discussion_response = DiscussionResponse(
             agent_name="Alice",
             round_number=3,
             internal_reasoning="""The group seems divided between maximizing average
                                 and maximizing floor. I should propose a compromise
                                 that addresses both concerns.""",
             public_statement="""I hear valid points from both sides. Perhaps we could
                               consider maximizing average with a floor constraint?
                               This would ensure efficiency while protecting the vulnerable.""",
             proposes_vote=False,
             addresses_other_agents=["Bob", "Carol"],
             response_time_seconds=67.8,
             emotional_tone="collaborative"
         )

   .. tab:: Voting Responses

      .. code-block:: python

         from models.response_types import VotingResponse

         # Voting response with constraint
         voting_response = VotingResponse(
             agent_name="Bob", 
             round_number=5,
             chosen_principle=JusticePrinciple.MAXIMIZING_AVERAGE_WITH_FLOOR,
             constraint_amount=18000,
             confidence_level=ConfidenceLevel.MEDIUM,
             reasoning="""After our discussion, I believe this compromise
                         addresses both efficiency and fairness concerns.""",
             changed_from_initial=True,
             initial_preference=JusticePrinciple.MAXIMIZING_AVERAGE,
             response_time_seconds=23.1
         )
         
         # Validate voting response
         if voting_response.requires_constraint() and voting_response.constraint_amount:
             print(f"Valid vote: {voting_response.chosen_principle} with ${voting_response.constraint_amount:,}")
         elif not voting_response.requires_constraint():
             print(f"Valid vote: {voting_response.chosen_principle}")
         else:
             print("Invalid vote: missing required constraint")

**Response Aggregation and Analysis**

.. code-block:: python

   # Aggregate responses across experiments
   def aggregate_responses(responses: List[PrincipleResponse]) -> Dict:
       """Aggregate principle responses for analysis."""
       
       aggregation = {
           'principle_counts': {},
           'confidence_distribution': {},
           'average_response_time': 0,
           'constraint_amounts': {}
       }
       
       for response in responses:
           # Count principle choices
           principle = response.chosen_principle
           aggregation['principle_counts'][principle] = aggregation['principle_counts'].get(principle, 0) + 1
           
           # Count confidence levels
           confidence = response.confidence_level
           aggregation['confidence_distribution'][confidence] = aggregation['confidence_distribution'].get(confidence, 0) + 1
           
           # Track constraint amounts for constrained principles
           if response.constraint_amount:
               if principle not in aggregation['constraint_amounts']:
                   aggregation['constraint_amounts'][principle] = []
               aggregation['constraint_amounts'][principle].append(response.constraint_amount)
       
       # Calculate average response time
       if responses:
           aggregation['average_response_time'] = sum(r.response_time_seconds for r in responses) / len(responses)
       
       return aggregation

Logging Types
-------------

Models for comprehensive experiment logging and tracing.

.. automodule:: models.logging_types
   :members:
   :undoc-members:
   :show-inheritance:

Event Logging
~~~~~~~~~~~~~

Structured logging for experiment events and agent activities.

.. tabs::

   .. tab:: Agent Events

      .. code-block:: python

         from models.logging_types import AgentEvent, EventType, EventSeverity

         # Log agent events throughout experiment
         events = [
             AgentEvent(
                 timestamp=datetime.now(),
                 agent_name="Alice",
                 event_type=EventType.PRINCIPLE_APPLICATION,
                 severity=EventSeverity.INFO,
                 message="Applied maximizing floor principle to distribution set",
                 details={
                     "principle": "maximizing_floor",
                     "chosen_distribution": 3,
                     "reasoning_length": 247,
                     "confidence": "high"
                 },
                 phase="phase1",
                 round_number=2
             ),
             AgentEvent(
                 timestamp=datetime.now(),
                 agent_name="Bob",
                 event_type=EventType.MEMORY_UPDATE,
                 severity=EventSeverity.INFO,
                 message="Updated memory with principle application results",
                 details={
                     "memory_before_length": 1200,
                     "memory_after_length": 1450,
                     "update_type": "principle_learning"
                 },
                 phase="phase1",
                 round_number=2
             ),
             AgentEvent(
                 timestamp=datetime.now(),
                 agent_name="Carol",
                 event_type=EventType.ERROR,
                 severity=EventSeverity.WARNING,
                 message="Memory limit exceeded, attempting compression",
                 details={
                     "memory_limit": 50000,
                     "current_usage": 52340,
                     "compression_attempted": True
                 },
                 phase="phase2",
                 round_number=7
             )
         ]

   .. tab:: Error Statistics

      .. code-block:: python

         from models.logging_types import ErrorStatistics, ErrorCategory

         # Track error statistics throughout experiment
         error_stats = ErrorStatistics(
             total_errors=7,
             errors_by_category={
                 ErrorCategory.MEMORY_ERROR: 3,
                 ErrorCategory.VALIDATION_ERROR: 2,
                 ErrorCategory.COMMUNICATION_ERROR: 1,
                 ErrorCategory.SYSTEM_ERROR: 1
             },
             errors_by_agent={
                 "Alice": 2,
                 "Bob": 1,
                 "Carol": 3,
                 "UtilityAgent": 1
             },
             recovery_success_rate=0.86,
             average_retry_count=2.3
         )
         
         # Generate error report
         report = error_stats.generate_report()
         print(report)

   .. tab:: Performance Metrics

      .. code-block:: python

         from models.logging_types import PerformanceMetrics

         # Track performance metrics
         performance = PerformanceMetrics(
             experiment_duration_seconds=1247.8,
             phase1_duration_seconds=523.2,
             phase2_duration_seconds=724.6,
             total_api_calls=67,
             total_tokens_used=45230,
             average_response_time=18.4,
             memory_usage_peak_mb=156.7,
             consensus_achieved=True,
             consensus_rounds=8,
             agent_participation_balance=0.92  # How evenly agents participated
         )
         
         # Analyze performance
         if performance.is_efficient():
             print("Experiment performed efficiently")
         else:
             print("Performance issues detected")
             print(performance.get_optimization_suggestions())

Data Serialization and Persistence
-----------------------------------

Working with model serialization for data persistence and analysis.

.. tabs::

   .. tab:: JSON Serialization

      .. code-block:: python

         import json
         from models.experiment_types import ExperimentResults

         # Serialize experiment results
         results = ExperimentResults(
             experiment_id="exp_2025_0822_001",
             configuration=config,
             phase1_results=phase1_data,
             phase2_results=phase2_data,
             error_statistics=error_stats,
             performance_metrics=performance
         )
         
         # Convert to JSON
         results_json = results.model_dump_json(indent=2)
         
         # Save to file
         with open("experiment_results.json", "w") as f:
             f.write(results_json)
         
         # Load from JSON
         with open("experiment_results.json", "r") as f:
             loaded_json = f.read()
         
         loaded_results = ExperimentResults.model_validate_json(loaded_json)
         print(f"Loaded experiment: {loaded_results.experiment_id}")

   .. tab:: Database Integration

      .. code-block:: python

         # Convert models to database-compatible format
         def model_to_db_record(model: BaseModel, table_name: str) -> Dict:
             """Convert Pydantic model to database record."""
             
             record = model.model_dump()
             record['table_name'] = table_name
             record['created_at'] = datetime.now().isoformat()
             
             # Handle nested models
             for key, value in record.items():
                 if isinstance(value, BaseModel):
                     record[key] = value.model_dump_json()
                 elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
                     record[key] = [item.model_dump() for item in value]
             
             return record
         
         # Save to database (example)
         db_record = model_to_db_record(config, "experiment_configurations")
         # database.save(db_record)

   .. tab:: Data Migration

      .. code-block:: python

         # Handle model version migration
         def migrate_model_data(old_data: Dict, target_version: str) -> Dict:
             """Migrate old model data to new format."""
             
             if target_version == "2.0":
                 # Add new fields introduced in v2.0
                 if 'memory_character_limit' not in old_data.get('agents', [{}])[0]:
                     for agent in old_data.get('agents', []):
                         agent['memory_character_limit'] = 50000
                 
                 if 'reasoning_enabled' not in old_data.get('agents', [{}])[0]:
                     for agent in old_data.get('agents', []):
                         agent['reasoning_enabled'] = True
                 
                 # Convert old field names
                 if 'max_rounds' in old_data:
                     old_data['phase2_rounds'] = old_data.pop('max_rounds')
             
             return old_data

Model Validation and Testing
-----------------------------

Testing and validation patterns for data models.

.. code-block:: python

   import pytest
   from pydantic import ValidationError

   def test_model_validation():
       """Test model validation behavior."""
       
       # Test valid model creation
       valid_config = AgentConfiguration(
           name="TestAgent",
           personality="Test personality",
           model="gpt-4.1-mini",
           temperature=0.5
       )
       assert valid_config.name == "TestAgent"
       
       # Test validation errors
       with pytest.raises(ValidationError) as exc_info:
           AgentConfiguration(
               name="",  # Empty name should fail
               personality="Test",
               model="invalid-model",
               temperature=3.0  # Out of range
           )
       
       errors = exc_info.value.errors()
       assert len(errors) >= 2  # Multiple validation errors

   def test_model_serialization():
       """Test model serialization roundtrip."""
       
       original = IncomeDistribution(
           high=50000, medium_high=40000, medium=30000,
           medium_low=20000, low=10000
       )
       
       # Serialize to JSON and back
       json_data = original.model_dump_json()
       restored = IncomeDistribution.model_validate_json(json_data)
       
       assert original == restored
       assert original.get_average_income() == restored.get_average_income()

See Also
--------

- :doc:`core` - How core modules use these data models
- :doc:`agents` - Agent interactions with data models
- :doc:`../user-guide/designing-experiments` - Using configuration models in practice
- :doc:`../user-guide/analyzing-results` - Working with result data models
- :doc:`../architecture/configuration` - Detailed configuration architecture