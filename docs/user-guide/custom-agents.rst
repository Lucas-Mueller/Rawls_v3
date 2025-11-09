Creating Custom Agents
======================

This advanced tutorial shows you how to extend the Frohlich Experiment system with custom agent types, specialized behaviors, and novel experimental paradigms.

Understanding the Agent Architecture
------------------------------------

Base Agent Structure
~~~~~~~~~~~~~~~~~~~

The system uses two main agent types:

.. code-block:: python

   from experiment_agents.participant_agent import ParticipantAgent
   from experiment_agents.utility_agent import UtilityAgent

**ParticipantAgent**: The core experimental subjects that engage in justice reasoning
**UtilityAgent**: Specialized agents for response parsing, validation, and system operations

Agent Lifecycle
~~~~~~~~~~~~~~~

1. **Initialization**: Agent creation with model provider detection
2. **Memory Setup**: Agent-managed memory system initialization
3. **Phase 1**: Individual principle familiarization (parallel)
4. **Phase 2**: Group discussion participation (sequential)
5. **Memory Management**: Continuous self-directed memory updates

Creating Custom Participant Agents
-----------------------------------

Basic Custom Agent
~~~~~~~~~~~~~~~~~

Create a specialized participant agent with custom behavior:

.. code-block:: python

   # custom_agents/specialized_participant.py
   from experiment_agents.participant_agent import ParticipantAgent
   from utils.memory_manager import MemoryManager
   import logging

   class SpecializedParticipantAgent(ParticipantAgent):
       """Custom participant agent with specialized reasoning patterns."""
       
       def __init__(self, name: str, personality: str, model: str, 
                    temperature: float, memory_character_limit: int,
                    reasoning_enabled: bool, specialty: str = None):
           super().__init__(name, personality, model, temperature, 
                          memory_character_limit, reasoning_enabled)
           self.specialty = specialty
           self.custom_metrics = {}
           
       async def process_principle_application(self, principle: str, 
                                             distributions: list, 
                                             context: dict) -> dict:
           """Custom principle application with specialty-specific reasoning."""
           
           # Add specialty-specific context to memory
           specialty_context = self._generate_specialty_context(principle)
           
           # Call parent method with enhanced context
           enhanced_context = {**context, "specialty": specialty_context}
           result = await super().process_principle_application(
               principle, distributions, enhanced_context
           )
           
           # Track custom metrics
           self._update_custom_metrics(principle, result)
           
           return result
           
       def _generate_specialty_context(self, principle: str) -> str:
           """Generate specialty-specific reasoning context."""
           specialty_prompts = {
               "economist": f"Apply economic theory to analyze {principle}",
               "ethicist": f"Consider moral implications of {principle}",
               "activist": f"Evaluate {principle} from social justice perspective"
           }
           return specialty_prompts.get(self.specialty, "")
           
       def _update_custom_metrics(self, principle: str, result: dict):
           """Track specialty-specific decision patterns."""
           if principle not in self.custom_metrics:
               self.custom_metrics[principle] = []
           
           self.custom_metrics[principle].append({
               "choice": result.get("chosen_principle"),
               "confidence": result.get("confidence_level"),
               "reasoning_length": len(result.get("reasoning", ""))
           })

Agent Factory Pattern
~~~~~~~~~~~~~~~~~~~~~

Create a factory for systematic custom agent creation:

.. code-block:: python

   # custom_agents/agent_factory.py
   from typing import List, Dict, Any
   from custom_agents.specialized_participant import SpecializedParticipantAgent

   class CustomAgentFactory:
       """Factory for creating specialized agent configurations."""
       
       SPECIALIST_PERSONALITIES = {
           "economist": {
               "personality": "You are an economics professor focused on efficiency, market mechanisms, and utility maximization. You analyze distribution problems through economic theory.",
               "specialty": "economist",
               "memory_limit": 60000,
               "reasoning_enabled": True
           },
           "ethicist": {
               "personality": "You are a moral philosopher who prioritizes fairness, rights, and ethical principles. You consider the moral implications of distribution decisions.",
               "specialty": "ethicist", 
               "memory_limit": 70000,
               "reasoning_enabled": True
           },
           "activist": {
               "personality": "You are a social justice advocate focused on reducing inequality and helping disadvantaged populations. You prioritize systemic change.",
               "specialty": "activist",
               "memory_limit": 65000,
               "reasoning_enabled": True
           }
       }
       
       @classmethod
       async def create_specialist_group(cls, model: str = "gpt-4.1-mini", 
                                       temperature: float = 0.3) -> List[SpecializedParticipantAgent]:
           """Create a balanced group of specialist agents."""
           agents = []
           
           for specialty, config in cls.SPECIALIST_PERSONALITIES.items():
               agent = SpecializedParticipantAgent(
                   name=f"{specialty.title()}_Agent",
                   personality=config["personality"],
                   model=model,
                   temperature=temperature,
                   memory_character_limit=config["memory_limit"],
                   reasoning_enabled=config["reasoning_enabled"],
                   specialty=config["specialty"]
               )
               
               await agent.async_init()
               agents.append(agent)
               
           return agents

