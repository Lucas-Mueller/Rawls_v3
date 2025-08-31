"""
Consolidated Core Integration Tests

This module contains essential integration tests that verify cross-component 
functionality, consolidating the most critical scenarios from multiple files
while eliminating over-complex mocking and brittleness.

Key integration scenarios tested:
1. End-to-end experiment flow (simplified)
2. Manager-to-manager communication
3. Multilingual integration workflows  
4. Configuration loading and validation
5. Error handling and recovery mechanisms

Consolidated from:
- test_complete_experiment_flow.py (simplified)
- test_consensus_mechanisms.py
- test_state_consistency.py
- test_config_loading.py
- test_error_recovery.py
- test_multilingual_agent_parsing.py
- test_multilingual_ballot_parsing_integration.py
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Any

from config.models import ExperimentConfiguration, AgentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from core.phase1_manager import Phase1Manager
from core.phase2_manager import Phase2Manager
from utils.language_manager import LanguageManager, SupportedLanguage
from models.principle_types import JusticePrinciple


class TestCoreIntegration:
    """Simplified integration tests focusing on essential cross-component scenarios."""
    
    @pytest.fixture
    def minimal_config(self):
        """Create minimal experiment configuration for testing."""
        return ExperimentConfiguration(
            agents=[
                AgentConfiguration(
                    name="Alice",
                    personality="Analytical and systematic",
                    model="gpt-4.1-mini",
                    language="english"
                ),
                AgentConfiguration(
                    name="Bob", 
                    personality="Collaborative and fair-minded",
                    model="gpt-4.1-mini",
                    language="english"
                )
            ],
            phase1_rounds=2,  # Minimal rounds for testing
            phase2_max_rounds=3,
            voting_detection_mode="simple",
            seed=12345,
            temperature=0.1
        )
    
    @pytest.fixture
    def multilingual_config(self):
        """Create multilingual experiment configuration."""
        return ExperimentConfiguration(
            agents=[
                AgentConfiguration(
                    name="Ana",
                    personality="Metódica y justa",
                    model="gpt-4.1-mini", 
                    language="spanish"
                ),
                AgentConfiguration(
                    name="李明",
                    personality="理性且公正",
                    model="gpt-4.1-mini",
                    language="mandarin"  
                )
            ],
            phase1_rounds=2,
            phase2_max_rounds=3,
            voting_detection_mode="simple",
            seed=12345
        )
    
    @pytest.fixture
    def temp_config_file(self, minimal_config):
        """Create temporary config file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        # Convert config to YAML format for file
        config_dict = {
            "agents": [
                {
                    "name": agent.name,
                    "personality": agent.personality,
                    "model": agent.model,
                    "language": agent.language
                }
                for agent in minimal_config.agents
            ],
            "phase1_rounds": minimal_config.phase1_rounds,
            "phase2_max_rounds": minimal_config.phase2_max_rounds,
            "voting_detection_mode": minimal_config.voting_detection_mode,
            "seed": minimal_config.seed
        }
        
        import yaml
        yaml.dump(config_dict, temp_file)
        temp_file.close()
        
        yield temp_file.name
        
        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)

    # CONFIGURATION INTEGRATION TESTS
    def test_config_loading_validation(self, temp_config_file):
        """Test configuration loading and validation integration."""
        # Load configuration from file
        config = ExperimentConfiguration.from_yaml_file(temp_config_file)
        
        # Verify configuration loaded correctly
        assert len(config.agents) == 2
        assert config.agents[0].name == "Alice"
        assert config.agents[1].name == "Bob"
        assert config.phase1_rounds == 2
        assert config.voting_detection_mode == "simple"
        
        # Test configuration validation
        assert config.is_valid()
        
        # Test that managers can be created with this config
        experiment_manager = FrohlichExperimentManager(config)
        assert experiment_manager.config == config

    def test_config_validation_error_handling(self):
        """Test configuration validation with invalid data."""
        # Test missing required fields
        invalid_configs = [
            # Missing agents
            {"phase1_rounds": 2, "phase2_max_rounds": 3},
            
            # Empty agents list
            {"agents": [], "phase1_rounds": 2, "phase2_max_rounds": 3},
            
            # Invalid voting mode
            {
                "agents": [{"name": "Alice", "personality": "Test", "model": "gpt-4.1-mini"}],
                "voting_detection_mode": "invalid_mode"
            }
        ]
        
        for invalid_config in invalid_configs:
            with pytest.raises((ValueError, ValidationError)):
                ExperimentConfiguration(**invalid_config)

    # MANAGER INTEGRATION TESTS
    def test_experiment_manager_initialization(self, minimal_config):
        """Test experiment manager initialization and setup."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Verify managers are created
        assert experiment_manager.phase1_manager is not None
        assert experiment_manager.phase2_manager is not None
        
        # Verify configuration is passed through
        assert experiment_manager.phase1_manager.config == minimal_config
        assert experiment_manager.phase2_manager.config == minimal_config
        
        # Verify agents are initialized
        assert len(experiment_manager.participants) == 2
        assert experiment_manager.participants[0].name == "Alice"
        assert experiment_manager.participants[1].name == "Bob"

    def test_phase1_to_phase2_transition(self, minimal_config):
        """Test transition from Phase 1 to Phase 2."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Test Phase 1 completion state
        phase1_results = experiment_manager.phase1_manager.create_mock_results()
        assert phase1_results is not None
        assert "participant_states" in phase1_results
        
        # Test Phase 2 initialization with Phase 1 results
        phase2_initialized = experiment_manager.phase2_manager.initialize_from_phase1(phase1_results)
        assert phase2_initialized is True
        
        # Verify state consistency across phases
        phase1_participants = set(phase1_results["participant_states"].keys())
        phase2_participants = set(experiment_manager.phase2_manager.get_active_participants())
        assert phase1_participants == phase2_participants

    def test_manager_state_consistency(self, minimal_config):
        """Test state consistency between managers."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Test initial state consistency
        phase1_state = experiment_manager.phase1_manager.get_state_snapshot()
        phase2_state = experiment_manager.phase2_manager.get_state_snapshot()
        
        # Both managers should know about the same participants
        assert set(phase1_state["participants"]) == set(phase2_state["participants"])
        
        # Configuration should be consistent
        assert phase1_state["config"]["seed"] == phase2_state["config"]["seed"]

    # MULTILINGUAL INTEGRATION TESTS
    @pytest.mark.parametrize("language", ["spanish", "mandarin"])
    def test_multilingual_manager_integration(self, language):
        """Test manager integration with multilingual configurations."""
        config = ExperimentConfiguration(
            agents=[
                AgentConfiguration(
                    name="TestAgent",
                    personality="Test personality",
                    model="gpt-4.1-mini",
                    language=language
                )
            ],
            phase1_rounds=1,
            phase2_max_rounds=1
        )
        
        experiment_manager = FrohlichExperimentManager(config)
        
        # Verify language settings are propagated
        assert experiment_manager.participants[0].language == language
        
        # Test that language manager is properly configured
        language_manager = experiment_manager.get_language_manager()
        assert language_manager.current_language == SupportedLanguage(language)

    def test_mixed_language_experiment_integration(self, multilingual_config):
        """Test integration with mixed language experiments."""
        experiment_manager = FrohlichExperimentManager(multilingual_config)
        
        # Verify both languages are supported
        participants = experiment_manager.participants
        assert participants[0].language == "spanish"
        assert participants[1].language == "mandarin"
        
        # Test that language-specific prompts are available
        spanish_prompt = experiment_manager.get_prompt_for_participant(participants[0], "phase1_intro")
        mandarin_prompt = experiment_manager.get_prompt_for_participant(participants[1], "phase1_intro")
        
        # Prompts should be different (translated)
        assert spanish_prompt != mandarin_prompt
        assert len(spanish_prompt) > 0
        assert len(mandarin_prompt) > 0

    # CONSENSUS MECHANISM INTEGRATION TESTS
    def test_simple_mode_consensus_detection(self, minimal_config):
        """Test consensus detection in simple mode."""
        # Set up simple mode configuration
        minimal_config.voting_detection_mode = "simple"
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Mock participant preferences
        mock_preferences = {
            "Alice": JusticePrinciple.MAXIMIZING_FLOOR,
            "Bob": JusticePrinciple.MAXIMIZING_FLOOR
        }
        
        # Test consensus detection
        consensus_result = experiment_manager.phase2_manager.check_consensus_simple(mock_preferences)
        
        assert consensus_result.has_consensus is True
        assert consensus_result.agreed_principle == JusticePrinciple.MAXIMIZING_FLOOR

    def test_complex_mode_voting_integration(self, minimal_config):
        """Test voting mechanism integration in complex mode.""" 
        # Set up complex mode configuration
        minimal_config.voting_detection_mode = "complex"
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Test voting initiation
        voting_manager = experiment_manager.phase2_manager.get_voting_manager()
        assert voting_manager is not None
        
        # Test voting state management
        voting_initiated = voting_manager.initiate_voting(["Alice", "Bob"])
        assert voting_initiated is True
        
        # Test voting completion detection
        mock_votes = {
            "Alice": {"principle": JusticePrinciple.MAXIMIZING_FLOOR, "constraint": None},
            "Bob": {"principle": JusticePrinciple.MAXIMIZING_FLOOR, "constraint": None}
        }
        
        voting_complete = voting_manager.check_voting_complete(mock_votes)
        assert voting_complete is True

    # ERROR HANDLING INTEGRATION TESTS
    def test_agent_failure_recovery(self, minimal_config):
        """Test error recovery when agents fail."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Simulate agent failure scenario
        failed_agent = experiment_manager.participants[0]
        
        # Test error handling mechanism
        error_handled = experiment_manager.handle_agent_failure(failed_agent, "Connection timeout")
        
        # Should handle error gracefully
        assert error_handled is True
        
        # Experiment should be able to continue or terminate gracefully  
        state_after_error = experiment_manager.get_experiment_state()
        assert state_after_error["status"] in ["continuing", "terminated", "error_handled"]

    def test_configuration_error_recovery(self):
        """Test recovery from configuration errors."""
        # Test malformed configuration handling
        malformed_configs = [
            {"agents": "not_a_list"},  # Wrong type
            {"agents": [{"name": ""}]},  # Empty name
            {"phase1_rounds": -1},     # Invalid value
        ]
        
        for malformed_config in malformed_configs:
            # Should either raise appropriate error or handle gracefully
            try:
                config = ExperimentConfiguration(**malformed_config)
                # If it doesn't raise error, should at least be invalid
                assert not config.is_valid()
            except (ValueError, TypeError, ValidationError):
                # Expected for malformed configs
                pass

    def test_resource_cleanup_on_error(self, minimal_config):
        """Test resource cleanup when errors occur."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Start experiment
        experiment_started = experiment_manager.initialize_experiment()
        assert experiment_started is True
        
        # Simulate error requiring cleanup
        cleanup_successful = experiment_manager.cleanup_on_error("Simulated error")
        assert cleanup_successful is True
        
        # Resources should be properly cleaned up
        assert experiment_manager.get_active_resources() == []

    # END-TO-END INTEGRATION TESTS (SIMPLIFIED)
    def test_minimal_experiment_flow(self, minimal_config):
        """Test minimal end-to-end experiment flow without complex mocking."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Test experiment initialization
        initialized = experiment_manager.initialize_experiment()
        assert initialized is True
        
        # Test Phase 1 can be initiated
        phase1_ready = experiment_manager.phase1_manager.is_ready_to_start()
        assert phase1_ready is True
        
        # Test Phase 2 can be initiated after Phase 1
        mock_phase1_results = experiment_manager.phase1_manager.create_mock_results()
        phase2_ready = experiment_manager.phase2_manager.initialize_from_phase1(mock_phase1_results)
        assert phase2_ready is True
        
        # Test experiment can be finalized
        final_results = experiment_manager.finalize_experiment()
        assert final_results is not None
        assert "experiment_id" in final_results
        assert "participants" in final_results

    def test_experiment_state_transitions(self, minimal_config):
        """Test experiment state transitions."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Test initial state
        initial_state = experiment_manager.get_experiment_state()
        assert initial_state["phase"] == "not_started"
        
        # Test transition to Phase 1
        experiment_manager.start_phase1()
        phase1_state = experiment_manager.get_experiment_state()
        assert phase1_state["phase"] == "phase1"
        
        # Test transition to Phase 2  
        experiment_manager.start_phase2()
        phase2_state = experiment_manager.get_experiment_state()
        assert phase2_state["phase"] == "phase2"
        
        # Test completion
        experiment_manager.complete_experiment()
        final_state = experiment_manager.get_experiment_state()
        assert final_state["phase"] == "completed"

    def test_data_flow_consistency(self, minimal_config):
        """Test data flow consistency across components."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Initialize with test data
        test_data = {
            "experiment_id": "test_123",
            "participants": ["Alice", "Bob"],
            "initial_state": {"phase": "starting"}
        }
        
        experiment_manager.initialize_with_data(test_data)
        
        # Verify data flows to all components
        phase1_data = experiment_manager.phase1_manager.get_initialization_data()
        phase2_data = experiment_manager.phase2_manager.get_initialization_data()
        
        assert phase1_data["experiment_id"] == test_data["experiment_id"]
        assert phase2_data["experiment_id"] == test_data["experiment_id"]
        assert set(phase1_data["participants"]) == set(test_data["participants"])
        assert set(phase2_data["participants"]) == set(test_data["participants"])

    # LOGGING AND MONITORING INTEGRATION TESTS
    def test_integrated_logging_flow(self, minimal_config):
        """Test integrated logging across all components."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Enable comprehensive logging
        experiment_manager.enable_detailed_logging()
        
        # Perform operations that should generate logs
        experiment_manager.initialize_experiment()
        experiment_manager.start_phase1()
        
        # Verify logs are generated
        logs = experiment_manager.get_experiment_logs()
        assert len(logs) > 0
        
        # Verify log structure
        for log in logs[:5]:  # Check first 5 logs
            assert "timestamp" in log
            assert "level" in log
            assert "message" in log
            assert "component" in log

    def test_performance_monitoring_integration(self, minimal_config):
        """Test performance monitoring integration."""
        experiment_manager = FrohlichExperimentManager(minimal_config)
        
        # Enable performance monitoring
        experiment_manager.enable_performance_monitoring()
        
        # Perform monitored operations
        experiment_manager.initialize_experiment()
        
        # Get performance metrics
        metrics = experiment_manager.get_performance_metrics()
        
        assert "initialization_time" in metrics
        assert "memory_usage" in metrics
        assert metrics["initialization_time"] > 0