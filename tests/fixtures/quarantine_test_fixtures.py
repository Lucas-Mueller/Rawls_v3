"""
Quarantine test fixtures for Phase 2 integration tests.

Provides centralized, robust mock creation for testing quarantine behavior,
retry logic, and statistics tracking without brittle mock configurations.
"""

import asyncio
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, AsyncMock, MagicMock

from config import ExperimentConfiguration, AgentConfiguration
from config.phase2_settings import Phase2Settings
from experiment_agents.participant_agent import ParticipantAgent
from experiment_agents.utility_agent import UtilityAgent
from models.experiment_types import ParticipantContext, GroupDiscussionState, ExperimentPhase
from core.phase2_manager import Phase2Manager


class QuarantineTestFixture:
    """Centralized factory for creating robust test fixtures for quarantine testing."""
    
    @staticmethod
    def create_test_agent_config(
        name: str = "TestAgent",
        reasoning_enabled: bool = False,
        model: str = "gpt-4o-mini",  # Fast model for testing
        temperature: float = 0.0      # Deterministic for testing
    ) -> AgentConfiguration:
        """Create a real AgentConfiguration object with test-appropriate defaults."""
        return AgentConfiguration(
            name=name,
            personality=f"Test personality for {name} - methodical and analytical",
            model=model,
            temperature=temperature,
            memory_character_limit=50000,
            reasoning_enabled=reasoning_enabled
        )
    
    @staticmethod
    def create_test_phase2_settings(
        quarantine_enabled: bool = True,
        max_retries: int = 2,
        timeout_seconds: int = 10  # Minimum allowed by Phase2Settings validation
    ) -> Phase2Settings:
        """Create Phase2Settings optimized for testing quarantine behavior."""
        settings = Phase2Settings.get_default()
        settings.quarantine_failed_responses = quarantine_enabled
        settings.max_statement_retries = max_retries
        settings.statement_timeout_seconds = timeout_seconds
        # Quick timeouts for faster test execution (only set fields that actually exist)
        settings.confirmation_timeout_seconds = 10  # Minimum allowed value
        settings.ballot_timeout_seconds = 10       # Minimum allowed value
        return settings
    
    @staticmethod
    def create_test_experiment_config(
        num_agents: int = 2,
        phase2_settings: Optional[Phase2Settings] = None
    ) -> ExperimentConfiguration:
        """Create a complete ExperimentConfiguration for quarantine testing."""
        if phase2_settings is None:
            phase2_settings = QuarantineTestFixture.create_test_phase2_settings()
        
        agents = []
        for i in range(num_agents):
            agents.append(QuarantineTestFixture.create_test_agent_config(
                name=f"TestAgent{i+1}",
                reasoning_enabled=(i == 0)  # Mix reasoning enabled/disabled for variety
            ))
        
        return ExperimentConfiguration(
            language="English",
            agents=agents,
            utility_agent_model="gpt-4o-mini",  # Fast model for testing
            utility_agent_temperature=0.0,
            phase2_rounds=3,
            phase2_settings=phase2_settings,
        )
    
    @staticmethod
    def create_mock_participant_agent(agent_config: AgentConfiguration) -> Mock:
        """Create a properly configured mock ParticipantAgent."""
        participant = Mock(spec=ParticipantAgent)
        participant.name = agent_config.name
        participant.agent = AsyncMock()
        participant.config = agent_config
        participant.reasoning_enabled = agent_config.reasoning_enabled
        
        # Set up expected methods
        participant.update_memory = AsyncMock(return_value="Updated test memory")
        participant.get_memory = Mock(return_value=f"Test memory for {agent_config.name}")
        
        return participant
    
    @staticmethod
    def create_mock_utility_agent(model: str = "gpt-4o-mini") -> Mock:
        """Create a properly configured mock UtilityAgent."""
        utility_agent = Mock(spec=UtilityAgent)
        utility_agent.utility_model = model
        utility_agent.temperature = 0.0
        
        # Set up expected async methods
        utility_agent.async_init = AsyncMock()
        # detect_vote_intention_enhanced removed - using formal voting system
        utility_agent.detect_preference_statement = AsyncMock(return_value=None)
        utility_agent.parse_principle_choice_enhanced = AsyncMock()
        utility_agent.validate_constraint_specification = AsyncMock(return_value=True)
        
        return utility_agent
    
    @staticmethod
    def create_test_participant_contexts(
        num_contexts: int = 2,
        phase: ExperimentPhase = ExperimentPhase.PHASE_2
    ) -> List[ParticipantContext]:
        """Create test ParticipantContext objects."""
        contexts = []
        for i in range(num_contexts):
            context = ParticipantContext(
                name=f"TestAgent{i+1}",
                role_description="Test participant agent",
                bank_balance=1000.0,
                memory=f"Test memory for agent {i+1}",
                round_number=1,
                phase=phase,
                memory_character_limit=50000
            )
            contexts.append(context)
        return contexts
    
    @staticmethod
    def create_test_discussion_state(
        valid_participants: Optional[List[str]] = None
    ) -> GroupDiscussionState:
        """Create a test GroupDiscussionState."""
        discussion_state = GroupDiscussionState()
        if valid_participants:
            discussion_state.valid_participants = valid_participants
        else:
            discussion_state.valid_participants = ["TestAgent1", "TestAgent2"]
        return discussion_state
    
    @staticmethod
    def create_mock_phase2_manager(
        experiment_config: Optional[ExperimentConfiguration] = None,
        participants: Optional[List[Mock]] = None,
        utility_agent: Optional[Mock] = None
    ) -> Phase2Manager:
        """Create a Phase2Manager with properly mocked components."""
        if experiment_config is None:
            experiment_config = QuarantineTestFixture.create_test_experiment_config()
        
        if participants is None:
            participants = [
                QuarantineTestFixture.create_mock_participant_agent(agent_config)
                for agent_config in experiment_config.agents
            ]
        
        if utility_agent is None:
            utility_agent = QuarantineTestFixture.create_mock_utility_agent()
        
        return Phase2Manager(participants, utility_agent, experiment_config)


