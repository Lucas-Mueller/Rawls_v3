"""Resilience coverage for Phase 1 and Phase 2 managers."""
from __future__ import annotations

import logging
import random
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.phase1_manager import Phase1Manager
from core.phase2_manager import Phase2Manager
from models import (
    ParticipantContext,
    ApplicationResult,
    Phase2Results,
    GroupDiscussionResult,
)
from models.principle_types import (
    PrincipleChoice,
    PrincipleRanking,
    RankedPrinciple,
    JusticePrinciple,
    CertaintyLevel,
)
from models.experiment_types import IncomeDistribution
from models.principle_types import IncomeClass


pytestmark = pytest.mark.resilience


class StubParticipant:
    """Lightweight participant agent used in resilience scenarios."""

    def __init__(self, name: str, agent_config):
        self.name = name
        self.config = agent_config
        self.agent = SimpleNamespace(name=name)

    async def update_memory(self, *_args, **_kwargs):
        return "memory-updated"


class StubLanguageManager:
    def __init__(self):
        self.requests: list[str] = []

    def get(self, key: str, **kwargs) -> str:
        self.requests.append(key)
        if key.startswith("constraint_formatting.currency_format"):
            amount = kwargs.get("amount", 0)
            return f"${amount:,.2f}"
        if key.startswith("common.income_classes"):
            return key.split(".")[-1]
        return key


@pytest.mark.asyncio
async def test_phase1_application_reprompts_on_invalid_constraint(monkeypatch):
    """Phase 1 should re-prompt for constraint amounts when validation fails initially."""

    from config.models import AgentConfiguration
    language_manager = StubLanguageManager()

    agent_config = AgentConfiguration(
        name="Agent Alpha",
        personality="Cooperative",
        model="stub-model",
        temperature=0.0,
        memory_character_limit=4096,
        reasoning_enabled=False,
        language="English",
    )

    participant = StubParticipant("Agent Alpha", agent_config)

    context = ParticipantContext(
        name="Agent Alpha",
        role_description="Cooperative",
        bank_balance=0.0,
        memory="baseline",
        round_number=1,
        phase="phase_1",
        memory_character_limit=agent_config.memory_character_limit,
    )

    first_choice = PrincipleChoice(
        principle=JusticePrinciple.MAXIMIZING_AVERAGE,
        constraint_amount=None,
        certainty=CertaintyLevel.SURE,
    )
    second_choice = PrincipleChoice(
        principle=JusticePrinciple.MAXIMIZING_AVERAGE,
        constraint_amount=20000,
        certainty=CertaintyLevel.SURE,
    )

    utility_agent = SimpleNamespace(
        parse_principle_choice_enhanced=AsyncMock(side_effect=[first_choice, second_choice]),
        validate_constraint_specification=AsyncMock(side_effect=[False, True]),
        re_prompt_for_constraint=AsyncMock(return_value="retry for constraint"),
    )

    config = SimpleNamespace(
        original_values_mode=None,
        income_class_probabilities={},
        distribution_range_phase1=(1, 2),
        memory_guidance_style="narrative",
    )

    distribution_set = SimpleNamespace(
        distributions=[IncomeDistribution(high=30_000, medium_high=25_000, medium=20_000, medium_low=15_000, low=10_000)],
        multiplier=1.0,
    )

    # Patch distribution helpers to deterministic stubs
    monkeypatch.setattr(
        "core.phase1_manager.DistributionGenerator.apply_principle_to_distributions",
        lambda *_args, **_kwargs: (
            IncomeDistribution(high=30_000, medium_high=25_000, medium=20_000, medium_low=15_000, low=10_000),
            "stub-explanation",
        ),
    )
    monkeypatch.setattr(
        "core.phase1_manager.DistributionGenerator.calculate_payoff",
        lambda *_args, **_kwargs: (IncomeClass.HIGH, 12_000.0),
    )
    monkeypatch.setattr(
        "core.phase1_manager.DistributionGenerator.calculate_alternative_earnings_by_principle",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        "core.phase1_manager.DistributionGenerator.calculate_alternative_earnings_by_principle_fixed_class",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        "core.phase1_manager.DistributionGenerator.calculate_alternative_earnings",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        "core.phase1_manager.DistributionGenerator.calculate_comprehensive_constraint_outcomes",
        lambda *_args, **_kwargs: {
            "class_display_name": "High",
            "outcomes": [],
        },
    )

    async def fake_run(_agent, prompt, context=None):
        outputs = {
            "application": "initial response",
            "retry for constraint": "retry response",
        }
        return SimpleNamespace(final_output=outputs.get(prompt, "initial response"))

    monkeypatch.setattr("core.phase1_manager.Runner.run", fake_run)
    monkeypatch.setattr(
        "core.phase1_manager.Phase1Manager._build_application_prompt",
        lambda *args, **kwargs: "application",
    )

    monkeypatch.setattr(
        "core.phase1_manager.MemoryManager.prompt_agent_for_memory_update",
        AsyncMock(return_value="updated memory"),
    )

    error_log: list = []
    error_handler = SimpleNamespace(_log_error=lambda err: error_log.append(err))
    seed_manager = SimpleNamespace(random=random.Random(7))

    manager = Phase1Manager([participant], utility_agent, language_manager, error_handler, seed_manager)

    application_result, round_content = await manager._step_1_3_principle_application(
        participant,
        context,
        distribution_set,
        round_num=1,
        agent_config=agent_config,
        config=config,
    )

    assert application_result.principle_choice.constraint_amount == 20000
    assert utility_agent.validate_constraint_specification.await_count == 2
    assert utility_agent.re_prompt_for_constraint.await_count == 1
    assert "application" in round_content


@pytest.mark.asyncio
async def test_phase2_missing_translation_logs_warning(caplog):
    """Phase 2 manager should fall back gracefully when translations are missing."""

    participants: list[StubParticipant] = []
    stub_utility = SimpleNamespace()
    error_handler = SimpleNamespace()

    manager = Phase2Manager(
        participants,
        stub_utility,
        experiment_config=None,
        language_manager=None,
        error_handler=error_handler,
    )

    class NoopLogger:
        def __init__(self, backing):
            self.debug_logger = backing

    caplog.set_level(logging.WARNING)
    manager.logger = NoopLogger(logging.getLogger("phase2-resilience"))

    manager.language_manager = SimpleNamespace(get=lambda key, **kwargs: (_ for _ in ()).throw(KeyError(key)))

    message = manager._get_localized_message("missing.translation.key")
    assert "[MISSING: missing.translation.key]" in message
    assert any("missing.translation.key" in record.message for record in caplog.records)
