Testing
=======

The Frohlich Experiment project maintains comprehensive test coverage to ensure reliability and research validity. This guide explains the testing framework, how to run tests, and how to write new tests.

Testing Framework
-----------------

Test Architecture
~~~~~~~~~~~~~~~~

The project uses Python's built-in `unittest` framework with a custom test runner that provides:

.. code-block:: text

   Testing Architecture
   ├── Import Validation     # Verify all modules can be imported
   ├── Basic Functionality   # Core system functionality tests
   ├── Configuration Tests   # YAML loading and validation
   ├── Unit Tests           # Individual component testing
   └── Integration Tests    # End-to-end system testing

**Test Categories:**

- **Import Tests**: Ensure all modules import correctly
- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions and complete workflows
- **Configuration Tests**: Validate configuration loading and parsing
- **Error Handling Tests**: Verify error recovery and retry mechanisms

Running Tests
------------

Basic Test Execution
~~~~~~~~~~~~~~~~~~~~

**Run All Tests:**

.. code-block:: bash

   python run_tests.py

**Expected Output:**

.. code-block:: text

   ============================================================
   FROHLICH EXPERIMENT TEST RUNNER
   ============================================================
   Testing imports...
   ✓ All core imports successful
   ✓ Basic functionality test passed
   ✓ Configuration loading test passed

   Running unit tests...
   
   Running integration tests...

   ============================================================
   ALL TESTS PASSED ✓
   ============================================================

**Run Specific Test Categories:**

.. code-block:: bash

   # Unit tests only
   python run_tests.py unit
   
   # Integration tests only
   python run_tests.py integration

Individual Test Execution
~~~~~~~~~~~~~~~~~~~~~~~~~

**Run Specific Test Files:**

.. code-block:: bash

   # Memory manager tests
   python -m unittest tests.unit.test_memory_manager -v
   
   # Distribution generator tests
   python -m unittest tests.unit.test_distribution_generator -v
   
   # Configuration tests
   python -m unittest tests.integration.test_config_loading -v

**Run Specific Test Methods:**

.. code-block:: bash

   # Specific test method
   python -m unittest tests.unit.test_memory_manager.TestMemoryManager.test_memory_validation -v
   
   # Pattern matching
   python -m unittest tests.unit.test_memory_manager.TestMemoryManager.test_memory* -v

Test Coverage Analysis
~~~~~~~~~~~~~~~~~~~~~

**Install Coverage Tools:**

.. code-block:: bash

   pip install coverage

**Run Tests with Coverage:**

.. code-block:: bash

   # Generate coverage report
   coverage run run_tests.py
   coverage report -m
   
   # Generate HTML coverage report
   coverage html
   open htmlcov/index.html  # View in browser

Unit Testing
------------

Test Structure
~~~~~~~~~~~~~

Unit tests are organized by module in the `tests/unit/` directory:

.. code-block:: text

   tests/unit/
   ├── test_distribution_generator.py
   ├── test_language_manager.py
   ├── test_memory_manager.py
   ├── test_model_provider.py
   ├── test_models.py
   └── test_translation_validation.py

**Example Unit Test Structure:**

.. code-block:: python

   # tests/unit/test_example_module.py
   import unittest
   from unittest.mock import Mock, patch, AsyncMock
   
   from your_module import YourClass

   class TestYourClass(unittest.TestCase):
       
       def setUp(self):
           """Set up test fixtures before each test method."""
           self.instance = YourClass(param="test_value")
       
       def tearDown(self):
           """Clean up after each test method."""
           pass
       
       def test_basic_functionality(self):
           """Test basic functionality with clear assertions."""
           result = self.instance.method()
           self.assertEqual(result, expected_value)
           self.assertIsNotNone(result)
       
       def test_error_handling(self):
           """Test error conditions and edge cases."""
           with self.assertRaises(ValueError):
               self.instance.method(invalid_param)
       
       @patch('your_module.external_dependency')
       def test_with_mocking(self, mock_dependency):
           """Test with external dependencies mocked."""
           mock_dependency.return_value = "mocked_response"
           result = self.instance.method_using_dependency()
           self.assertEqual(result, expected_result)
           mock_dependency.assert_called_once()

