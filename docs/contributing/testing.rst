Testing
=======

The Frohlich Experiment project maintains comprehensive test coverage to ensure reliability and research validity. This guide explains the testing framework, how to run tests, and how to write new tests.

Testing Framework
-----------------

Intelligent Test Acceleration System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Frohlich Experiment implements an **intelligent test acceleration system** that provides ultra-fast feedback for development while maintaining comprehensive validation for releases.

.. code-block:: text

   Intelligent Testing Architecture
   ├── Ultra-Fast Mode          # 7 seconds - Unit tests only
   ├── Development Mode         # 5 minutes - Unit + fast tests
   ├── CI/CD Mode              # 15 minutes - Comprehensive validation
   ├── Full Mode               # 30-45 minutes - Complete validation
   └── Strategic Mocking Layer # 0.04 seconds - Service boundary testing

**Performance Achievements:**
- **Ultra-fast mode**: 99.3% improvement (7.6s vs 90-120 minutes)
- **Development workflow**: 95% improvement (5min vs 90-120 minutes)
- **CI/CD pipeline**: 85% improvement (15min vs 90-120 minutes)

**Test Categories:**

- **Ultra-fast Tests**: Service boundary testing with deterministic data (0 API calls)
- **Unit Tests**: Component-level testing with protocol-based dependency injection
- **Component Tests**: Mid-level integration with multilingual coverage
- **Integration Tests**: Cross-component workflows with API calls
- **Snapshot Tests**: Regression testing with golden reference data

Running Tests
------------

Intelligent Test Execution Modes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Ultra-Fast Mode (7 seconds, 0 API calls):**

.. code-block:: bash

   python run_tests.py --mode=ultra_fast

**Development Mode (5 minutes, minimal API calls):**

.. code-block:: bash

   python run_tests.py --mode=dev

**CI/CD Mode (15 minutes, comprehensive validation):**

.. code-block:: bash

   python run_tests.py --mode=ci

**Full Mode (30-45 minutes, complete validation):**

.. code-block:: bash

   python run_tests.py --mode=full

Individual Test Execution
~~~~~~~~~~~~~~~~~~~~~~~~~

**Run Specific Test Files:**

.. code-block:: bash

   # Memory manager tests
   pytest tests/unit/test_memory_manager.py -v

   # Distribution generator tests
   pytest tests/unit/test_distribution_generator.py -v

   # Configuration tests
   pytest tests/integration/test_config_loading.py -v

**Run Specific Test Methods:**

.. code-block:: bash

   # Specific test method
   pytest tests/unit/test_memory_manager.py::TestMemoryManager::test_memory_validation -v

   # Pattern matching
   pytest tests/unit/test_memory_manager.py -k "test_memory" -v

**Run Tests by Category:**

.. code-block:: bash

   # Run only unit tests
   pytest -m "unit" -v

   # Run only integration tests
   pytest -m "integration" -v

   # Run only live API tests (requires API keys)
   pytest -m "live" -v

   # Run only component tests
   pytest -m "component" -v

Test Coverage Analysis
~~~~~~~~~~~~~~~~~~~~~

**Run Tests with Coverage:**

.. code-block:: bash

   # Generate coverage report
   python run_tests.py --mode=ci --coverage

   # Generate HTML coverage report
   python run_tests.py --mode=ci --coverage -- --cov-report=html
   open htmlcov/index.html  # View in browser

Environment-Based Test Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Development mode (skips expensive tests by default)
   DEVELOPMENT_MODE=1 pytest --mode=dev

   # Force comprehensive testing in development
   pytest --mode=ci --run-live

   # Skip expensive tests even with API keys
   pytest --mode=ci --skip-expensive

   # Use custom configuration globally
   TEST_CONFIG_OVERRIDE=config/test_ultra_fast.yaml pytest --mode=dev

CLI Toggles
~~~~~~~~~~~

.. code-block:: bash

   pytest --run-live                    # enable live suites explicitly
   pytest --no-run-live                 # force-skip live suites
   pytest --languages=en,es             # restrict parametrised suites to English + Spanish
   pytest --languages=all               # force all supported languages
   pytest --skip-expensive              # skip tests marked expensive

