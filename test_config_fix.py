#!/usr/bin/env python3
"""
Quick test to verify config file logging fix.
"""
import sys
from pathlib import Path

# Add the parent directory to Python path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager

def test_config_file_logging():
    """Test that the experiment manager correctly captures config file path."""
    # Test case 1: Default config file
    config1 = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    manager1 = FrohlichExperimentManager(config1, "config/default_config.yaml")
    expected1 = Path("config/default_config.yaml").name
    actual1 = Path(manager1.config_file_path).name
    print(f"Test 1 - Expected: {expected1}, Actual: {actual1}, Match: {expected1 == actual1}")
    
    # Test case 2: Custom config file 
    config2 = ExperimentConfiguration.from_yaml("config/fast_config.yaml")
    manager2 = FrohlichExperimentManager(config2, "config/fast_config.yaml")
    expected2 = Path("config/fast_config.yaml").name  
    actual2 = Path(manager2.config_file_path).name
    print(f"Test 2 - Expected: {expected2}, Actual: {actual2}, Match: {expected2 == actual2}")
    
    # Test case 3: Full path
    full_path = str(Path("config/stupid.yaml").absolute())
    config3 = ExperimentConfiguration.from_yaml("config/stupid.yaml")
    manager3 = FrohlichExperimentManager(config3, full_path)
    expected3 = Path(full_path).name
    actual3 = Path(manager3.config_file_path).name  
    print(f"Test 3 - Expected: {expected3}, Actual: {actual3}, Match: {expected3 == actual3}")
    
    # Test what would be logged
    print(f"\nWhat would be logged:")
    print(f"  Manager 1: '{Path(manager1.config_file_path).name}'")
    print(f"  Manager 2: '{Path(manager2.config_file_path).name}'")
    print(f"  Manager 3: '{Path(manager3.config_file_path).name}'")
    
    # All tests should pass
    all_passed = (expected1 == actual1 and expected2 == actual2 and expected3 == actual3)
    print(f"\nAll tests passed: {all_passed}")
    return all_passed

if __name__ == "__main__":
    test_config_file_logging()