Memory Manager Tests
~~~~~~~~~~~~~~~~~~~

**Example: Testing Memory Management:**

.. code-block:: python

   # tests/unit/test_memory_manager.py
   class TestMemoryManager(unittest.TestCase):
       
       def test_memory_validation(self):
           """Test memory length validation."""
           # Valid memory
           valid_memory = "Short memory content"
           result = validate_memory_length(valid_memory, limit=1000)
           self.assertTrue(result)
           
           # Invalid memory (too long)
           invalid_memory = "x" * 2000
           result = validate_memory_length(invalid_memory, limit=1000)
           self.assertFalse(result)
       
       async def test_memory_update_success(self):
           """Test successful memory update."""
           mock_agent = AsyncMock()
           mock_agent.run.return_value = Mock(data="Updated memory")
           
           manager = MemoryManager()
           result = await manager.prompt_agent_for_memory_update(
               mock_agent, "new_context", 50000
           )
           
           self.assertEqual(result, "Updated memory")
           mock_agent.run.assert_called_once()
       
       async def test_memory_retry_mechanism(self):
           """Test retry mechanism for memory limit exceeded."""
           mock_agent = AsyncMock()
           
           # First call fails, second succeeds
           mock_agent.run.side_effect = [
               Mock(data="x" * 60000),  # Too long
               Mock(data="Shorter memory")  # Valid
           ]
           
           manager = MemoryManager()
           result = await manager.prompt_agent_for_memory_update(
               mock_agent, "context", 50000
           )
           
           self.assertEqual(result, "Shorter memory")
           self.assertEqual(mock_agent.run.call_count, 2)

Configuration Testing
~~~~~~~~~~~~~~~~~~~~

**Example: Testing Configuration Validation:**