Unit Testing
------------

Test Structure
~~~~~~~~~~~~~

Unit tests are organised around deterministic helpers in the `tests/unit/`
directory. The active suite focuses on configuration validation, model helper
logic, and the memory/error subsystems; parsing/voting coverage now lives in
the component layer alongside the prompt harness.

.. code-block:: text

   tests/unit/
   ├── test_agent_centric_logger.py
   ├── test_distribution_generator.py
   ├── test_error_handler.py
   ├── test_experiment_configuration_yaml.py
   ├── test_group_discussion_state.py
   ├── test_memory_manager.py
   ├── test_model_provider.py
   ├── test_model_provider_info.py
   ├── test_original_values_data.py
   ├── test_original_values_mode.py
   ├── test_phase2_context_initialization.py
   ├── test_principle_choice_validation.py
   ├── test_reasoning_error_handling.py
   ├── test_reproducibility.py
   ├── test_retry_helpers.py
   └── test_utility_agent_parsing.py

**Example Unit Test Structure:**

.. code-block:: python

   # tests/unit/test_example_module.py
   import pytest
   from unittest.mock import Mock, patch, AsyncMock

   from your_module import YourClass

   class TestYourClass:

       def test_basic_functionality(self):
           """Test basic functionality with clear assertions."""
           instance = YourClass(param="test_value")
           result = instance.method()
           assert result == expected_value
           assert result is not None

       def test_error_handling(self):
           """Test error conditions and edge cases."""
           instance = YourClass(invalid_param)
           with pytest.raises(ValueError):
               instance.method()

       @patch('your_module.external_dependency')
       def test_with_mocking(self, mock_dependency):
           """Test with external dependencies mocked."""
           mock_dependency.return_value = "mocked_response"
           instance = YourClass(dependency=mock_dependency)
           result = instance.method_using_dependency()
           assert result == expected_result
           mock_dependency.assert_called_once()

Memory Manager Tests
~~~~~~~~~~~~~~~~~~~

**Example: Testing Memory Management:**

.. code-block:: python

   # tests/unit/test_memory_manager.py
   import pytest
   from unittest.mock import AsyncMock, Mock

   from utils.memory_manager import MemoryManager

   class TestMemoryManager:

       def test_memory_validation(self):
           """Test memory length validation."""
           # Valid memory
           valid_memory = "Short memory content"
           result = MemoryManager.validate_memory_length(valid_memory, limit=1000)
           assert result is True

           # Invalid memory (too long)
           invalid_memory = "x" * 2000
           result = MemoryManager.validate_memory_length(invalid_memory, limit=1000)
           assert result is False

       @pytest.mark.asyncio
       async def test_memory_update_success(self):
           """Test successful memory update."""
           mock_agent = AsyncMock()
           mock_agent.run.return_value = Mock(data="Updated memory")

           result = await MemoryManager.prompt_agent_for_memory_update(
               agent=mock_agent,
               event_type="discussion_statement",
               event_data={"statement": "..."}
           )

           assert result == "Updated memory"
           mock_agent.run.assert_called_once()

       @pytest.mark.asyncio
       async def test_memory_retry_mechanism(self):
           """Test retry mechanism for memory limit exceeded."""
           mock_agent = AsyncMock()

           # First call fails, second succeeds
           mock_agent.run.side_effect = [
               Mock(data="x" * 60000),  # Too long
               Mock(data="Shorter memory")  # Valid
           ]

           result = await MemoryManager.prompt_agent_for_memory_update(
               agent=mock_agent,
               event_type="context",
               event_data={"statement": "..."}
           )

           assert result == "Shorter memory"
           assert mock_agent.run.call_count == 2

Configuration Testing
~~~~~~~~~~~~~~~~~~~~

**Example: Testing Configuration Validation:**

