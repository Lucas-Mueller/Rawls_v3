Agent Modules
=============

The agent modules implement sophisticated AI agents that participate in justice principle experiments. This comprehensive guide covers agent architecture, customization patterns, and advanced usage scenarios.

.. contents:: Table of Contents
   :local:
   :depth: 2

Agent Architecture Overview
---------------------------

The Frohlich Experiment system uses a multi-agent architecture with specialized agent types designed for different roles in the experimental process.

.. mermaid::

   graph TB
       subgraph "Agent Ecosystem"
           PA[Participant Agents]
           UA[Utility Agent]
           LM[Language Manager]
           MM[Memory Manager]
       end
       
       subgraph "Participant Agent Features"
           P1[Configurable Personalities]
           P2[Multi-Model Support]
           P3[Self-Managed Memory]
           P4[Multi-Language Reasoning]
       end
       
       subgraph "Utility Agent Features"
           U1[Response Validation]
           U2[Data Parsing]
           U3[Constraint Checking]
           U4[Error Detection]
       end
       
       PA --> P1
       PA --> P2
       PA --> P3
       PA --> P4
       
       UA --> U1
       UA --> U2
       UA --> U3
       UA --> U4
       
       PA --> MM
       PA --> LM
       UA --> LM

Participant Agents
------------------

Participant agents are the primary experimental subjects that reason about justice principles, engage in discussions, and make decisions throughout the experiment.

.. automodule:: experiment_agents.participant_agent
   :members:
   :undoc-members:
   :show-inheritance:

Agent Creation and Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Basic Agent Creation

      .. code-block:: python

         from experiment_agents import create_participant_agent
         from config import AgentConfiguration

         # Create basic participant agent
         agent_config = AgentConfiguration(
             name="Alice",
             personality="Analytical and methodical researcher",
             model="gpt-4.1-mini",
             temperature=0.0,
             memory_character_limit=50000,
             reasoning_enabled=True
         )
         
         agent = await create_participant_agent(agent_config)
         
         # Agent is ready for experiment participation
         print(f"Created agent: {agent.name}")
         print(f"Model: {agent.model}")
         print(f"Personality: {agent.personality}")

   .. tab:: Multi-Provider Configuration

      .. code-block:: python

         # Using different model providers
         openai_agent = AgentConfiguration(
             name="OpenAI_Agent",
             personality="Precise and analytical",
             model="gpt-4.1-mini",  # OpenAI model
             temperature=0.0
         )
         
         openrouter_agent = AgentConfiguration(
             name="Gemini_Agent", 
             personality="Creative and empathetic",
             model="gemini-2.5-flash",  # OpenRouter model
             temperature=0.5
         )
         
         claude_agent = AgentConfiguration(
             name="Claude_Agent",
             personality="Thoughtful and balanced",
             model="anthropic/claude-3-5-sonnet",  # OpenRouter model
             temperature=0.3
         )

   .. tab:: Advanced Customization

      .. code-block:: python

         # Highly customized agent with specific traits
         custom_agent = AgentConfiguration(
             name="Specialist",
             personality="""You are an expert in distributive justice theory 
                           with a background in economics and philosophy. You 
                           approach problems systematically and always consider
                           both utilitarian and deontological perspectives.""",
             model="gpt-4-turbo",
             temperature=0.2,
             memory_character_limit=100000,  # Large memory for complex reasoning
             reasoning_enabled=True
         )

**Personality Design Patterns**

Effective agent personalities should be specific, actionable, and relevant to justice reasoning:

.. code-block:: python

   # Good personality examples
   personalities = {
       "utilitarian": "You prioritize the greatest good for the greatest number",
       "egalitarian": "You believe in equal treatment and fair distribution",
       "rawlsian": "You support justice as fairness behind a veil of ignorance",
       "libertarian": "You emphasize individual rights and minimal redistribution",
       "pragmatist": "You focus on practical solutions that can be implemented",
       "consensus_builder": "You work to find common ground and build agreement"
   }

