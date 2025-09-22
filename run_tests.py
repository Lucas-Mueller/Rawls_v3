"""
Test runner for the Frohlich Experiment.

Usage:
    python run_tests.py [test_type] [--coverage]
    
Arguments:
    test_type: 'unit', 'integration', 'regression', or 'all' (default: 'all')
    --coverage: Run tests with coverage reporting (requires pytest-cov)
"""
import sys
import subprocess
import os
from pathlib import Path

# Disable OpenAI Agents SDK tracing for all test execution
os.environ['OPENAI_AGENTS_DISABLE_TRACING'] = '1'
os.environ['OPENAI_DISABLE_TRACING'] = 'true'

# Also disable programmatically if agents module is available
try:
    from agents import set_tracing_disabled
    set_tracing_disabled(True)
except ImportError:
    # If agents module not available during import, just continue
    pass


def has_pytest():
    """Check if pytest is available."""
    try:
        import pytest
        return True
    except ImportError:
        return False


def run_unit_tests(coverage=False):
    """Run unit tests."""
    print("Running unit tests...")
    test_dir = Path(__file__).parent / "tests" / "unit"
    
    if has_pytest():
        cmd = [sys.executable, "-m", "pytest", "-q", str(test_dir)]
        if coverage:
            cmd.extend(["--cov=.", "--cov-report=term-missing"])
    else:
        print("Warning: pytest not available, falling back to unittest. Some tests may be skipped.")
        if coverage:
            print("Warning: Coverage reporting requires pytest-cov. Running without coverage.")
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(test_dir), "-p", "test_*.py", "-v"]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_integration_tests(coverage=False):
    """Run integration tests."""
    print("Running integration tests...")
    test_dir = Path(__file__).parent / "tests" / "integration"
    
    if has_pytest():
        cmd = [sys.executable, "-m", "pytest", "-q", str(test_dir)]
        if coverage:
            cmd.extend(["--cov=.", "--cov-report=term-missing"])
    else:
        print("Warning: pytest not available, falling back to unittest. Some async tests may not run properly.")
        if coverage:
            print("Warning: Coverage reporting requires pytest-cov. Running without coverage.")
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", str(test_dir), "-p", "test_*.py", "-v"]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_regression_tests(coverage=False):
    """Run regression tests that cover higher-level behaviours."""
    print("Running regression tests...")
    test_dir = Path(__file__).parent / "tests" / "regression"

    if not test_dir.exists():
        print("No regression tests directory found. Skipping.")
        return True

    if has_pytest():
        cmd = [sys.executable, "-m", "pytest", "-q", str(test_dir)]
        if coverage:
            cmd.extend(["--cov=.", "--cov-report=term-missing"])
    else:
        print("Warning: pytest not available, falling back to unittest for regression tests.")
        if coverage:
            print("Warning: Coverage reporting requires pytest-cov. Running without coverage.")
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
        from utils import MemoryManager, AgentCentricLogger
        
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
    args = sys.argv[1:]
    test_type = "all"
    coverage = False
    
    for arg in args:
        if arg == "--coverage":
            coverage = True
        elif arg in ["unit", "integration", "regression", "all"]:
            test_type = arg
    
    print("=" * 60)
    print("FROHLICH EXPERIMENT TEST RUNNER")
    if coverage:
        print("Running with coverage reporting")
    print("=" * 60)
    
    success = True
    
    # Always run import test first
    if not run_import_test():
        print("Import tests failed. Stopping.")
        sys.exit(1)
    
    print()
    
    if test_type in ["unit", "all"]:
        if not run_unit_tests(coverage):
            success = False
        print()
    
    if test_type in ["integration", "all"]:
        if not run_integration_tests(coverage):
            success = False
        print()

    if test_type in ["regression", "all"]:
        if not run_regression_tests(coverage):
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