Advanced Agent Behaviors
------------------------

Memory-Enhanced Agents
~~~~~~~~~~~~~~~~~~~~~

Create agents with sophisticated memory management:

.. code-block:: python

   # custom_agents/memory_enhanced_agent.py
   class MemoryEnhancedAgent(ParticipantAgent):
       """Agent with advanced memory categorization and retrieval."""
       
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.memory_categories = {
               "principles": [],
               "social_contexts": [],
               "personal_values": [],
               "group_dynamics": []
           }
           
       async def update_memory_with_categorization(self, experience: str, 
                                                 category: str):
           """Update memory with categorical organization."""
           if category in self.memory_categories:
               self.memory_categories[category].append(experience)
           
           # Create structured memory update
           categorized_memory = self._format_categorized_memory()
           await self.memory_manager.prompt_agent_for_memory_update(
               self.agent, categorized_memory, self.memory_character_limit
           )
           
       def _format_categorized_memory(self) -> str:
           """Format memory with category structure."""
           formatted_sections = []
           
           for category, items in self.memory_categories.items():
               if items:
                   section = f"\\n{category.upper()}:\\n"
                   section += "\\n".join(f"- {item}" for item in items[-5:])  # Keep recent items
                   formatted_sections.append(section)
                   
           return "\\n".join(formatted_sections)

Learning Agents
~~~~~~~~~~~~~~

Implement agents that adapt their behavior over time:

.. code-block:: python

   # custom_agents/learning_agent.py
   class LearningAgent(ParticipantAgent):
       """Agent that learns from experience and adapts behavior."""
       
       def __init__(self, *args, learning_rate: float = 0.1, **kwargs):
           super().__init__(*args, **kwargs)
           self.learning_rate = learning_rate
           self.decision_history = []
           self.outcome_feedback = []
           self.adapted_personality = self.personality
           
       async def make_decision_with_learning(self, context: dict) -> dict:
           """Make decisions incorporating learning from past experiences."""
           
           # Incorporate learning into decision context
           learning_context = self._generate_learning_context()
           enhanced_context = {**context, "learning": learning_context}
           
           # Make decision
           decision = await self._make_enhanced_decision(enhanced_context)
           
           # Record decision for learning
           self.decision_history.append(decision)
           
           return decision
           
       def _generate_learning_context(self) -> str:
           """Generate context based on learning from past decisions."""
           if not self.decision_history:
               return "This is your first decision in this type of situation."
           
           # Analyze past patterns
           recent_decisions = self.decision_history[-3:]  # Last 3 decisions
           pattern_analysis = self._analyze_decision_patterns(recent_decisions)
           
           return f"Based on your recent experience: {pattern_analysis}"
           
       def _analyze_decision_patterns(self, decisions: list) -> str:
           """Analyze patterns in recent decisions."""
           if not decisions:
               return ""
           
           # Simple pattern analysis
           principle_choices = [d.get("chosen_principle") for d in decisions]
           most_common = max(set(principle_choices), key=principle_choices.count)
           
           return f"You have recently favored {most_common}. Consider if this pattern serves your values."

Specialized Utility Agents
--------------------------

Custom Validation Agents
~~~~~~~~~~~~~~~~~~~~~~~~

Create specialized utility agents for domain-specific validation:

.. code-block:: python

   # custom_agents/specialized_utility.py
   from experiment_agents.utility_agent import UtilityAgent
   
   class EconomicValidationAgent(UtilityAgent):
       """Utility agent specialized in economic reasoning validation."""
       
       def __init__(self, model: str, temperature: float = 0.0):
           super().__init__(model, temperature)
           self.validation_criteria = {
               "economic_reasoning": ["efficiency", "utility", "optimization"],
               "logical_consistency": ["coherent", "consistent", "logical"],
               "quantitative_support": ["numbers", "calculation", "measurement"]
           }
           
       async def validate_economic_reasoning(self, response: dict) -> dict:
           """Validate response for economic reasoning quality."""
           
           reasoning_text = response.get("reasoning", "")
           validation_results = {}
           
           for criterion, keywords in self.validation_criteria.items():
               score = sum(1 for keyword in keywords if keyword in reasoning_text.lower())
               validation_results[criterion] = {
                   "score": score,
                   "max_score": len(keywords),
                   "meets_threshold": score >= len(keywords) // 2
               }
           
           # Overall validation
           overall_valid = all(result["meets_threshold"] for result in validation_results.values())
           
           return {
               "economic_validation": validation_results,
               "overall_valid": overall_valid,
               "suggestions": self._generate_improvement_suggestions(validation_results)
           }
           
       def _generate_improvement_suggestions(self, results: dict) -> list:
           """Generate suggestions for improving economic reasoning."""
           suggestions = []
           
           for criterion, result in results.items():
               if not result["meets_threshold"]:
                   suggestions.append(f"Improve {criterion}: provide more specific economic analysis")
                   
           return suggestions

Integration with Experiment Manager
-----------------------------------

Custom Experiment Manager
~~~~~~~~~~~~~~~~~~~~~~~~~

Extend the main experiment manager to use custom agents:

.. code-block:: python

   # custom_experiments/custom_experiment_manager.py
   from core.experiment_manager import FrohlichExperimentManager
   from custom_agents.agent_factory import CustomAgentFactory
   from custom_agents.specialized_utility import EconomicValidationAgent

   class CustomExperimentManager(FrohlichExperimentManager):
       """Experiment manager with custom agent support."""
       
       def __init__(self, config, use_custom_agents: bool = False):
           super().__init__(config)
           self.use_custom_agents = use_custom_agents
           
       async def _create_participants(self):
           """Create participants using custom agent factory if specified."""
           if self.use_custom_agents:
               return await CustomAgentFactory.create_specialist_group(
                   model=self.config.agents[0].model,
                   temperature=0.3
               )
           else:
               return await super()._create_participants()
               
       async def _create_utility_agent(self):
           """Create specialized utility agent if configured."""
           if hasattr(self.config, 'use_economic_validation') and self.config.use_economic_validation:
               return EconomicValidationAgent(
                   model=self.config.utility_agent_model,
                   temperature=self.config.utility_agent_temperature
               )
           else:
               return await super()._create_utility_agent()

Configuration for Custom Agents
-------------------------------

Extended Configuration Schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extend the configuration to support custom agents:

.. code-block:: yaml

   # custom_config.yaml
   language: "english"
   
   # Custom agent configuration
   custom_agents:
     enabled: true
     agent_type: "specialist"
     specialist_config:
       include_economist: true
       include_ethicist: true  
       include_activist: true
       base_model: "gpt-4.1-mini"
       base_temperature: 0.3
   
   # Custom utility agent
   utility_agent:
     type: "economic_validation"
     model: "gpt-4.1-mini"
     temperature: 0.0
     validation_enabled: true
   
   # Extended phase configuration
   phase_config:
     phase1_custom_rounds: 5
     phase2_custom_mechanics: "learning_enabled"
     memory_sharing: false
     cross_agent_learning: true

Custom Configuration Loader
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # custom_experiments/config_loader.py
   from pydantic import BaseModel
   from typing import Optional
   from config.models import ExperimentConfiguration

   class CustomAgentConfig(BaseModel):
       enabled: bool = False
       agent_type: str = "standard"
       specialist_config: Optional[dict] = None

   class CustomUtilityConfig(BaseModel):
       type: str = "standard"
       model: str
       temperature: float = 0.0
       validation_enabled: bool = False

   class ExtendedExperimentConfiguration(ExperimentConfiguration):
       custom_agents: Optional[CustomAgentConfig] = None
       utility_agent: Optional[CustomUtilityConfig] = None
       phase_config: Optional[dict] = None

Running Custom Experiments
--------------------------