Agent Memory Management
~~~~~~~~~~~~~~~~~~~~~~~

Agents in the Frohlich Experiment maintain their own memory throughout the experimental process.

.. tabs::

   .. tab:: Memory System Overview

      .. code-block:: python

         from utils.memory_manager import MemoryManager
         
         # Memory is automatically managed by agents
         agent = await create_participant_agent(config)
         
         # After each experimental step, agents update their memory
         await agent.update_memory(
             step_type="principle_application",
             input_data="Justice principle selection task", 
             output_data="Selected maximizing floor income",
             reasoning="This principle protects the most vulnerable..."
         )
         
         # Access current memory
         current_memory = agent.get_current_memory()
         print(f"Memory usage: {len(current_memory)} characters")

   .. tab:: Memory Configuration

      .. code-block:: python

         # Different memory strategies
         memory_configs = [
             # Minimal memory for simple tasks
             AgentConfiguration(
                 name="SimpleAgent",
                 memory_character_limit=25000,
                 personality="Focused and concise"
             ),
             
             # Standard memory for typical experiments  
             AgentConfiguration(
                 name="StandardAgent",
                 memory_character_limit=50000,
                 personality="Balanced and thoughtful"
             ),
             
             # Extended memory for complex reasoning
             AgentConfiguration(
                 name="DeepThinker", 
                 memory_character_limit=150000,
                 personality="Comprehensive and analytical"
             )
         ]

   .. tab:: Memory Optimization

      .. code-block:: python

         # Memory guidance styles
         structured_config = ExperimentConfiguration(
             memory_guidance_style="structured",  # Bullet points, organized
             agents=[
                 AgentConfiguration(
                     name="StructuredAgent",
                     personality="Organized and systematic"
                 )
             ]
         )
         
         narrative_config = ExperimentConfiguration(
             memory_guidance_style="narrative",  # Free-form narrative
             agents=[
                 AgentConfiguration(
                     name="NarrativeAgent", 
                     personality="Storytelling and contextual"
                 )
             ]
         )

Agent Interaction Patterns
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Phase 1: Individual Principle Application**

.. code-block:: python

   async def demonstrate_phase1_interaction():
       """Show how agents interact with justice principles."""
       
       # Agent receives justice principle information
       principle_info = {
           "principle": "maximizing_floor",
           "description": "Maximize the income of the worst-off individual",
           "distributions": [dist1, dist2, dist3, dist4]
       }
       
       # Agent processes and responds
       response = await agent.apply_principle(principle_info)
       
       # Response includes chosen distribution and reasoning
       print(f"Agent chose: {response.chosen_distribution}")
       print(f"Reasoning: {response.reasoning}")
       print(f"Confidence: {response.confidence_level}")

**Phase 2: Group Discussion**

.. code-block:: python

   async def demonstrate_phase2_interaction():
       """Show how agents participate in group discussions."""
       
       # Agent receives discussion context
       discussion_context = {
           "current_round": 2,
           "total_rounds": 10,
           "public_history": "Previous discussion transcript...",
           "other_agents": ["Alice", "Bob"]
       }
       
       # Agent provides reasoning (internal) and statement (public)
       response = await agent.participate_in_discussion(discussion_context)
       
       print(f"Internal reasoning: {response.internal_reasoning}")
       print(f"Public statement: {response.public_statement}")
       
       # Agent can also propose voting
       if response.proposes_vote:
           print("Agent proposes to take a vote")

**Voting Behavior**

.. code-block:: python

   async def demonstrate_voting():
       """Show agent voting behavior."""
       
       voting_context = {
           "available_principles": [
               "maximizing_floor",
               "maximizing_average", 
               "maximizing_average_with_floor",
               "maximizing_average_with_range"
           ],
           "discussion_history": "Full transcript of discussions..."
       }
       
       vote = await agent.cast_vote(voting_context)
       
       print(f"Agent votes for: {vote.chosen_principle}")
       if vote.constraint_amount:
           print(f"With constraint: ${vote.constraint_amount:,}")
       print(f"Reasoning: {vote.reasoning}")