.. code-block:: python

   # tests/unit/test_models.py
   import pytest
   from pydantic import ValidationError

   from config.models import AgentConfiguration, ExperimentConfiguration

   class TestConfigurationModels:

       def test_valid_agent_configuration(self):
           """Test valid agent configuration creation."""
           config_data = {
               "name": "TestAgent",
               "personality": "Test personality",
               "model": "gpt-4o-mini",
               "temperature": 0.3
           }

           config = AgentConfiguration(**config_data)
           assert config.name == "TestAgent"
           assert config.temperature == 0.3

       def test_invalid_temperature(self):
           """Test validation of invalid temperature values."""
           config_data = {
               "name": "TestAgent",
               "personality": "Test personality",
               "model": "gpt-4o-mini",
               "temperature": 2.0  # Invalid: > 1.0
           }

           with pytest.raises(ValidationError):
               AgentConfiguration(**config_data)

       def test_probability_sum_validation(self):
           """Test income probability validation."""
           # Invalid: probabilities don't sum to 1.0
           invalid_probs = {
               "high": 0.1, "medium_high": 0.2, "medium": 0.3,
               "medium_low": 0.3, "low": 0.2  # Sums to 1.1
           }

           with pytest.raises(ValidationError):
               ExperimentConfiguration(
                   agents=[AgentConfiguration(
                       name="TestAgent",
                       personality="Test personality",
                       model="gpt-4o-mini"
                   )],
                   income_class_probabilities=invalid_probs
               )

Integration Testing
------------------

Integration Test Structure
~~~~~~~~~~~~~~~~~~~~~~~~~

Integration tests verify component interactions in `tests/integration/`:

.. code-block:: text

   tests/integration/
   ├── test_complete_experiment_flow.py
   ├── test_config_loading.py
   ├── test_error_recovery.py
   ├── test_mixed_model_experiment.py
   ├── test_multilingual_logging.py
   └── test_state_consistency.py

**Example Integration Test:**

.. code-block:: python

   # tests/integration/test_complete_experiment_flow.py
   import pytest
   from unittest.mock import AsyncMock, Mock, patch

   from core.experiment_manager import FrohlichExperimentManager
   from config.models import ExperimentConfiguration, AgentConfiguration

   class TestCompleteExperimentFlow:

       @pytest.fixture
       def test_config(self):
           """Create test configuration."""
           return ExperimentConfiguration(
               agents=[
                   AgentConfiguration(
                       name="TestAgent1",
                       personality="Test personality 1",
                       model="gpt-4o-mini",
                       temperature=0.0
                   ),
                   AgentConfiguration(
                       name="TestAgent2",
                       personality="Test personality 2",
                       model="gpt-4o-mini",
                       temperature=0.0
                   )
               ],
               phase2_rounds=2
           )

       @pytest.mark.asyncio
       @patch('experiment_agents.participant_agent.Agent')
       @patch('experiment_agents.utility_agent.Agent')
       async def test_complete_experiment_with_mocks(self, mock_utility, mock_participant, test_config):
           """Test complete experiment flow with mocked agents."""

           # Mock agent responses
           mock_participant_instance = AsyncMock()
           mock_participant_instance.run.return_value = Mock(
               data='{"chosen_principle": "a", "confidence_level": "high"}'
           )
           mock_participant.return_value = mock_participant_instance

           mock_utility_instance = AsyncMock()
           mock_utility_instance.run.return_value = Mock(
               data='{"parsed": true, "valid": true}'
           )
           mock_utility.return_value = mock_utility_instance

           # This test would need proper async initialization
           # For now, showing the test structure
           assert True  # Placeholder

Error Recovery Testing
~~~~~~~~~~~~~~~~~~~~~

**Testing Error Handling and Recovery:**

