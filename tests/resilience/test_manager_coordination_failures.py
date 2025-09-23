"""Manager-level resilience tests for coordination failures."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

import pytest

from core.phase1_manager import Phase1Manager
from core.phase2_manager import Phase2Manager
from config.models import AgentConfiguration, ExperimentConfiguration
from config.phase2_settings import Phase2Settings
from models import (
    ParticipantContext,
    Phase1Results,
    ApplicationResult,
    PrincipleRanking,
    RankedPrinciple,
    JusticePrinciple,
    CertaintyLevel,
    PrincipleChoice,
    IncomeClass,
)
from models.experiment_types import IncomeDistribution

pytestmark = pytest.mark.resilience


class StubParticipant:
    """Lightweight participant for resilience testing."""

    def __init__(self, name: str, agent_config=None):
        self.name = name
        self.config = agent_config or SimpleNamespace(
            name=name,
            personality="Cooperative",
            model="stub-model",
            temperature=0.0,
            memory_character_limit=4096,
            reasoning_enabled=False,
            language="English",
        )
        self.agent = SimpleNamespace(name=name)

    async def update_memory(self, *args, **kwargs):
        return "memory-updated"

    async def async_init(self):
        return None


class StubLanguageManager:
    """Language manager stub that provides basic translations."""

    def get(self, key: str, **kwargs) -> str:
        if key.startswith("constraint_formatting.currency_format"):
            amount = kwargs.get("amount", 0)
            return f"${amount:,.2f}"
        if key.startswith("common.income_classes"):
            return key.split(".")[-1]
        return key


@pytest.fixture
def agent_config():
    """Basic agent configuration for tests."""
    return AgentConfiguration(
        name="Agent Alpha",
        personality="Cooperative",
        model="stub-model",
        temperature=0.0,
        memory_character_limit=4096,
        reasoning_enabled=False,
        language="English",
    )


@pytest.fixture
def experiment_config():
    """Minimal experiment configuration."""
    return ExperimentConfiguration(
        agents=[
            AgentConfiguration(
                name="Agent A",
                personality="Cooperative",
                model="stub-model",
                temperature=0.0,
                memory_character_limit=4096,
                reasoning_enabled=False,
                language="English",
            ),
            AgentConfiguration(
                name="Agent B",
                personality="Competitive",
                model="stub-model",
                temperature=0.0,
                memory_character_limit=4096,
                reasoning_enabled=False,
                language="English",
            ),
        ],
        phase2_settings=Phase2Settings.get_default(),
    )


@pytest.fixture
def stub_utility_agent():
    """Utility agent with mock methods."""
    agent = SimpleNamespace()
    agent.parse_principle_choice_enhanced = AsyncMock(return_value=PrincipleChoice(
        principle=JusticePrinciple.MAXIMIZING_AVERAGE,
        constraint_amount=20000,
        certainty=CertaintyLevel.SURE,
    ))
    # PrincipleRanking requires all 4 principles ranked
    agent.parse_principle_ranking_enhanced = AsyncMock(return_value=PrincipleRanking(
        rankings=[
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=2),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
            RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4),
        ],
        certainty=CertaintyLevel.SURE,
    ))
    agent.validate_constraint_specification = AsyncMock(return_value=True)
    return agent


@pytest.mark.asyncio
async def test_phase1_parallel_task_partial_failure(monkeypatch, agent_config, stub_utility_agent):
    """Test Phase1Manager resilience when one participant task fails during asyncio.gather()."""

    # Create participants - one will fail, one will succeed
    participants = [
        StubParticipant("Agent A", agent_config),
        StubParticipant("Agent B", agent_config),
    ]

    language_manager = StubLanguageManager()
    error_handler = SimpleNamespace(_log_error=MagicMock())
    seed_manager = SimpleNamespace()

    manager = Phase1Manager(participants, stub_utility_agent, language_manager, error_handler, seed_manager)

    # Mock the single participant runner to fail for first participant
    call_count = 0
    async def mock_run_single_participant(participant, context, config, agent_config, logger, process_logger):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # First participant fails
            raise RuntimeError("Participant A task failed")
        # Second participant succeeds
        return Phase1Results(
            participant_name=participant.name,
            principle_choice=PrincipleChoice(
                principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                constraint_amount=20000,
                certainty=CertaintyLevel.SURE,
            ),
            principle_rankings=PrincipleRanking(
                rankings=[
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE, rank=1),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_FLOOR, rank=2),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT, rank=3),
                    RankedPrinciple(principle=JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT, rank=4),
                ],
                certainty=CertaintyLevel.SURE,
            ),
            application_result=ApplicationResult(
                round_number=1,
                principle_choice=PrincipleChoice(
                    principle=JusticePrinciple.MAXIMIZING_AVERAGE,
                    constraint_amount=20000,
                    certainty=CertaintyLevel.SURE,
                ),
                chosen_distribution=IncomeDistribution(
                    high=30000, medium_high=25000, medium=20000, medium_low=15000, low=10000
                ),
                assigned_income_class=IncomeClass.MEDIUM,
                earnings=15000.0,
            ),
            alternative_calculations={},
            round_contents={},
        )

    monkeypatch.setattr(manager, "_run_single_participant_phase1", mock_run_single_participant)

    config = SimpleNamespace(agents=[agent_config, agent_config])

    # The gather() should propagate the exception from the first participant
    with pytest.raises(RuntimeError, match="Participant A task failed"):
        await manager.run_phase1(config)

    assert call_count == 2  # Both tasks were started


@pytest.mark.asyncio
async def test_phase1_utility_agent_persistent_failure(monkeypatch, agent_config):
    """Test Phase1Manager resilience when utility agent validation consistently fails."""

    participants = [StubParticipant("Agent A", agent_config)]
    language_manager = StubLanguageManager()
    error_handler = SimpleNamespace(_log_error=MagicMock())
    seed_manager = SimpleNamespace()

    # Create utility agent that always fails parsing
    failing_utility_agent = SimpleNamespace()
    failing_utility_agent.parse_principle_choice_enhanced = AsyncMock(side_effect=asyncio.TimeoutError("Parse timeout"))
    failing_utility_agent.validate_constraint_specification = AsyncMock(return_value=True)

    manager = Phase1Manager(participants, failing_utility_agent, language_manager, error_handler, seed_manager)

    # Mock other components to focus on utility agent failure
    context = ParticipantContext(
        name="Agent A",
        role_description="Cooperative",
        bank_balance=0.0,
        memory="baseline",
        round_number=1,
        phase="phase_1",
        memory_character_limit=4096,
    )

    distribution_set = SimpleNamespace(
        distributions=[IncomeDistribution(
            high=30000, medium_high=25000, medium=20000, medium_low=15000, low=10000
        )],
        multiplier=1.0,
    )

    # Mock distribution and runner components
    monkeypatch.setattr(
        "core.phase1_manager.DistributionGenerator.apply_principle_to_distributions",
        lambda *args, **kwargs: (SimpleNamespace(), "explanation"),
    )
    monkeypatch.setattr(
        "core.phase1_manager.Runner.run",
        AsyncMock(return_value=SimpleNamespace(final_output="response")),
    )
    monkeypatch.setattr(
        "core.phase1_manager.MemoryManager.prompt_agent_for_memory_update",
        AsyncMock(return_value="updated memory"),
    )

    config = SimpleNamespace(
        original_values_mode=None,
        income_class_probabilities=None,
        distribution_range_phase1=(1, 2),
        memory_guidance_style="narrative",
    )

    # The utility agent failure should propagate up during principle application
    with pytest.raises(asyncio.TimeoutError, match="Parse timeout"):
        await manager._step_1_3_principle_application(
            participants[0], context, distribution_set, 1, agent_config, config
        )

    # Verify the utility agent was called
    failing_utility_agent.parse_principle_choice_enhanced.assert_called()


@pytest.mark.asyncio
async def test_phase2_memory_coordination_failure(monkeypatch, experiment_config):
    """Test Phase2Manager resilience when MemoryService operations fail."""

    participants = [
        StubParticipant("Agent A"),
        StubParticipant("Agent B"),
    ]

    utility_agent = SimpleNamespace()
    language_manager = StubLanguageManager()
    error_handler = SimpleNamespace(_log_error=MagicMock())
    seed_manager = SimpleNamespace()

    manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=experiment_config,
        language_manager=language_manager,
        error_handler=error_handler,
        seed_manager=seed_manager,
    )

    # Mock MemoryService to fail during memory operations
    failing_memory_service = MagicMock()
    failing_memory_service.update_discussion_memory = AsyncMock(
        side_effect=RuntimeError("Memory service coordination failed")
    )

    # Initialize services and replace MemoryService
    manager._initialize_services()
    manager.memory_service = failing_memory_service

    # Mock other services to pass through
    manager.discussion_service = MagicMock()
    manager.discussion_service.build_discussion_prompt = MagicMock(return_value="discussion prompt")
    manager.discussion_service.validate_statement = MagicMock(return_value=(True, "valid statement"))

    manager.speaking_order_service = MagicMock()
    manager.speaking_order_service.determine_speaking_order = MagicMock(return_value=["Agent A"])

    # Mock participant context and runner
    contexts = {
        "Agent A": ParticipantContext(
            name="Agent A",
            role_description="Cooperative",
            bank_balance=0.0,
            memory="baseline",
            round_number=1,
            phase="phase_2",
            memory_character_limit=4096,
        )
    }

    monkeypatch.setattr(
        "agents.Runner.run",
        AsyncMock(return_value=SimpleNamespace(final_output="discussion statement")),
    )

    # The memory service failure should propagate during memory update
    with pytest.raises(RuntimeError, match="Memory service coordination failed"):
        await manager._update_participant_memory_and_context(
            participants[0], contexts["Agent A"], "test statement", None, 1, 0, SimpleNamespace(public_history=[])
        )

    # Verify memory service was called
    failing_memory_service.update_discussion_memory.assert_called()


@pytest.mark.asyncio
async def test_phase1_to_phase2_state_transfer_failure(experiment_config):
    """Test cross-phase resilience when Phase1Results are malformed."""

    participants = [
        StubParticipant("Agent A"),
        StubParticipant("Agent B"),
    ]

    utility_agent = SimpleNamespace()
    language_manager = StubLanguageManager()
    error_handler = SimpleNamespace(_log_error=MagicMock())

    manager = Phase2Manager(
        participants,
        utility_agent,
        experiment_config=experiment_config,
        language_manager=language_manager,
        error_handler=error_handler,
    )

    # Create malformed Phase1 results - using SimpleNamespace to simulate missing attributes
    malformed_phase1_results = [
        SimpleNamespace(
            participant_name="Agent A",
            # Missing required attributes like final_ranking, application_results
        ),
        SimpleNamespace(
            participant_name="Agent B",
            # Incomplete structure
        ),
    ]

    # The malformed state transfer should fail during context initialization
    with pytest.raises((AttributeError, KeyError)):
        await manager.run_phase2(experiment_config, malformed_phase1_results)

