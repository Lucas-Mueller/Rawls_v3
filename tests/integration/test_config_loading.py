"""
Integration tests for configuration loading and validation.
"""
import unittest
import tempfile
import os
from pathlib import Path

from config import ExperimentConfiguration


class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for experiment configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config_content = """
agents:
  - name: "TestAgent1"
    personality: "Analytical and methodical."
    model: "gpt-4o-mini"
    temperature: 0.7
    memory_character_limit: 50000
    
  - name: "TestAgent2"
    personality: "Pragmatic and results-oriented."
    model: "gpt-4o-mini"
    temperature: 0.8
    memory_character_limit: 40000

phase2_rounds: 5
distribution_range_phase1: [0.8, 1.5]
distribution_range_phase2: [0.6, 1.8]
"""
    
    def test_config_loading_from_yaml(self):
        """Test loading configuration from YAML file."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(self.test_config_content)
            temp_config_path = f.name
        
        try:
            # Load configuration
            config = ExperimentConfiguration.from_yaml(temp_config_path)
            
            # Verify loaded values
            self.assertEqual(len(config.agents), 2)
            self.assertEqual(config.agents[0].name, "TestAgent1")
            self.assertEqual(config.agents[1].name, "TestAgent2")
            self.assertEqual(config.phase2_rounds, 5)
            self.assertEqual(config.distribution_range_phase1, (0.8, 1.5))
            self.assertEqual(config.distribution_range_phase2, (0.6, 1.8))
            
            # Test agent-specific settings
            self.assertEqual(config.agents[0].memory_character_limit, 50000)
            self.assertEqual(config.agents[1].memory_character_limit, 40000)
            
        finally:
            # Clean up
            os.unlink(temp_config_path)
    
    def test_config_validation_errors(self):
        """Test configuration validation catches errors."""
        # Test duplicate agent names
        invalid_config = """
agents:
  - name: "Agent1"
    personality: "Test personality"
    model: "gpt-4o-mini"
    temperature: 0.7
    memory_character_limit: 50000
    
  - name: "Agent1"  # Duplicate name
    personality: "Another personality"
    model: "gpt-4o-mini"
    temperature: 0.8
    memory_character_limit: 50000

phase2_rounds: 5
distribution_range_phase1: [0.8, 1.5]
distribution_range_phase2: [0.6, 1.8]
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_config)
            temp_config_path = f.name
        
        try:
            with self.assertRaises(ValueError):  # Should raise validation error
                ExperimentConfiguration.from_yaml(temp_config_path)
        finally:
            os.unlink(temp_config_path)
    
    def test_config_missing_file(self):
        """Test handling of missing configuration file."""
        with self.assertRaises(FileNotFoundError):
            ExperimentConfiguration.from_yaml("nonexistent_config.yaml")
    
    def test_config_to_yaml_roundtrip(self):
        """Test saving and loading configuration maintains integrity."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(self.test_config_content)
            temp_config_path = f.name
        
        try:
            # Load and save configuration
            original_config = ExperimentConfiguration.from_yaml(temp_config_path)
            
            # Save to new file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f2:
                saved_config_path = f2.name
            
            original_config.to_yaml(saved_config_path)
            
            # Load the saved configuration
            loaded_config = ExperimentConfiguration.from_yaml(saved_config_path)
            
            # Compare configurations
            self.assertEqual(len(original_config.agents), len(loaded_config.agents))
            self.assertEqual(original_config.phase2_rounds, loaded_config.phase2_rounds)
            self.assertEqual(original_config.distribution_range_phase1, loaded_config.distribution_range_phase1)
            
            # Compare first agent details
            orig_agent = original_config.agents[0]
            loaded_agent = loaded_config.agents[0]
            self.assertEqual(orig_agent.name, loaded_agent.name)
            self.assertEqual(orig_agent.personality, loaded_agent.personality)
            self.assertEqual(orig_agent.temperature, loaded_agent.temperature)
            
            os.unlink(saved_config_path)
            
        finally:
            os.unlink(temp_config_path)
    
    def test_default_config_exists_and_loads(self):
        """Test that the default configuration file exists and loads correctly."""
        default_config_path = Path(__file__).parent.parent.parent / "config" / "default_config.yaml"
        
        # Check file exists
        self.assertTrue(default_config_path.exists(), f"Default config not found at {default_config_path}")
        
        # Load default configuration
        config = ExperimentConfiguration.from_yaml(str(default_config_path))
        
        # Basic validation
        self.assertGreater(len(config.agents), 0, "Default config should have at least one agent")
        self.assertGreater(config.phase2_rounds, 0, "Phase 2 rounds should be positive")
        
        # Validate each agent has required fields
        for agent in config.agents:
            self.assertIsNotNone(agent.name)
            self.assertIsNotNone(agent.personality)
            self.assertIsNotNone(agent.model)
            self.assertGreater(agent.memory_character_limit, 0)


if __name__ == '__main__':
    unittest.main()