.. code-block:: python

   # tests/integration/test_error_recovery.py
   import pytest
   from unittest.mock import AsyncMock, Mock, patch

   class TestErrorRecovery:

       @pytest.mark.asyncio
       async def test_memory_limit_recovery(self):
           """Test recovery from memory limit exceeded."""

           # Mock agent that first exceeds memory, then succeeds
           mock_agent = AsyncMock()
           mock_agent.run.side_effect = [
               Mock(data="x" * 60000),  # Too long - triggers retry
               Mock(data="Valid memory")  # Succeeds on retry
           ]

           # Test with retry logic
           result = await MemoryManager.prompt_agent_for_memory_update(
               agent=mock_agent,
               event_type="context",
               event_data={"statement": "..."}
           )

           assert result == "Valid memory"
           assert mock_agent.run.call_count == 2

       @pytest.mark.asyncio
       async def test_api_error_retry(self):
           """Test API error retry mechanism."""

           mock_agent = AsyncMock()

           # First call raises API error, second succeeds
           mock_agent.run.side_effect = [
               Exception("API rate limit exceeded"),
               Mock(data="Success after retry")
           ]

           # Test with retry logic
           with patch('asyncio.sleep'):  # Mock sleep for faster testing
               # This would call retry_on_api_error function
               pass  # Placeholder for actual test

State Consistency Testing
~~~~~~~~~~~~~~~~~~~~~~~~

**Testing State Consistency Across Phases:**

.. code-block:: python

   # tests/integration/test_state_consistency.py
   import pytest
   from unittest.mock import AsyncMock

   class TestStateConsistency:

       @pytest.mark.asyncio
       async def test_agent_state_preservation(self):
           """Test that agent state is preserved across phases."""

           # Mock agents with stateful behavior
           mock_agents = []
           for i in range(2):
               agent = AsyncMock()
               agent.name = f"Agent_{i}"
               agent.memory = {}  # Track state
               mock_agents.append(agent)

           # This test would verify state preservation across phases
           # For now, showing test structure
           for agent in mock_agents:
               assert hasattr(agent, 'memory')

Writing New Tests
----------------

Test Writing Guidelines
~~~~~~~~~~~~~~~~~~~~~~

**1. Test Naming Convention:**

.. code-block:: python

   def test_[functionality]_[condition]_[expected_result]():
       """Clear description of what is being tested."""

   # Examples:
   def test_memory_validation_with_valid_input_returns_true():
   def test_agent_creation_with_invalid_model_raises_error():
   def test_consensus_detection_with_majority_agreement_succeeds():

**2. Test Structure (AAA Pattern):**

.. code-block:: python

   def test_example():
       """Test example following AAA pattern."""

       # Arrange - Set up test data and mocks
       test_data = {"key": "value"}
       mock_dependency = Mock()
       instance = YourClass(dependency=mock_dependency)

       # Act - Execute the function being tested
       result = instance.process(test_data)

       # Assert - Verify the results
       assert result == expected_value
       mock_dependency.assert_called_once_with(test_data)

**3. Async Test Patterns:**

.. code-block:: python

   import pytest

   class TestAsyncFunctionality:

       @pytest.mark.asyncio
       async def test_async_function(self):
           """Test async functionality."""

           mock_async_dependency = AsyncMock()
           mock_async_dependency.return_value = "expected_result"

           result = await async_function(mock_async_dependency)

           assert result == "expected_result"

**4. Mock Usage Patterns:**

.. code-block:: python

   # Mock external dependencies
   @patch('your_module.external_api_call')
   def test_with_external_dependency(mock_api):
       mock_api.return_value = {"status": "success"}
       # Test implementation

   # Mock async dependencies
   @pytest.mark.asyncio
   async def test_async_with_mock():
       mock_agent = AsyncMock()
       mock_agent.run.return_value = Mock(data="response")
       # Test implementation

   # Mock multiple dependencies
   @patch('module.dependency_b')
   @patch('module.dependency_a')
   def test_multiple_mocks(mock_a, mock_b):
       # Note: patches are applied in reverse order
       # Test implementation

Test Data Management
~~~~~~~~~~~~~~~~~~~

**Creating Test Fixtures:**

