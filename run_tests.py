"""
Test runner for the Frohlich Experiment.

Usage:
    python run_tests.py [test_type]
    
Arguments:
    test_type: 'unit', 'integration', or 'all' (default: 'all')
"""
import sys
import subprocess
from pathlib import Path


def run_unit_tests():
    """Run unit tests."""
    print("Running unit tests...")
    test_dir = Path(__file__).parent / "tests" / "unit"
    
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(test_dir), "-p", "test_*.py", "-v"]
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_integration_tests():
    """Run integration tests."""
    print("Running integration tests...")
    test_dir = Path(__file__).parent / "tests" / "integration"
    
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(test_dir), "-p", "test_*.py", "-v"]
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_import_test():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")
    
    try:
        # Test core imports
        from models import JusticePrinciple, IncomeDistribution
        from config import ExperimentConfiguration
        from core import DistributionGenerator, Phase1Manager, Phase2Manager
        from experiment_agents import UtilityAgent, create_participant_agent
        from utils import MemoryManager, ExperimentLogger
        
        print("✓ All core imports successful")
        
        # Test basic functionality
        dist = IncomeDistribution(high=32000, medium_high=27000, medium=24000, medium_low=13000, low=12000)
        assert dist.get_floor_income() == 12000
        assert dist.get_average_income() == 21600
        
        print("✓ Basic functionality test passed")
        
        # Test configuration loading
        config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
        assert len(config.agents) > 0
        
        print("✓ Configuration loading test passed")
        
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner."""
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    print("=" * 60)
    print("FROHLICH EXPERIMENT TEST RUNNER")
    print("=" * 60)
    
    success = True
    
    # Always run import test first
    if not run_import_test():
        print("Import tests failed. Stopping.")
        sys.exit(1)
    
    print()
    
    if test_type in ["unit", "all"]:
        if not run_unit_tests():
            success = False
        print()
    
    if test_type in ["integration", "all"]:
        if not run_integration_tests():
            success = False
        print()
    
    print("=" * 60)
    if success:
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        sys.exit(0)
    else:
        print("SOME TESTS FAILED ✗")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()