Multi-Language Agent Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Agents can operate in multiple languages with full experimental support.

.. tabs::

   .. tab:: English Agents

      .. code-block:: python

         english_config = ExperimentConfiguration(
             language="English",
             agents=[
                 AgentConfiguration(
                     name="EnglishAgent",
                     personality="You are a thoughtful American college student",
                     model="gpt-4.1-mini"
                 )
             ]
         )

   .. tab:: Spanish Agents

      .. code-block:: python

         spanish_config = ExperimentConfiguration(
             language="Spanish", 
             agents=[
                 AgentConfiguration(
                     name="AgentEspa?ol",
                     personality="Eres un estudiante universitario espa?ol reflexivo",
                     model="gemini-2.5-flash"
                 )
             ]
         )

   .. tab:: Mandarin Agents

      .. code-block:: python

         mandarin_config = ExperimentConfiguration(
             language="Mandarin",
             agents=[
                 AgentConfiguration(
                     name="??Agent",
                     personality="??????????????", 
                     model="anthropic/claude-3-5-sonnet"
                 )
             ]
         )

**Language-Specific Behavior**

.. code-block:: python

   # Language manager handles all translations automatically
   from utils.language_manager import get_language_manager, SupportedLanguage
   
   # Set experiment language
   language_manager = get_language_manager(SupportedLanguage.SPANISH)
   
   # All agent prompts and responses will be in Spanish
   # Justice principle names translated appropriately
   # Discussion conducted entirely in target language

Utility Agent
-------------

The utility agent provides specialized services for response validation, data parsing, and constraint checking throughout the experiment.

.. automodule:: experiment_agents.utility_agent
   :members:
   :undoc-members:
   :show-inheritance:

Core Functionality
~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Response Validation

      .. code-block:: python

         from experiment_agents.utility_agent import UtilityAgent
         
         # Create utility agent
         utility_config = AgentConfiguration(
             name="UtilityAgent",
             model="gpt-4.1-mini",
             temperature=0.0  # Deterministic for consistent parsing
         )
         
         utility_agent = UtilityAgent(
            utility_model="gpt-4.1-mini",
            temperature=0.0,
            experiment_language="english",
            language_manager=language_manager
        )
        await utility_agent.async_init()  # Required async initialization
         
         # Validate participant response
         participant_response = """
         I choose the maximizing floor income principle because it ensures
         that the most vulnerable members of society are protected...
         """
         
         validation_result = await utility_agent.validate_response(
             response_text=participant_response,
             expected_format="principle_choice",
             context="phase1_application"
         )
         
         if validation_result.is_valid:
             print(f"Valid response: {validation_result.parsed_data}")
         else:
             print(f"Validation error: {validation_result.error_message}")

   .. tab:: Data Parsing

      .. code-block:: python

         # Parse complex agent responses
         complex_response = """
         After careful consideration, I believe the maximizing average 
         income with floor constraint approach is most just. I would set 
         the floor constraint at $15,000 to ensure basic needs are met.
         My confidence level in this choice is high.
         """
         
         parsed_data = await utility_agent.parse_response(
             response_text=complex_response,
             parse_type="principle_with_constraint"
         )
         
         print(f"Principle: {parsed_data.principle}")
         print(f"Constraint: ${parsed_data.constraint_amount:,}")
         print(f"Confidence: {parsed_data.confidence}")

   .. tab:: Constraint Validation

      .. code-block:: python

         # Validate constraint specifications
         vote_response = "I vote for maximizing average with floor constraint"
         
         constraint_check = await utility_agent.validate_constraint_specification(
             principle="maximizing_average_with_floor",
             response_text=vote_response
         )
         
         if not constraint_check.has_required_constraint:
             # Send feedback to participant
             feedback = await utility_agent.generate_constraint_feedback(
                 principle="maximizing_average_with_floor",
                 missing_constraint="floor_amount"
             )
             print(f"Feedback: {feedback}")