.. code-block:: python

   # tests/unit/test_models.py
   class TestConfigurationModels(unittest.TestCase):
       
       def test_valid_agent_configuration(self):
           """Test valid agent configuration creation."""
           config_data = {
               "name": "TestAgent",
               "personality": "Test personality",
               "model": "gpt-4.1-mini",
               "temperature": 0.3
           }
           
           config = AgentConfiguration(**config_data)
           self.assertEqual(config.name, "TestAgent")
           self.assertEqual(config.temperature, 0.3)
       
       def test_invalid_temperature(self):
           """Test validation of invalid temperature values."""
           config_data = {
               "name": "TestAgent", 
               "personality": "Test personality",
               "model": "gpt-4.1-mini",
               "temperature": 2.0  # Invalid: > 1.0
           }
           
           with self.assertRaises(ValidationError):
               AgentConfiguration(**config_data)
       
       def test_probability_sum_validation(self):
           """Test income probability validation."""
           # Invalid: probabilities don't sum to 1.0
           invalid_probs = {
               "high": 0.1, "medium_high": 0.2, "medium": 0.3,
               "medium_low": 0.3, "low": 0.2  # Sums to 1.1
           }
           
           with self.assertRaises(ValidationError):
               ExperimentConfiguration(
                   agents=[valid_agent_config],
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
   class TestCompleteExperimentFlow(unittest.TestCase):
       
       def setUp(self):
           """Set up integration test environment."""
           self.test_config = ExperimentConfiguration(
               agents=[
                   AgentConfiguration(
                       name="TestAgent1",
                       personality="Test personality 1",
                       model="gpt-4.1-mini",
                       temperature=0.0
                   ),
                   AgentConfiguration(
                       name="TestAgent2", 
                       personality="Test personality 2",
                       model="gpt-4.1-mini",
                       temperature=0.0
                   )
               ],
               utility_agent_model="gpt-4.1-mini",
               phase2_rounds=2
           )
       
       @patch('experiment_agents.participant_agent.Agent')
       @patch('experiment_agents.utility_agent.Agent')
       async def test_complete_experiment_with_mocks(self, mock_utility, mock_participant):
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
           
           # Run experiment
           manager = FrohlichExperimentManager(self.test_config)
           results = await manager.run_complete_experiment()
           
           # Verify results structure
           self.assertIsNotNone(results)
           self.assertIn('experiment_id', results)
           self.assertIn('phase1_results', results)
           self.assertIn('phase2_results', results)

Error Recovery Testing
~~~~~~~~~~~~~~~~~~~~~

**Testing Error Handling and Recovery:**

.. code-block:: python

   # tests/integration/test_error_recovery.py
   class TestErrorRecovery(unittest.TestCase):
       
       async def test_memory_limit_recovery(self):
           """Test recovery from memory limit exceeded."""
           
           # Mock agent that first exceeds memory, then succeeds
           mock_agent = AsyncMock()
           mock_agent.run.side_effect = [
               Mock(data="x" * 60000),  # Too long - triggers retry
               Mock(data="Valid memory")  # Succeeds on retry
           ]
           
           manager = MemoryManager()
           result = await manager.prompt_agent_for_memory_update(
               mock_agent, "context", 50000
           )
           
           # Verify recovery succeeded
           self.assertEqual(result, "Valid memory")
           self.assertEqual(mock_agent.run.call_count, 2)
       
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
               result = await retry_on_api_error(mock_agent.run)
           
           self.assertEqual(result.data, "Success after retry")

State Consistency Testing
~~~~~~~~~~~~~~~~~~~~~~~~

**Testing State Consistency Across Phases:**

.. code-block:: python

   # tests/integration/test_state_consistency.py
   class TestStateConsistency(unittest.TestCase):
       
       async def test_agent_state_preservation(self):
           """Test that agent state is preserved across phases."""
           
           # Mock agents with stateful behavior
           mock_agents = []
           for i in range(2):
               agent = AsyncMock()
               agent.name = f"Agent_{i}"
               agent.memory = {}  # Track state
               mock_agents.append(agent)
           
           # Simulate Phase 1
           phase1_manager = Phase1Manager(mock_agents, mock_utility_agent)
           phase1_results = await phase1_manager.run_phase1()
           
           # Verify state after Phase 1
           for agent in mock_agents:
               self.assertIsNotNone(agent.memory)
           
           # Simulate Phase 2 with same agents
           phase2_manager = Phase2Manager(mock_agents, mock_utility_agent)
           phase2_results = await phase2_manager.run_phase2(test_config)
           
           # Verify state consistency
           for agent in mock_agents:
               self.assertTrue(hasattr(agent, 'memory'))

Writing New Tests
----------------

Test Writing Guidelines
~~~~~~~~~~~~~~~~~~~~~~

**1. Test Naming Convention:**

.. code-block:: python

   def test_[functionality]_[condition]_[expected_result](self):
       """Clear description of what is being tested."""
       
   # Examples:
   def test_memory_validation_with_valid_input_returns_true(self):
   def test_agent_creation_with_invalid_model_raises_error(self):
   def test_consensus_detection_with_majority_agreement_succeeds(self):

**2. Test Structure (AAA Pattern):**

.. code-block:: python

   def test_example(self):
       """Test example following AAA pattern."""
       
       # Arrange - Set up test data and mocks
       test_data = {"key": "value"}
       mock_dependency = Mock()
       instance = YourClass(dependency=mock_dependency)
       
       # Act - Execute the function being tested
       result = instance.process(test_data)
       
       # Assert - Verify the results
       self.assertEqual(result, expected_value)
       mock_dependency.assert_called_once_with(test_data)

**3. Async Test Patterns:**

.. code-block:: python

   class TestAsyncFunctionality(unittest.TestCase):
       
       async def test_async_function(self):
           """Test async functionality."""
           
           mock_async_dependency = AsyncMock()
           mock_async_dependency.return_value = "expected_result"
           
           result = await async_function(mock_async_dependency)
           
           self.assertEqual(result, "expected_result")
       
       def test_async_wrapper(self):
           """Wrapper for async tests in unittest."""
           import asyncio
           asyncio.run(self.test_async_function())

**4. Mock Usage Patterns:**

.. code-block:: python

   # Mock external dependencies
   @patch('your_module.external_api_call')
   def test_with_external_dependency(self, mock_api):
       mock_api.return_value = {"status": "success"}
       # Test implementation
   
   # Mock async dependencies
   async def test_async_with_mock(self):
       mock_agent = AsyncMock()
       mock_agent.run.return_value = Mock(data="response")
       # Test implementation
   
   # Mock multiple dependencies
   @patch('module.dependency_b')
   @patch('module.dependency_a') 
   def test_multiple_mocks(self, mock_a, mock_b):
       # Note: patches are applied in reverse order
       # Test implementation

Test Data Management
~~~~~~~~~~~~~~~~~~~

**Creating Test Fixtures:**

.. code-block:: python

   # tests/fixtures/test_data.py
   def create_test_configuration():
       """Create standard test configuration."""
       return ExperimentConfiguration(
           agents=[
               AgentConfiguration(
                   name="TestAgent1",
                   personality="Analytical test agent",
                   model="gpt-4.1-mini",
                   temperature=0.0
               ),
               AgentConfiguration(
                   name="TestAgent2",
                   personality="Empathetic test agent", 
                   model="gpt-4.1-mini",
                   temperature=0.0
               )
           ],
           utility_agent_model="gpt-4.1-mini",
           phase2_rounds=2
       )

   def create_mock_phase1_results():
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

   from tests.fixtures.test_data import create_test_configuration
   
   class TestWithFixtures(unittest.TestCase):
       
       def setUp(self):
           self.test_config = create_test_configuration()
       
       def test_with_standard_config(self):
           # Use self.test_config in tests
           pass

Performance Testing
------------------

Testing Performance Characteristics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import time
   from tests.utils.performance import measure_time

   class TestPerformance(unittest.TestCase):
       
       @measure_time
       def test_memory_manager_performance(self):
           """Test memory manager performance."""
           manager = MemoryManager()
           
           start_time = time.time()
           
           # Perform operation
           result = manager.validate_memory_length("test" * 1000, 50000)
           
           end_time = time.time()
           execution_time = end_time - start_time
           
           # Assert performance requirements
           self.assertLess(execution_time, 0.1)  # Should complete in < 100ms
           self.assertTrue(result)

   # tests/utils/performance.py  
   def measure_time(func):
       """Decorator to measure test execution time."""
       def wrapper(*args, **kwargs):
           start = time.time()
           result = func(*args, **kwargs)
           end = time.time()
           print(f"{func.__name__} executed in {end - start:.4f} seconds")
           return result
       return wrapper

Test Debugging
--------------

Debugging Failed Tests
~~~~~~~~~~~~~~~~~~~~~

**1. Verbose Test Output:**

.. code-block:: bash

   # Run with verbose output
   python -m unittest tests.unit.test_memory_manager -v
   
   # Debug specific failing test
   python -m unittest tests.unit.test_memory_manager.TestMemoryManager.test_failing_method -v

**2. Add Debug Information:**

.. code-block:: python

   def test_debug_example(self):
       """Example of adding debug information to tests."""
       
       test_input = {"key": "value"}
       result = function_under_test(test_input)
       
       # Add debug output
       print(f"Test input: {test_input}")
       print(f"Result: {result}")
       print(f"Expected: {expected_value}")
       
       self.assertEqual(result, expected_value)

**3. Breakpoint Debugging:**

.. code-block:: python

   def test_with_breakpoint(self):
       """Test with debugger breakpoint."""
       
       test_data = setup_test_data()
       
       # Add breakpoint for debugging
       import pdb; pdb.set_trace()
       
       result = function_under_test(test_data)
       self.assertEqual(result, expected_value)

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
   python -m pytest tests/ --maxfail=1 --tb=short
   
   # Run with coverage like CI
   coverage run -m pytest tests/
   coverage report --show-missing

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

   def tearDown(self):
       """Clean up after tests."""
       # Clean up test files
       if hasattr(self, 'test_files'):
           for file_path in self.test_files:
               if os.path.exists(file_path):
                   os.remove(file_path)
       
       # Reset global state
       reset_global_configuration()

For more information on testing specific components, see the individual test files in the `tests/` directory and refer to the :doc:`development-setup` guide for setting up your testing environment.