#!/usr/bin/env python3
"""
Unit tests for config file logging functionality.
Tests that experiment manager correctly captures and logs config file paths.
"""
import unittest
from pathlib import Path
import pytest

from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager


@pytest.mark.unit
class TestConfigFileLogging(unittest.TestCase):
    """Unit test suite for config file logging functionality."""
    
    def test_default_config_file_logging(self):
        """Test that the experiment manager correctly captures default config file path."""
        config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
        manager = FrohlichExperimentManager(config, "config/default_config.yaml")
        
        expected = Path("config/default_config.yaml").name
        actual = Path(manager.config_file_path).name
        
        self.assertEqual(expected, actual, f"Expected config filename {expected}, got {actual}")
    
    def test_custom_config_file_logging(self):
        """Test that the experiment manager correctly captures custom config file path.""" 
        config = ExperimentConfiguration.from_yaml("config/fast_config.yaml")
        manager = FrohlichExperimentManager(config, "config/fast_config.yaml")
        
        expected = Path("config/fast_config.yaml").name  
        actual = Path(manager.config_file_path).name
        
        self.assertEqual(expected, actual, f"Expected config filename {expected}, got {actual}")
    
    def test_full_path_config_file_logging(self):
        """Test that the experiment manager correctly handles full path config files."""
        full_path = str(Path("config/stupid.yaml").absolute())
        config = ExperimentConfiguration.from_yaml("config/stupid.yaml")
        manager = FrohlichExperimentManager(config, full_path)
        
        expected = Path(full_path).name
        actual = Path(manager.config_file_path).name  
        
        self.assertEqual(expected, actual, f"Expected config filename {expected}, got {actual}")
    
    def test_config_file_path_storage(self):
        """Test that config file path is properly stored in manager."""
        config_path = "config/default_config.yaml"
        config = ExperimentConfiguration.from_yaml(config_path)
        manager = FrohlichExperimentManager(config, config_path)
        
        # Verify the path is stored
        self.assertIsNotNone(manager.config_file_path, "Config file path should be stored")
        self.assertEqual(manager.config_file_path, config_path, "Config file path should match input")
    
    def test_relative_vs_absolute_path_handling(self):
        """Test that both relative and absolute paths are handled correctly."""
        relative_path = "config/default_config.yaml"
        absolute_path = str(Path(relative_path).absolute())
        
        # Test relative path
        config1 = ExperimentConfiguration.from_yaml(relative_path)
        manager1 = FrohlichExperimentManager(config1, relative_path)
        
        # Test absolute path
        config2 = ExperimentConfiguration.from_yaml(relative_path)  # Load from relative
        manager2 = FrohlichExperimentManager(config2, absolute_path)  # But store as absolute
        
        # Both should result in the same filename when logged
        filename1 = Path(manager1.config_file_path).name
        filename2 = Path(manager2.config_file_path).name
        
        self.assertEqual(filename1, filename2, "Relative and absolute paths should result in same filename")
        self.assertEqual(filename1, "default_config.yaml", "Both should extract correct filename")
    
    def test_config_path_edge_cases(self):
        """Test edge cases for config path handling."""
        test_cases = [
            ("config/default_config.yaml", "default_config.yaml"),
            ("./config/default_config.yaml", "default_config.yaml"),
            ("config/../config/default_config.yaml", "default_config.yaml"),
        ]
        
        for input_path, expected_name in test_cases:
            with self.subTest(input_path=input_path):
                try:
                    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
                    manager = FrohlichExperimentManager(config, input_path)
                    
                    actual_name = Path(manager.config_file_path).name
                    self.assertEqual(expected_name, actual_name, 
                                   f"Path {input_path} should extract to filename {expected_name}")
                except Exception as e:
                    self.fail(f"Failed to handle config path {input_path}: {e}")
    
    def test_config_logging_integration(self):
        """Test that config file logging integrates with the logging system."""
        config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
        manager = FrohlichExperimentManager(config, "config/default_config.yaml")
        
        # Verify that the manager has the necessary attributes for logging
        self.assertTrue(hasattr(manager, 'config_file_path'), "Manager should have config_file_path attribute")
        self.assertTrue(hasattr(manager, 'logger'), "Manager should have logger attribute")
        
        # The config file path should be available for inclusion in experiment results
        expected_filename = "default_config.yaml"
        actual_filename = Path(manager.config_file_path).name
        self.assertEqual(expected_filename, actual_filename, 
                        "Config filename should be available for logging")


if __name__ == "__main__":
    # Allow direct execution for debugging
    unittest.main()