Integration Example
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # run_custom_experiment.py
   import asyncio
   from custom_experiments.custom_experiment_manager import CustomExperimentManager
   from custom_experiments.config_loader import ExtendedExperimentConfiguration

   async def run_custom_experiment():
       """Run experiment with custom agents."""
       
       # Load extended configuration
       config = ExtendedExperimentConfiguration.from_yaml("custom_config.yaml")
       
       # Create custom experiment manager
       manager = CustomExperimentManager(config, use_custom_agents=True)
       await manager.async_init()  # Required async initialization

       # Run experiment
       results = await manager.run_complete_experiment()
       
       # Process custom results
       custom_results = analyze_custom_results(results)
       
       return custom_results

   def analyze_custom_results(results):
       """Analyze results with custom metrics."""
       analysis = {
           "specialist_agreement": calculate_specialist_agreement(results),
           "learning_progression": track_learning_progression(results),
           "economic_validity": assess_economic_reasoning(results)
       }
       return analysis

   if __name__ == "__main__":
       results = asyncio.run(run_custom_experiment())
       print("Custom experiment completed with results:", results)

Testing Custom Agents
---------------------

Unit Testing Custom Agents
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/test_custom_agents.py
   import unittest
   from unittest.mock import AsyncMock, MagicMock
   from custom_agents.specialized_participant import SpecializedParticipantAgent

   class TestSpecializedParticipantAgent(unittest.TestCase):
       
       def setUp(self):
           self.agent = SpecializedParticipantAgent(
               name="TestAgent",
               personality="Test personality",
               model="gpt-4.1-mini",
               temperature=0.3,
               memory_character_limit=50000,
               reasoning_enabled=True,
               specialty="economist"
           )
           
       async def test_specialty_context_generation(self):
           """Test specialty-specific context generation."""
           context = self.agent._generate_specialty_context("maximizing average")
           self.assertIn("economic theory", context)
           
       async def test_custom_metrics_tracking(self):
           """Test custom metrics tracking functionality."""
           result = {"chosen_principle": "a", "confidence_level": "high"}
           self.agent._update_custom_metrics("principle_a", result)
           
           self.assertIn("principle_a", self.agent.custom_metrics)
           self.assertEqual(len(self.agent.custom_metrics["principle_a"]), 1)

   if __name__ == '__main__':
       unittest.main()

Integration Testing
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/test_custom_integration.py
   import unittest
   import asyncio
   from custom_experiments.custom_experiment_manager import CustomExperimentManager
   from config.models import ExperimentConfiguration

   class TestCustomIntegration(unittest.TestCase):
       
       def test_custom_agent_creation(self):
           """Test that custom agents are created correctly."""
           
           async def run_test():
               config = ExperimentConfiguration.from_yaml("test_custom_config.yaml")
               manager = CustomExperimentManager(config, use_custom_agents=True)
               
               await manager.async_init()
               
               self.assertEqual(len(manager.participants), 3)
               self.assertTrue(all(hasattr(agent, 'specialty') for agent in manager.participants))
               
           asyncio.run(run_test())

Best Practices for Custom Agents
--------------------------------

Design Principles
~~~~~~~~~~~~~~~~

1. **Inherit Don't Rewrite**: Extend existing agents rather than creating from scratch
2. **Maintain Interface Compatibility**: Keep the same method signatures for core functionality  
3. **Add Observability**: Include custom metrics and logging for analysis
4. **Test Thoroughly**: Custom agents need comprehensive testing due to complexity
5. **Document Behavior**: Clearly document what makes your custom agents different

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~

- **Memory Usage**: Custom agents may use more memory - monitor and adjust limits
- **Processing Time**: Additional logic increases execution time - profile and optimize
- **API Costs**: More complex agents may use more tokens - track and budget accordingly
- **Error Handling**: Implement robust error handling for custom functionality

Debugging Custom Agents
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Add detailed logging to custom agents
   import logging

   class DebuggableCustomAgent(ParticipantAgent):
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.logger = logging.getLogger(f"CustomAgent.{self.name}")
           
       async def process_decision(self, context):
           self.logger.info(f"Processing decision with context: {context}")
           result = await super().process_decision(context)
           self.logger.info(f"Decision result: {result}")
           return result

See Also
--------

* :doc:`running-experiments` - Execute experiments with your custom agents
* :doc:`../architecture/system-overview` - Understand agent architecture and lifecycle
* :doc:`../architecture/services-architecture` - Learn about the services-based Phase 2 system
* :doc:`../api/agents` - Complete API reference for agent classes
* :doc:`../contributing/guidelines` - Development best practices for contributions

For more advanced customization examples and troubleshooting, see the ``custom_agents/`` directory in the repository and refer to :doc:`../architecture/system-overview` for detailed system internals.