**Multi-Language Parsing Support**

.. code-block:: python

   # Utility agent handles multi-language responses
   spanish_response = """
   Elijo el principio de maximizar el ingreso promedio con restricci?n 
   de piso. Establecer?a el piso en $12,000.
   """
   
   # Parse in Spanish context
   spanish_utility = UtilityAgent(
       utility_model="gpt-4.1-mini",
       temperature=0.0,
       experiment_language="spanish",
       language_manager=spanish_language_manager
   )
   await spanish_utility.async_init()  # Required async initialization
   parsed_spanish = await spanish_utility.parse_response(
       response_text=spanish_response,
       parse_type="principle_with_constraint"
   )

Advanced Agent Patterns
-----------------------

Specialized Agent Types
~~~~~~~~~~~~~~~~~~~~~~~

**Consensus Builder Agent**

.. code-block:: python

   consensus_builder = AgentConfiguration(
       name="Mediator",
       personality="""You are skilled at finding common ground and building 
                     consensus. You listen carefully to all perspectives and 
                     propose compromises that address everyone's concerns.""",
       model="gpt-4-turbo",
       temperature=0.4,  # Moderate creativity for compromise solutions
       reasoning_enabled=True
   )

**Devil's Advocate Agent**

.. code-block:: python

   devils_advocate = AgentConfiguration(
       name="Challenger", 
       personality="""You critically examine proposals and point out potential
                     flaws or unintended consequences. You help the group think
                     more deeply by raising important objections.""",
       model="anthropic/claude-3-5-sonnet",
       temperature=0.6,  # Higher creativity for generating counter-arguments
       reasoning_enabled=True
   )

**Domain Expert Agent**

.. code-block:: python

   expert_agent = AgentConfiguration(
       name="EconomicsExpert",
       personality="""You have deep expertise in economics and distributive 
                     justice theory. You draw on academic knowledge to inform
                     discussions and can explain complex trade-offs.""",
       model="gpt-4-turbo",
       temperature=0.2,  # Lower temperature for more factual responses
       memory_character_limit=100000  # Large memory for knowledge retention
   )

Agent Interaction Networks
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Analyzing Agent Relationships**

.. code-block:: python

   def analyze_agent_interactions(experiment_results):
       """Analyze how agents interact with each other."""
       
       phase2_results = experiment_results['phase2_results']
       interaction_matrix = {}
       
       for round_data in phase2_results['discussion_rounds']:
           for turn in round_data['agent_turns']:
               speaker = turn['agent_name']
               message = turn['message']
               
               # Count mentions of other agents
               for other_agent in get_agent_names():
                   if other_agent != speaker and other_agent.lower() in message.lower():
                       if speaker not in interaction_matrix:
                           interaction_matrix[speaker] = {}
                       if other_agent not in interaction_matrix[speaker]:
                           interaction_matrix[speaker][other_agent] = 0
                       interaction_matrix[speaker][other_agent] += 1
       
       return interaction_matrix

**Agent Influence Patterns**

.. code-block:: python

   def measure_agent_influence(experiment_results):
       """Measure how much each agent influences others."""
       
       phase1_preferences = extract_phase1_preferences(experiment_results)
       phase2_votes = extract_phase2_votes(experiment_results) 
       final_consensus = experiment_results['phase2_results']['voting_results']['chosen_principle']
       
       influence_scores = {}
       for agent_name in phase1_preferences:
           initial_preference = phase1_preferences[agent_name]
           
           # Agent gets influence points if others switch to their preference
           if initial_preference == final_consensus:
               influence_scores[agent_name] = calculate_switching_influence(
                   agent_name, initial_preference, phase1_preferences, final_consensus
               )
       
       return influence_scores

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