class QuarantineTestValidators:
    """Validation helpers for quarantine testing."""
    
    @staticmethod
    def assert_mock_has_required_attributes(mock_obj, required_attrs: List[str]):
        """Validate that a mock object has all required attributes."""
        for attr in required_attrs:
            assert hasattr(mock_obj, attr), f"Mock object missing required attribute: {attr}"
    
    @staticmethod
    def assert_agent_config_complete(agent_config: AgentConfiguration):
        """Validate that an AgentConfiguration has all required fields."""
        required_fields = ['name', 'personality', 'model', 'temperature', 
                          'memory_character_limit', 'reasoning_enabled']
        
        for field in required_fields:
            assert hasattr(agent_config, field), f"AgentConfiguration missing field: {field}"
            assert getattr(agent_config, field) is not None, f"AgentConfiguration field is None: {field}"
    
    @staticmethod
    def assert_statistics_dict_structure(stats_dict: Dict[str, int]):
        """Validate that a statistics dictionary has the expected structure."""
        expected_keys = [
            "total_statement_requests",
            "successful_statements", 
            "failed_validations",
            "retry_attempts",
            "fallback_statements",
            "quarantined_responses"
        ]
        
        for key in expected_keys:
            assert key in stats_dict, f"Statistics dictionary missing key: {key}"
            assert isinstance(stats_dict[key], int), f"Statistics key {key} should be integer, got {type(stats_dict[key])}"


class QuarantineTestScenarios:
    """Common test scenarios for quarantine behavior testing."""
    
    @staticmethod
    def create_timeout_scenario():
        """Create a test scenario that simulates agent timeouts."""
        return {
            "description": "Agent timeout during statement generation",
            "mock_exception": asyncio.TimeoutError("Agent timeout"),
            "expected_quarantine": True,
            "expected_fallback": True
        }
    
    @staticmethod
    def create_validation_failure_scenario():
        """Create a test scenario that simulates validation failures."""
        return {
            "description": "Agent returns invalid response",
            "mock_response": "",  # Empty response
            "validation_result": False,
            "expected_quarantine": True,
            "expected_retry": True
        }
    
    @staticmethod
    def create_retry_exhaustion_scenario():
        """Create a test scenario that simulates retry exhaustion."""
        return {
            "description": "Multiple validation failures leading to retry exhaustion",
            "mock_responses": ["", "invalid", "still invalid"],
            "validation_results": [False, False, False],
            "expected_final_quarantine": True,
            "expected_retry_count": 3
        }