.. code-block:: python

   # tests/fixtures/test_data.py
   import pytest

   from config.models import ExperimentConfiguration, AgentConfiguration

   @pytest.fixture
   def test_configuration():
       """Create standard test configuration."""
       return ExperimentConfiguration(
           agents=[
               AgentConfiguration(
                   name="TestAgent1",
                   personality="Analytical test agent",
                   model="gpt-4o-mini",
                   temperature=0.0
               ),
               AgentConfiguration(
                   name="TestAgent2",
                   personality="Empathetic test agent",
                   model="gpt-4o-mini",
                   temperature=0.0
               )
           ],
           phase2_rounds=2
       )

   @pytest.fixture
   def mock_phase1_results():
       """Create mock Phase 1 results for testing."""
       return [
           {
               "agent_name": "TestAgent1",
               "responses": {
                   "principle_a": {
                       "chosen_principle": "a",
                       "confidence_level": "high"
                   }
               }
           }
       ]

**Using Test Fixtures:**

.. code-block:: python

   import pytest
   from tests.fixtures.test_data import test_configuration

   class TestWithFixtures:

       def test_with_standard_config(self, test_configuration):
           # Use test_configuration fixture in tests
           assert len(test_configuration.agents) == 2

Performance Testing
------------------

Testing Performance Characteristics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import time
   import pytest

   class TestPerformance:

       def test_memory_manager_performance(self):
           """Test memory manager performance."""
           start_time = time.time()

           # Perform operation
           result = MemoryManager.validate_memory_length("test" * 1000, 50000)

           end_time = time.time()
           execution_time = end_time - start_time

           # Assert performance requirements
           assert execution_time < 0.1  # Should complete in < 100ms
           assert result is True

Test Debugging
--------------

Debugging Failed Tests
~~~~~~~~~~~~~~~~~~~~~

**1. Verbose Test Output:**

.. code-block:: bash

   # Run with verbose output
   pytest tests/unit/test_memory_manager.py -v

   # Debug specific failing test
   pytest tests/unit/test_memory_manager.py::TestMemoryManager::test_failing_method -v

   # Show local variables on failure
   pytest tests/unit/test_memory_manager.py -v --tb=long

**2. Add Debug Information:**

.. code-block:: python

   def test_debug_example():
       """Example of adding debug information to tests."""

       test_input = {"key": "value"}
       result = function_under_test(test_input)

       # Add debug output
       print(f"Test input: {test_input}")
       print(f"Result: {result}")
       print(f"Expected: {expected_value}")

       assert result == expected_value

**3. Breakpoint Debugging:**

.. code-block:: python

   def test_with_breakpoint():
       """Test with debugger breakpoint."""

       test_data = setup_test_data()

       # Add breakpoint for debugging
       import pdb; pdb.set_trace()

       result = function_under_test(test_data)
       assert result == expected_value

Continuous Integration
---------------------

GitHub Actions Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

The project includes GitHub Actions that automatically run tests on:

- Pull requests
- Pushes to main branch
- Scheduled runs (weekly)

**Local CI Simulation:**

.. code-block:: bash

   # Simulate CI environment locally
   pytest --mode=ci --maxfail=1 --tb=short

   # Run with coverage like CI
   pytest --mode=ci --cov=. --cov-report=term-missing

Test Maintenance
---------------

Keeping Tests Current
~~~~~~~~~~~~~~~~~~~~

**Regular Maintenance Tasks:**

1. **Update Test Data**: Keep test configurations current with system changes
2. **Review Coverage**: Ensure new code has appropriate test coverage
3. **Mock Updates**: Update mocks when external dependencies change
4. **Performance Baselines**: Update performance expectations as system evolves

**Test Cleanup:**

.. code-block:: python

   import pytest
   import os

   class TestWithCleanup:

       def teardown_method(self):
           """Clean up after tests."""
           # Clean up test files
           test_files = getattr(self, 'test_files', [])
           for file_path in test_files:
               if os.path.exists(file_path):
                   os.remove(file_path)

           # Reset global state
           # reset_global_configuration()

For more information on testing specific components, see the individual test files in the `tests/` directory and refer to the :doc:`development-setup` guide for setting up your testing environment.