**Efficient Agent Configuration**

.. code-block:: python

   # Fast experiment configuration
   fast_agents = [
       AgentConfiguration(
           name=f"FastAgent{i}",
           personality="Concise and decisive",
           model="gpt-4.1-mini",  # Fastest OpenAI model
           temperature=0.0,  # No randomness for speed
           memory_character_limit=30000,  # Smaller memory
           reasoning_enabled=False  # Skip internal reasoning
       )
       for i in range(3)
   ]

**Memory-Optimized Agents**

.. code-block:: python

   # Memory-efficient agents for large-scale studies
   memory_optimized_agents = [
       AgentConfiguration(
           name=f"EfficientAgent{i}",
           personality="Focused and direct",
           model="gemini-2.5-flash",  # Fast OpenRouter model
           memory_character_limit=20000,  # Minimal memory
           reasoning_enabled=True
       )
       for i in range(5)
   ]

Error Handling and Recovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Agent-Level Error Recovery**

.. code-block:: python

   from utils.error_handling import AgentError, ErrorCategory
   
   class RobustParticipantAgent(ParticipantAgent):
       """Participant agent with enhanced error recovery."""
       
       async def apply_principle_with_retry(self, principle_info):
           """Apply principle with automatic retry on failures."""
           
           max_retries = 3
           for attempt in range(max_retries):
               try:
                   response = await self.apply_principle(principle_info)
                   
                   # Validate response completeness
                   if self.validate_response_completeness(response):
                       return response
                   else:
                       raise AgentError(
                           "Incomplete response",
                           ErrorCategory.VALIDATION_ERROR
                       )
                       
               except AgentError as e:
                   if attempt == max_retries - 1:
                       # Final attempt failed
                       raise e
                   
                   # Adjust strategy for retry
                   await self.adjust_for_retry(e.category, attempt)
                   
               except Exception as e:
                   # Unexpected error
                   await self.handle_unexpected_error(e, attempt)

Testing and Validation
----------------------

Agent Testing Framework
~~~~~~~~~~~~~~~~~~~~~~~

**Unit Testing Agents**

.. code-block:: python

   import pytest
   from experiment_agents import create_participant_agent
   
   @pytest.fixture
   async def test_agent():
       """Create agent for testing."""
       config = AgentConfiguration(
           name="TestAgent",
           personality="Test personality",
           model="gpt-4.1-mini",
           temperature=0.0
       )
       return create_participant_agent(config)
   
   @pytest.mark.asyncio
   async def test_principle_application(test_agent):
       """Test agent's principle application capability."""
       
       principle_info = create_test_principle_info()
       response = await test_agent.apply_principle(principle_info)
       
       assert response.chosen_principle is not None
       assert response.reasoning is not None
       assert len(response.reasoning) > 50  # Meaningful reasoning
       assert response.confidence_level in ["low", "medium", "high"]

**Integration Testing**

.. code-block:: python

   @pytest.mark.asyncio
   async def test_agent_memory_consistency():
       """Test that agent memory remains consistent across operations."""
       
       agent = create_test_agent()
       initial_memory = agent.get_current_memory()
       
       # Perform several operations
       await agent.apply_principle(principle1)
       await agent.update_memory("step1", "input1", "output1")
       
       await agent.apply_principle(principle2) 
       await agent.update_memory("step2", "input2", "output2")
       
       final_memory = agent.get_current_memory()
       
       # Memory should have grown and contain both steps
       assert len(final_memory) > len(initial_memory)
       assert "step1" in final_memory
       assert "step2" in final_memory

See Also
--------

- :doc:`../user-guide/custom-agents` - Complete guide to creating custom agents
- :doc:`core` - Core system components that agents interact with
- :doc:`models` - Data models used in agent communications
- :doc:`../user-guide/running-experiments` - How to run experiments with different agent configurations
- :doc:`../architecture/system-overview` - Overall system architecture and agent roles