"""
Unit tests for experiment reproducibility functionality.
"""
import unittest
import tempfile
import yaml
from unittest.mock import patch

from utils.seed_manager import SeedManager
from config import ExperimentConfiguration


class TestSeedManager(unittest.TestCase):
    """Test the SeedManager utility class."""
    
    def test_set_experiment_seed_valid(self):
        """Test setting a valid seed."""
        # Should not raise any exception
        SeedManager.set_experiment_seed(12345)
        
        # Verify random operations are seeded
        import random
        first_value = random.random()
        
        # Reset with same seed
        SeedManager.set_experiment_seed(12345)
        second_value = random.random()
        
        self.assertEqual(first_value, second_value, "Same seed should produce same random values")
    
    def test_set_experiment_seed_invalid(self):
        """Test setting invalid seeds raises ValueError."""
        with self.assertRaises(ValueError):
            SeedManager.set_experiment_seed(-1)
        
        with self.assertRaises(ValueError):
            SeedManager.set_experiment_seed("not_an_int")
        
        with self.assertRaises(ValueError):
            SeedManager.set_experiment_seed(2**31)  # Too large (our limit)
    
    def test_validate_seed(self):
        """Test seed validation function."""
        self.assertTrue(SeedManager.validate_seed(0))
        self.assertTrue(SeedManager.validate_seed(12345))
        self.assertTrue(SeedManager.validate_seed(2**31 - 1))
        
        self.assertFalse(SeedManager.validate_seed(-1))
        self.assertFalse(SeedManager.validate_seed(2**31))
        self.assertFalse(SeedManager.validate_seed("invalid"))
        self.assertFalse(SeedManager.validate_seed(3.14))
    
    def test_generate_seed_from_config_deterministic(self):
        """Test that same configuration generates same seed."""
        # Create test configuration
        config_data = {
            "language": "English",
            "agents": [
                {
                    "name": "Agent_1",
                    "personality": "Test personality A",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.7,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": True
                },
                {
                    "name": "Agent_2",
                    "personality": "Test personality B",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.5,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": False
                }
            ],
            "utility_agent_model": "gpt-4.1-mini",
            "phase2_rounds": 10
        }
        
        config1 = ExperimentConfiguration(**config_data)
        config2 = ExperimentConfiguration(**config_data)
        
        seed1 = SeedManager.generate_seed_from_config(config1)
        seed2 = SeedManager.generate_seed_from_config(config2)
        
        self.assertEqual(seed1, seed2, "Same configuration should generate same seed")
        self.assertIsInstance(seed1, int)
        self.assertTrue(0 <= seed1 < 2**31)
    
    def test_generate_seed_from_config_different(self):
        """Test that different configurations generate different seeds."""
        config_data1 = {
            "language": "English",
            "agents": [
                {
                    "name": "Agent_1",
                    "personality": "Test personality A",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.7,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": True
                },
                {
                    "name": "Agent_2",
                    "personality": "Test personality B",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.5,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": False
                }
            ],
            "utility_agent_model": "gpt-4.1-mini",
            "phase2_rounds": 10
        }
        
        config_data2 = config_data1.copy()
        config_data2["phase2_rounds"] = 20  # Different parameter
        
        config1 = ExperimentConfiguration(**config_data1)
        config2 = ExperimentConfiguration(**config_data2)
        
        seed1 = SeedManager.generate_seed_from_config(config1)
        seed2 = SeedManager.generate_seed_from_config(config2)
        
        self.assertNotEqual(seed1, seed2, "Different configurations should generate different seeds")


class TestExperimentConfiguration(unittest.TestCase):
    """Test ExperimentConfiguration seed functionality."""
    
    def test_get_effective_seed_explicit(self):
        """Test get_effective_seed with explicit seed."""
        config_data = {
            "language": "English",
            "agents": [
                {
                    "name": "Agent_1",
                    "personality": "Test personality A",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.7,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": True
                },
                {
                    "name": "Agent_2",
                    "personality": "Test personality B",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.5,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": False
                }
            ],
            "utility_agent_model": "gpt-4.1-mini",
            "phase2_rounds": 10,
            "seed": 42
        }
        
        config = ExperimentConfiguration(**config_data)
        self.assertEqual(config.get_effective_seed(), 42)
    
    def test_get_effective_seed_generated(self):
        """Test get_effective_seed with generated seed."""
        config_data = {
            "language": "English",
            "agents": [
                {
                    "name": "Agent_1",
                    "personality": "Test personality A",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.7,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": True
                },
                {
                    "name": "Agent_2",
                    "personality": "Test personality B",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.5,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": False
                }
            ],
            "utility_agent_model": "gpt-4.1-mini",
            "phase2_rounds": 10
            # No explicit seed
        }
        
        config = ExperimentConfiguration(**config_data)
        seed = config.get_effective_seed()
        
        self.assertIsInstance(seed, int)
        self.assertTrue(0 <= seed < 2**31)
        
        # Should be consistent
        seed2 = config.get_effective_seed()
        self.assertEqual(seed, seed2)
    
    def test_seed_validation_in_config(self):
        """Test that invalid seeds are rejected in configuration."""
        config_data = {
            "language": "English",
            "agents": [
                {
                    "name": "Agent_1",
                    "personality": "Test personality A",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.7,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": True
                },
                {
                    "name": "Agent_2",
                    "personality": "Test personality B",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.5,
                    "memory_character_limit": 50000,
                    "reasoning_enabled": False
                }
            ],
            "utility_agent_model": "gpt-4.1-mini",
            "phase2_rounds": 10,
            "seed": -1  # Invalid seed
        }
        
        with self.assertRaises(Exception):  # Pydantic should raise validation error
            ExperimentConfiguration(**config_data)
    
    def test_from_yaml_with_seed(self):
        """Test loading configuration with seed from YAML."""
        config_yaml = """
language: "English"
seed: 12345
agents:
  - name: "Agent_1"
    personality: "Test personality A"
    model: "gpt-4.1-mini"
    temperature: 0.7
    memory_character_limit: 50000
    reasoning_enabled: true
  - name: "Agent_2"
    personality: "Test personality B"
    model: "gpt-4.1-mini"
    temperature: 0.5
    memory_character_limit: 50000
    reasoning_enabled: false
utility_agent_model: "gpt-4.1-mini"
phase2_rounds: 10
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            f.flush()
            
            config = ExperimentConfiguration.from_yaml(f.name)
            self.assertEqual(config.seed, 12345)
            self.assertEqual(config.get_effective_seed(), 12345)
    
    def test_from_yaml_without_seed(self):
        """Test loading configuration without seed from YAML."""
        config_yaml = """
language: "English"
agents:
  - name: "Agent_1"
    personality: "Test personality A"
    model: "gpt-4.1-mini"
    temperature: 0.7
    memory_character_limit: 50000
    reasoning_enabled: true
  - name: "Agent_2"
    personality: "Test personality B"
    model: "gpt-4.1-mini"
    temperature: 0.5
    memory_character_limit: 50000
    reasoning_enabled: false
utility_agent_model: "gpt-4.1-mini"
phase2_rounds: 10
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            f.flush()
            
            config = ExperimentConfiguration.from_yaml(f.name)
            self.assertIsNone(config.seed)
            
            # Should still generate a seed
            effective_seed = config.get_effective_seed()
            self.assertIsInstance(effective_seed, int)
            self.assertTrue(0 <= effective_seed < 2**31)


if __name__ == '__main__':
    unittest.main()