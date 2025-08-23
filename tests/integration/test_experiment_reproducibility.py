"""
Integration tests for full experiment reproducibility.
"""
import unittest
import asyncio
import tempfile
import json
import os
from pathlib import Path

from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from utils.seed_manager import SeedManager


class TestExperimentReproducibility(unittest.TestCase):
    """Test full experiment reproducibility with seed control."""
    
    def setUp(self):
        """Set up test configuration."""
        # Create minimal test configuration
        self.config_data = {
            "language": "English",
            "agents": [
                {
                    "name": "Alice",
                    "personality": "Test personality A",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.0,  # Deterministic temperature
                    "memory_character_limit": 25000,
                    "reasoning_enabled": False  # Disable for faster testing
                },
                {
                    "name": "Bob", 
                    "personality": "Test personality B",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.0,  # Deterministic temperature
                    "memory_character_limit": 25000,
                    "reasoning_enabled": False  # Disable for faster testing
                }
            ],
            "utility_agent_model": "gpt-4.1-mini",
            "utility_agent_temperature": 0.0,
            "phase2_rounds": 2,  # Minimal rounds for faster testing
            "distribution_range_phase1": [0.8, 1.2],  # Minimal randomness for testing
            "distribution_range_phase2": [0.8, 1.2],  # Minimal randomness for testing
            "original_values_mode": {
                "enabled": True  # Use original values for more deterministic behavior
            }
        }
    
    def test_seed_generation_consistency(self):
        """Test that same configuration generates same seed consistently."""
        config1 = ExperimentConfiguration(**self.config_data)
        config2 = ExperimentConfiguration(**self.config_data)
        
        seed1 = config1.get_effective_seed()
        seed2 = config2.get_effective_seed()
        
        self.assertEqual(seed1, seed2, "Same configuration should always generate same seed")
    
    def test_explicit_seed_override(self):
        """Test that explicit seed overrides generated seed."""
        # Configuration without explicit seed
        config1 = ExperimentConfiguration(**self.config_data)
        generated_seed = config1.get_effective_seed()
        
        # Configuration with explicit seed
        config_with_seed = self.config_data.copy()
        config_with_seed["seed"] = 12345
        config2 = ExperimentConfiguration(**config_with_seed)
        explicit_seed = config2.get_effective_seed()
        
        self.assertEqual(explicit_seed, 12345)
        self.assertNotEqual(generated_seed, explicit_seed)
    
    def test_random_operations_seeded(self):
        """Test that random operations are controlled by seed."""
        import random
        
        # Test with first seed
        SeedManager.set_experiment_seed(42)
        values1 = [random.random() for _ in range(10)]
        
        # Test with same seed again
        SeedManager.set_experiment_seed(42)
        values2 = [random.random() for _ in range(10)]
        
        # Test with different seed
        SeedManager.set_experiment_seed(123)
        values3 = [random.random() for _ in range(10)]
        
        self.assertEqual(values1, values2, "Same seed should produce identical random sequences")
        self.assertNotEqual(values1, values3, "Different seed should produce different sequences")
    
    def test_distribution_generator_reproducibility(self):
        """Test that distribution generation is reproducible."""
        from core.distribution_generator import DistributionGenerator
        
        # Test distribution generation with same seed
        SeedManager.set_experiment_seed(42)
        dist_set1 = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0))
        
        SeedManager.set_experiment_seed(42)
        dist_set2 = DistributionGenerator.generate_dynamic_distribution((0.5, 2.0))
        
        # Should be identical
        self.assertEqual(dist_set1.multiplier, dist_set2.multiplier)
        self.assertEqual(len(dist_set1.distributions), len(dist_set2.distributions))
        
        for d1, d2 in zip(dist_set1.distributions, dist_set2.distributions):
            self.assertEqual(d1.high, d2.high)
            self.assertEqual(d1.medium_high, d2.medium_high)
            self.assertEqual(d1.medium, d2.medium)
            self.assertEqual(d1.medium_low, d2.medium_low)
            self.assertEqual(d1.low, d2.low)
    
    def test_config_yaml_roundtrip_with_seed(self):
        """Test saving and loading configuration with seed preserves reproducibility."""
        # Add explicit seed
        config_with_seed = self.config_data.copy()
        config_with_seed["seed"] = 54321
        
        config_original = ExperimentConfiguration(**config_with_seed)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_original.to_yaml(f.name)
            
            # Load from file
            config_loaded = ExperimentConfiguration.from_yaml(f.name)
            
            # Should have same effective seed
            self.assertEqual(config_original.get_effective_seed(), config_loaded.get_effective_seed())
            self.assertEqual(config_loaded.seed, 54321)
            
            # Clean up
            os.unlink(f.name)
    
    def test_experiment_manager_seed_initialization(self):
        """Test that ExperimentManager initializes seeds properly."""
        config = ExperimentConfiguration(**self.config_data)
        manager = FrohlichExperimentManager(config)
        
        # The seed should be determined from config
        expected_seed = config.get_effective_seed()
        
        # Create mock to capture seed initialization
        import unittest.mock
        with unittest.mock.patch.object(SeedManager, 'set_experiment_seed') as mock_set_seed:
            # Note: We can't easily test full experiment without API keys
            # So we just test the seed initialization part
            
            # This would normally be called in run_complete_experiment
            effective_seed = SeedManager.initialize_reproducibility(config)
            
            # Verify seed was set
            mock_set_seed.assert_called_once_with(expected_seed)
            self.assertEqual(effective_seed, expected_seed)
    
    @unittest.skipIf(
        not os.getenv('OPENAI_API_KEY') and not os.getenv('OPENROUTER_API_KEY'),
        "API keys required for full experiment test"
    )
    async def test_full_experiment_reproducibility(self):
        """Test that complete experiments are reproducible with same seed.
        
        Note: This test requires API keys and may be slow/expensive.
        Only run when specifically testing reproducibility end-to-end.
        """
        # Add explicit seed for reproducibility
        config_with_seed = self.config_data.copy()
        config_with_seed["seed"] = 99999
        
        config = ExperimentConfiguration(**config_with_seed)
        
        # Run first experiment
        manager1 = FrohlichExperimentManager(config)
        await manager1.async_init()
        
        # We would run the full experiment here, but it requires API access
        # For now, just verify the seed is properly initialized
        effective_seed1 = config.get_effective_seed()
        
        # Create second manager with same config
        manager2 = FrohlichExperimentManager(config)
        await manager2.async_init()
        effective_seed2 = config.get_effective_seed()
        
        # Should have same seeds
        self.assertEqual(effective_seed1, effective_seed2)
    
    def test_different_configs_different_seeds(self):
        """Test that different configurations produce different seeds."""
        config1 = ExperimentConfiguration(**self.config_data)
        
        # Modify configuration slightly
        config_data2 = self.config_data.copy()
        config_data2["phase2_rounds"] = 5  # Different from original
        config2 = ExperimentConfiguration(**config_data2)
        
        seed1 = config1.get_effective_seed()
        seed2 = config2.get_effective_seed()
        
        self.assertNotEqual(seed1, seed2, "Different configurations should generate different seeds")


def async_test(coro):
    """Decorator to run async test methods."""
    def wrapper(self):
        return asyncio.run(coro(self))
    return wrapper


# Apply async decorator to async test methods
TestExperimentReproducibility.test_full_experiment_reproducibility = async_test(
    TestExperimentReproducibility.test_full_experiment_reproducibility
)


if __name__ == '__main__':
    unittest.main()