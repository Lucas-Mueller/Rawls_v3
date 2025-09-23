"""
Trace metadata validation tests using real experiment manager execution.

This module tests trace metadata generation through actual experiment manager
execution with stubbed external services. Tests the real trace generation workflow
that would catch metadata drift and integration issues.

Focus areas:
- Real trace metadata generation from experiment execution
- Multilingual metadata accuracy through actual workflows
- Production code path validation for trace integration
- Real config → metadata propagation testing

Uses actual experiment execution patterns:
- Runs FrohlichExperimentManager.run_complete_experiment() with stubbed externals
- Tests real trace metadata creation through production code paths
- Validates actual trace generation workflow components
- Ensures trace metadata consistency with production behavior
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from config import ExperimentConfiguration
from core.experiment_manager import FrohlichExperimentManager
from models import (
    Phase1Results,
    Phase2Results,
    GroupDiscussionResult,
    ApplicationResult,
)
from models.principle_types import (
    PrincipleRanking,
    RankedPrinciple,
    PrincipleChoice,
    JusticePrinciple,
    CertaintyLevel,
)
from models.experiment_types import IncomeDistribution, IncomeClass


class StubParticipant:
    def __init__(self, cfg):
        self.name = cfg.name
        self.config = cfg
        self.agent = SimpleNamespace(name=cfg.name)

    async def update_memory(self, *_args, **_kwargs):
        return "memory"


class StubUtilityAgent:
    def __init__(self, *args, **kwargs):
        pass

    async def async_init(self):  # pragma: no cover - behaviour verified via manager tests
        return None

    async def validate_consensus_against_discussion(self, *_args, **_kwargs):
        return True, []


class StubAgentLogger:
    def initialize_experiment(self, *_args, **_kwargs):
        return None

    def set_seed_info(self, *_args, **_kwargs):
        return None

    def initialize_voting_history(self):
        return None


class StubPhase1Manager:
    def __init__(self, participants, *_args, **_kwargs):
        self.participants = participants

    async def run_phase1(self, *_args, **_kwargs):
        ranking = PrincipleRanking(
            rankings=[
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=2),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4),
            ],
            certainty=CertaintyLevel.SURE,
        )

        application = ApplicationResult(
            round_number=1,
            principle_choice=PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=None,
                certainty=CertaintyLevel.SURE,
            ),
            chosen_distribution=IncomeDistribution(high=30_000, medium_high=25_000, medium=20_000, medium_low=15_000, low=10_000),
            assigned_income_class=IncomeClass.HIGH,
            earnings=12_000.0,
            alternative_earnings={},
            alternative_earnings_same_class={},
        )

        return [
            Phase1Results(
                participant_name=participant.name,
                initial_ranking=ranking,
                post_explanation_ranking=ranking,
                application_results=[application],
                final_ranking=ranking,
                total_earnings=12_000.0,
                final_memory_state="memory",
            )
            for participant in self.participants
        ]


class StubPhase2Manager:
    def __init__(self, participants, *_args, **_kwargs):
        self.participants = participants

    async def run_phase2(self, _config, phase1_results, *_args, **_kwargs):
        principle_choice = PrincipleChoice(
            principle=JusticePrinciple.MAXIMIZING_AVERAGE,
            constraint_amount=None,
            certainty=CertaintyLevel.SURE,
        )
        discussion = GroupDiscussionResult(
            consensus_reached=True,
            agreed_principle=principle_choice,
            final_round=1,
            discussion_history="generated",
            vote_history=[],
        )

        payoff_results = {result.participant_name: 15_000.0 for result in phase1_results}
        final_rankings = {result.participant_name: result.final_ranking for result in phase1_results}

        return Phase2Results(
            discussion_result=discussion,
            payoff_results=payoff_results,
            final_rankings=final_rankings,
        )


def create_complete_language_manager_stub():
    """Create a complete language manager stub with all required methods."""
    return SimpleNamespace(
        get=lambda path, **kwargs: path,
        format_memory_section=lambda memory, **kwargs: memory,
        get_localized_principle_name=lambda principle, **kwargs: str(principle),
        get_localized_principle_description=lambda principle, **kwargs: f"Description for {principle}",
        format_number=lambda num, **kwargs: str(num),
        format_currency=lambda amount, **kwargs: f"${amount:,.2f}",
        get_phase1_instructions=lambda round_number, **kwargs: f"Phase 1 instructions for round {round_number}",
        get_phase2_instructions=lambda round_number, max_rounds=5, **kwargs: f"Phase 2 instructions for round {round_number} of {max_rounds}",
        get_parser_instructions=lambda **kwargs: "Parser instructions",
        get_validator_instructions=lambda **kwargs: "Validator instructions",
        get_experiment_explanation=lambda **kwargs: "Experiment explanation",
        get_prompt=lambda category, prompt_key, **kwargs: f"{category}_{prompt_key}",
        get_message=lambda category, message_group, message_key, **kwargs: f"{category}_{message_group}_{message_key}",
        format_context_info=lambda name, role_description, bank_balance, **kwargs: f"Context for {name}",
        format_memory_context=lambda name, bank_balance, personality, **kwargs: f"Memory context for {name}",
        format_phase2_discussion_instructions=lambda **kwargs: "Phase 2 discussion instructions",
        get_principle_list_formatted=lambda list_type="detailed", **kwargs: "Formatted principle list",
        get_two_stage_principle_selection_prompt=lambda **kwargs: "Two stage principle selection prompt",
        get_two_stage_amount_specification_prompt=lambda principle_name, **kwargs: f"Amount specification for {principle_name}",
        get_justice_principle_name=lambda principle_key, **kwargs: str(principle_key),
        get_certainty_level_name=lambda certainty_key, **kwargs: str(certainty_key),
        get_phase_name=lambda phase_key, **kwargs: str(phase_key),
        format_amount_display=lambda amount, **kwargs: f"${amount:,}",
        get_two_stage_timeout_message=lambda **kwargs: "Timeout message",
        get_validation_message=lambda validation_key, **kwargs: f"Validation: {validation_key}",
        get_error_message=lambda error_key, **kwargs: f"Error: {error_key}",
        get_success_message=lambda success_key, **kwargs: f"Success: {success_key}",
        get_status_message=lambda status_key, **kwargs: f"Status: {status_key}",
        get_principle_choice_parsing_prompt=lambda response, **kwargs: f"Parse choice from: {response}",
        get_principle_ranking_parsing_prompt=lambda response, **kwargs: f"Parse ranking from: {response}",
        get_constraint_re_prompt=lambda participant_name, principle_name, constraint_type, **kwargs: f"Constraint re-prompt for {participant_name}",
        get_format_improvement_prompt=lambda response, parse_type, **kwargs: f"Format improvement for {parse_type}",
        get_two_stage_error_message=lambda error_type, attempt, max_attempts, **kwargs: f"Error {error_type}, attempt {attempt}/{max_attempts}",
        get_justice_principle_name_english=lambda principle_key, **kwargs: str(principle_key),
        get_certainty_level_name_english=lambda certainty_key, **kwargs: str(certainty_key),
    )


def setup_experiment_with_trace_capture(monkeypatch, config):
    """Setup experiment with all necessary stubs and trace capture."""
    captured_trace = {}

    # Stub participant creation
    participant_agents = [StubParticipant(cfg) for cfg in config.agents]

    async def fake_create_participants(self):
        return participant_agents

    # Set up all necessary stubs
    monkeypatch.setattr(FrohlichExperimentManager, "_create_participants", fake_create_participants)
    monkeypatch.setattr("core.experiment_manager.UtilityAgent", StubUtilityAgent)
    monkeypatch.setattr("core.experiment_manager.Phase1Manager", StubPhase1Manager)
    monkeypatch.setattr("core.experiment_manager.Phase2Manager", StubPhase2Manager)
    monkeypatch.setattr("core.experiment_manager.build_experiment_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        FrohlichExperimentManager,
        "_set_general_logging_info",
        lambda self, _results: None,
    )
    monkeypatch.setattr(
        FrohlichExperimentManager,
        "_set_fallback_general_info",
        lambda self, _results: None,
    )

    # Set up trace capture
    class DummyTrace:
        def __init__(self, name: str, metadata: dict) -> None:
            captured_trace["name"] = name
            captured_trace["metadata"] = metadata

        def __enter__(self):
            return SimpleNamespace(trace_id="trace-12345")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("core.experiment_manager.trace", DummyTrace)

    return captured_trace


# =============================================================================
# Multilingual Metadata Accuracy Tests
# =============================================================================

@pytest.mark.contracts
@pytest.mark.asyncio
@pytest.mark.parametrize("config_path,expected_language", [
    ("config/default_config.yaml", "English"),
    ("config/cheap_spanish.yaml", "Spanish"),
    ("config/cheap_mandarin.yaml", "Mandarin"),
])
async def test_multilingual_trace_metadata_accuracy(monkeypatch, config_path, expected_language):
    """Test trace metadata accuracy through real experiment execution."""
    # Load config and run actual experiment
    config = ExperimentConfiguration.from_yaml(config_path)
    config.agents = config.agents[:2]  # Limit for faster testing

    # Setup experiment with trace capture
    captured_trace = setup_experiment_with_trace_capture(monkeypatch, config)

    # Create and run actual experiment manager
    language_manager = create_complete_language_manager_stub()
    manager = FrohlichExperimentManager(config, config_path, language_manager=language_manager)
    manager.agent_logger = StubAgentLogger()

    # Run the complete experiment to generate real trace metadata
    results = await manager.run_complete_experiment()

    # Verify trace was captured and metadata is correct
    assert "name" in captured_trace
    assert "metadata" in captured_trace

    metadata = captured_trace["metadata"]
    assert metadata["experiment_id"] == manager.experiment_id
    assert metadata["language"] == expected_language, f"Expected {expected_language}, got {metadata['language']}"
    assert metadata["participant_count"] == str(len(config.agents))

    expected_names = ", ".join(agent.name for agent in config.agents)
    assert metadata["participant_names"] == expected_names

    # Verify experiment actually ran successfully
    assert isinstance(results.phase1_results, list) and results.phase1_results
    assert results.phase2_results.discussion_result.consensus_reached is True


@pytest.mark.contracts
@pytest.mark.asyncio
async def test_explicit_language_override_metadata(monkeypatch):
    """Test trace metadata when language is explicitly overridden in config."""
    # Load config and override language
    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    config.language = "Spanish"  # Override to Spanish
    config.agents = config.agents[:2]  # Limit for faster testing

    # Setup experiment with trace capture
    captured_trace = setup_experiment_with_trace_capture(monkeypatch, config)

    # Create and run actual experiment manager
    language_manager = create_complete_language_manager_stub()
    manager = FrohlichExperimentManager(config, "config/default_config.yaml", language_manager=language_manager)
    manager.agent_logger = StubAgentLogger()

    # Run the complete experiment to generate real trace metadata
    results = await manager.run_complete_experiment()

    # Verify language override is reflected in trace metadata
    metadata = captured_trace["metadata"]
    assert metadata["language"] == "Spanish"
    assert metadata["experiment_id"] == manager.experiment_id

    # Verify experiment actually ran successfully
    assert isinstance(results.phase1_results, list) and results.phase1_results
    assert results.phase2_results.discussion_result.consensus_reached is True


# =============================================================================
# Trace Disabling Behavior Tests
# =============================================================================

@pytest.mark.contracts
def test_trace_initialization_with_disabled_tracing():
    """Test trace metadata preparation behaves correctly when tracing is disabled."""
    # The disable_tracing_env fixture is already applied automatically
    # This test verifies experiment manager initialization works when tracing is disabled

    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    language_manager = create_complete_language_manager_stub()

    # When tracing is disabled, creating the manager should work without errors
    manager = FrohlichExperimentManager(config, "config/default_config.yaml", language_manager=language_manager)

    # Should be able to create experiment manager even when tracing is disabled
    assert manager.experiment_id is not None
    assert manager.config.language == "English"

    # Experiment manager should be properly initialized for trace generation
    assert hasattr(manager, 'config')
    assert hasattr(manager, 'experiment_id')


@pytest.mark.contracts
@pytest.mark.parametrize("config_path,expected_language", [
    ("config/default_config.yaml", "English"),
    ("config/cheap_spanish.yaml", "Spanish"),
    ("config/cheap_mandarin.yaml", "Mandarin"),
])
def test_trace_disabled_multilingual_configurations(config_path, expected_language):
    """Test multilingual configurations handle trace disabling correctly."""
    config = ExperimentConfiguration.from_yaml(config_path)
    language_manager = create_complete_language_manager_stub()

    # Should not raise errors regardless of language when tracing disabled
    manager = FrohlichExperimentManager(config, config_path, language_manager=language_manager)

    assert manager.experiment_id is not None
    assert manager.config.language == expected_language

    # Experiment manager should be properly initialized for any language
    assert hasattr(manager, 'config')
    assert hasattr(manager, 'experiment_id')


# =============================================================================
# Extended Metadata Field Validation Tests
# =============================================================================

@pytest.mark.contracts
@pytest.mark.asyncio
async def test_trace_metadata_field_completeness(monkeypatch):
    """Test all expected metadata fields are present and valid through real experiment execution."""
    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    config.agents = config.agents[:2]  # Limit for faster testing

    # Setup experiment with trace capture
    captured_trace = setup_experiment_with_trace_capture(monkeypatch, config)

    # Create and run actual experiment manager
    language_manager = create_complete_language_manager_stub()
    manager = FrohlichExperimentManager(config, "config/default_config.yaml", language_manager=language_manager)
    manager.agent_logger = StubAgentLogger()

    # Run the complete experiment to generate real trace metadata
    results = await manager.run_complete_experiment()

    # Verify all expected metadata fields are present
    metadata = captured_trace["metadata"]
    required_fields = ["experiment_id", "participant_count", "language", "participant_names"]

    for field in required_fields:
        assert field in metadata, f"Missing required metadata field: {field}"
        assert metadata[field] is not None, f"Metadata field {field} is None"
        assert metadata[field] != "", f"Metadata field {field} is empty"

    # Verify field types and formats
    assert isinstance(metadata["experiment_id"], str)
    assert len(metadata["experiment_id"]) > 0

    assert isinstance(metadata["participant_count"], str)
    assert metadata["participant_count"].isdigit()
    assert int(metadata["participant_count"]) == len(config.agents)

    assert isinstance(metadata["language"], str)
    assert metadata["language"] in ["English", "Spanish", "Mandarin"]

    assert isinstance(metadata["participant_names"], str)
    # Should have comma-separated names for multi-agent configs
    if len(config.agents) > 1:
        assert "," in metadata["participant_names"]

    # Verify additional fields that are actually in the metadata
    assert "config_file" in metadata
    assert "voting_system" in metadata
    assert metadata["voting_system"] == "formal_voting"
    assert "phase2_max_rounds" in metadata
    assert "participant_models" in metadata

    # Verify experiment actually ran successfully
    assert isinstance(results.phase1_results, list) and results.phase1_results
    assert results.phase2_results.discussion_result.consensus_reached is True


@pytest.mark.contracts
@pytest.mark.asyncio
async def test_trace_name_consistency(monkeypatch):
    """Test trace name is consistent and meaningful through real experiment execution."""
    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    config.agents = config.agents[:2]  # Limit for faster testing

    # Setup experiment with trace capture
    captured_trace = setup_experiment_with_trace_capture(monkeypatch, config)

    # Create and run actual experiment manager
    language_manager = create_complete_language_manager_stub()
    manager = FrohlichExperimentManager(config, "config/default_config.yaml", language_manager=language_manager)
    manager.agent_logger = StubAgentLogger()

    # Run the complete experiment to generate real trace
    results = await manager.run_complete_experiment()

    # Verify trace name exists and is meaningful
    assert "name" in captured_trace
    actual_trace_name = captured_trace["name"]
    assert isinstance(actual_trace_name, str)
    assert len(actual_trace_name) > 0
    assert "Frohlich Experiment" in actual_trace_name
    assert manager.experiment_id in actual_trace_name

    # Verify experiment actually ran successfully
    assert isinstance(results.phase1_results, list) and results.phase1_results
    assert results.phase2_results.discussion_result.consensus_reached is True


@pytest.mark.contracts
@pytest.mark.asyncio
@pytest.mark.parametrize("agent_count", [1, 2, 3])
async def test_participant_count_accuracy(monkeypatch, agent_count):
    """Test participant count metadata accuracy through real experiment execution."""
    # Create config with specific agent count
    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    if agent_count == 1:
        config.agents = config.agents[:1]
    elif agent_count == 2:
        config.agents = config.agents[:2]
    else:  # agent_count == 3
        # Add third agent by duplicating first one with different name
        third_agent = config.agents[0].model_copy()
        third_agent.name = "Charlie"
        config.agents = config.agents[:2] + [third_agent]

    # Setup experiment with trace capture
    captured_trace = setup_experiment_with_trace_capture(monkeypatch, config)

    # Create and run actual experiment manager
    language_manager = create_complete_language_manager_stub()
    manager = FrohlichExperimentManager(config, "config/default_config.yaml", language_manager=language_manager)
    manager.agent_logger = StubAgentLogger()

    # Run the complete experiment to generate real trace metadata
    results = await manager.run_complete_experiment()

    # Verify participant count matches exactly
    metadata = captured_trace["metadata"]
    assert metadata["participant_count"] == str(agent_count)
    assert int(metadata["participant_count"]) == len(config.agents)

    # Verify participant names list matches count
    names = metadata["participant_names"].split(", ")
    assert len(names) == agent_count

    # Verify experiment actually ran successfully
    assert isinstance(results.phase1_results, list) and results.phase1_results
    assert results.phase2_results.discussion_result.consensus_reached is True


# =============================================================================
# Edge Case Tests
# =============================================================================

@pytest.mark.contracts
@pytest.mark.asyncio
async def test_trace_metadata_with_empty_agent_names(monkeypatch):
    """Test trace metadata handles edge case of empty agent names through real experiment execution."""
    config = ExperimentConfiguration.from_yaml("config/default_config.yaml")
    config.agents = config.agents[:2]  # Limit for faster testing
    # Create edge case with empty name
    config.agents[0].name = ""

    # Setup experiment with trace capture
    captured_trace = setup_experiment_with_trace_capture(monkeypatch, config)

    # Create and run actual experiment manager
    language_manager = create_complete_language_manager_stub()
    manager = FrohlichExperimentManager(config, "config/default_config.yaml", language_manager=language_manager)
    manager.agent_logger = StubAgentLogger()

    # Run the complete experiment to generate real trace metadata
    results = await manager.run_complete_experiment()

    # Should still work and generate metadata
    metadata = captured_trace["metadata"]
    assert "participant_names" in metadata
    assert isinstance(metadata["participant_names"], str)

    # The empty name should be handled gracefully
    assert metadata["participant_count"] == str(len(config.agents))

    # Verify empty name is actually in the participant_names string
    assert metadata["participant_names"].startswith(", ") or ", ," in metadata["participant_names"]

    # Verify experiment actually ran successfully
    assert isinstance(results.phase1_results, list) and results.phase1_results
    assert results.phase2_results.discussion_result.consensus_reached is True