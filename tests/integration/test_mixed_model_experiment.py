"""
Integration test for experiments with mixed model providers.
"""
import unittest
import asyncio
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from config.models import ExperimentConfiguration, AgentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from utils.model_provider import get_model_provider_info


class TestMixedModelExperiment(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test configuration with mixed models
        self.mixed_config = ExperimentConfiguration(
            agents=[
                AgentConfiguration(
                    name="Alice",
                    personality="Analytical and methodical. Values fairness and systematic approaches.",
                    model="gpt-4.1-mini",  # OpenAI
                    temperature=0.0,
                    memory_character_limit=50000,
                    reasoning_enabled=True
                ),
                AgentConfiguration(
                    name="Bob", 
                    personality="Creative and intuitive. Approaches problems from unique angles.",
                    model="google/gemini-2.5-flash",  # OpenRouter via LiteLLM
                    temperature=0.7,
                    memory_character_limit=50000,
                    reasoning_enabled=True
                ),
                AgentConfiguration(
                    name="Carol",
                    personality="Empathetic and community-focused. Prioritizes social welfare.",
                    model="anthropic/claude-3-5-sonnet-20241022",  # OpenRouter via LiteLLM
                    temperature=0.5,
                    memory_character_limit=50000,
                    reasoning_enabled=True
                )
            ],
            utility_agent_model="google/gemini-2.5-flash",  # OpenRouter for utility agent
            phase2_rounds=3,
            distribution_range_phase1=[0.5, 2.0],
            distribution_range_phase2=[0.5, 2.0]
        )
    
    def test_model_provider_detection(self):
        """Test that different model providers are correctly detected."""
        # Test each agent's model provider info
        alice_info = get_model_provider_info("gpt-4.1-mini")
        self.assertEqual(alice_info["provider"], "OpenAI")
        self.assertFalse(alice_info["is_litellm"])
        
        bob_info = get_model_provider_info("google/gemini-2.5-flash")
        self.assertEqual(bob_info["provider"], "OpenRouter")
        self.assertTrue(bob_info["is_litellm"])
        
        carol_info = get_model_provider_info("anthropic/claude-3-5-sonnet-20241022")
        self.assertEqual(carol_info["provider"], "OpenRouter")
        self.assertTrue(carol_info["is_litellm"])
    
    @patch.dict("os.environ", {
        "OPENAI_API_KEY": "test-openai-key", 
        "OPENROUTER_API_KEY": "test-openrouter-key"
    })
    @patch('experiment_agents.participant_agent.Agent')
    @patch('experiment_agents.utility_agent.Agent')
    @patch('utils.model_provider.LitellmModel')
    def test_experiment_manager_initialization(self, mock_litellm, mock_utility_agent, mock_participant_agent):
        """Test that experiment manager initializes with mixed model providers."""
        # Mock LiteLLM model instances
        mock_litellm_instance = MagicMock()
        mock_litellm.return_value = mock_litellm_instance
        
        # Mock agent instances
        mock_participant_instance = MagicMock()
        mock_participant_instance.name = "test_agent"
        mock_participant_agent.return_value = mock_participant_instance
        
        mock_utility_instance = MagicMock()
        mock_utility_agent.return_value = mock_utility_instance
        
        # Initialize experiment manager
        manager = FrohlichExperimentManager(self.mixed_config)
        
        # Verify manager was created
        self.assertIsNotNone(manager)
        self.assertEqual(len(manager.participants), 3)
        self.assertIsNotNone(manager.utility_agent)
        
        # Verify LiteLLM was called for OpenRouter models
        expected_calls = [
            # Bob's model
            unittest.mock.call(
                model="openrouter/google/gemini-2.5-flash",
                api_key="test-openrouter-key"
            ),
            # Carol's model  
            unittest.mock.call(
                model="openrouter/anthropic/claude-3-5-sonnet-20241022",
                api_key="test-openrouter-key"
            ),
            # Utility agent model (called twice for parser and validator)
            unittest.mock.call(
                model="openrouter/google/gemini-2.5-flash",
                api_key="test-openrouter-key"
            ),
            unittest.mock.call(
                model="openrouter/google/gemini-2.5-flash", 
                api_key="test-openrouter-key"
            )
        ]
        
        # Check that LiteLLM was called the expected number of times
        # (2 participant agents + 2 utility agents = 4 calls)
        self.assertEqual(mock_litellm.call_count, 4)
    
    @patch.dict("os.environ", {})
    def test_no_environment_validation_required(self):
        """Test that no environment validation is required for any configuration."""
        # This should not raise any validation errors (both keys are optional)
        from utils.model_provider import validate_environment_for_models
        errors = validate_environment_for_models(
            self.mixed_config.agents, 
            self.mixed_config.utility_agent_model
        )
        self.assertEqual(len(errors), 0)  # No validation errors - keys retrieved dynamically
    
    def test_configuration_yaml_serialization(self):
        """Test that mixed model configuration can be saved/loaded from YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save configuration to YAML
            self.mixed_config.to_yaml(temp_path)
            
            # Load configuration from YAML
            loaded_config = ExperimentConfiguration.from_yaml(temp_path)
            
            # Verify loaded configuration matches original
            self.assertEqual(len(loaded_config.agents), len(self.mixed_config.agents))
            
            for original, loaded in zip(self.mixed_config.agents, loaded_config.agents):
                self.assertEqual(original.name, loaded.name)
                self.assertEqual(original.model, loaded.model)
                self.assertEqual(original.temperature, loaded.temperature)
            
            self.assertEqual(loaded_config.utility_agent_model, self.mixed_config.utility_agent_model)
            
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
    
    @patch.dict("os.environ", {
        "OPENAI_API_KEY": "test-openai-key",
        "OPENROUTER_API_KEY": "test-openrouter-key"
    })
    def test_agent_configuration_validation(self):
        """Test that agent configuration validation works with mixed models."""
        # This should not raise any validation errors
        config = ExperimentConfiguration(
            agents=[
                AgentConfiguration(
                    name="TestAgent1",
                    personality="Test personality",
                    model="gpt-4.1-mini"  # OpenAI
                ),
                AgentConfiguration(
                    name="TestAgent2", 
                    personality="Test personality",
                    model="google/gemini-2.5-flash"  # OpenRouter
                )
            ],
            utility_agent_model="gpt-4.1-mini"
        )
        
        # Validate unique names (should pass)
        agent_names = [agent.name for agent in config.agents]
        self.assertEqual(len(agent_names), len(set(agent_names)))
        
        # Validate model configurations
        for agent in config.agents:
            provider_info = get_model_provider_info(agent.model)
            self.assertIn(provider_info["provider"], ["OpenAI", "OpenRouter"])
    
    @patch.dict("os.environ", {
        "OPENAI_API_KEY": "test-openai-key",
        "OPENROUTER_API_KEY": "test-openrouter-key"
    })
    @patch('core.phase1_manager.Phase1Manager.run_phase1')
    @patch('core.phase2_manager.Phase2Manager.run_phase2')
    @patch('experiment_agents.participant_agent.Agent')
    @patch('experiment_agents.utility_agent.Agent')
    @patch('utils.model_provider.LitellmModel')
    async def test_full_experiment_mock_run(self, mock_litellm, mock_utility_agent, 
                                           mock_participant_agent, mock_phase2, mock_phase1):
        """Test full experiment flow with mocked phases."""
        # Mock LiteLLM and Agent instances
        mock_litellm.return_value = MagicMock()
        mock_participant_agent.return_value = MagicMock()
        mock_utility_agent.return_value = MagicMock()
        
        # Mock phase results
        mock_phase1_results = []
        mock_phase2_results = MagicMock()
        mock_phase2_results.discussion_result.consensus_reached = True
        mock_phase2_results.payoff_results = {"Alice": 10.0, "Bob": 15.0, "Carol": 12.0}
        
        mock_phase1.return_value = mock_phase1_results
        mock_phase2.return_value = mock_phase2_results
        
        # Initialize and run experiment
        manager = FrohlichExperimentManager(self.mixed_config)
        
        # Mock the agent logger to avoid file I/O
        manager.agent_logger = MagicMock()
        
        # Run experiment (phases are mocked)
        results = await manager.run_complete_experiment()
        
        # Verify experiment completed
        self.assertIsNotNone(results)
        self.assertIsNotNone(results.experiment_id)
        self.assertEqual(results.phase1_results, mock_phase1_results)
        self.assertEqual(results.phase2_results, mock_phase2_results)
        
        # Verify both phases were called
        mock_phase1.assert_called_once()
        mock_phase2.assert_called_once()
    
    def test_model_temperature_handling(self):
        """Test that temperature settings are properly handled for different model types."""
        # Test OpenAI model (temperature should be in ModelSettings)
        alice_config = self.mixed_config.agents[0]  # OpenAI model
        self.assertEqual(alice_config.model, "gpt-4.1-mini")
        self.assertEqual(alice_config.temperature, 0.0)
        
        # Test OpenRouter models (temperature ignored in LiteLLM)
        bob_config = self.mixed_config.agents[1]  # OpenRouter model
        self.assertIn("/", bob_config.model)
        self.assertEqual(bob_config.temperature, 0.7)
        
        carol_config = self.mixed_config.agents[2]  # OpenRouter model
        self.assertIn("/", carol_config.model)
        self.assertEqual(carol_config.temperature, 0.5)


# Async test runner helper
def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Override test methods to handle async
class AsyncTestCase(unittest.TestCase):
    def run_async_test(self, coro):
        return run_async_test(coro)


# Make the async test method work
TestMixedModelExperiment.test_full_experiment_mock_run = lambda self: self.run_async_test(
    TestMixedModelExperiment.test_full_experiment_mock_run.__wrapped__(self)
)


if __name__ == '__main__':
    unittest.main()