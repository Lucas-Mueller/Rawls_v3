"""Component-level tests for Phase 2 quarantine behaviour."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.phase2_manager import Phase2Manager
from tests.fixtures.quarantine_test_fixtures import (
    QuarantineTestFixture,
    QuarantineTestValidators,
)
from utils.language_manager import create_language_manager, SupportedLanguage


@pytest.mark.component
@pytest.mark.asyncio
async def test_quarantine_triggers_on_timeout():
    settings = QuarantineTestFixture.create_test_phase2_settings(
        quarantine_enabled=True,
        max_retries=1,
        timeout_seconds=0.1,
    )
    config = QuarantineTestFixture.create_test_experiment_config(num_agents=2, phase2_settings=settings)
    participants = [QuarantineTestFixture.create_mock_participant_agent(agent_cfg) for agent_cfg in config.agents]
    utility_agent = QuarantineTestFixture.create_mock_utility_agent()

    manager = Phase2Manager(participants, utility_agent, config)
    manager.language_manager = create_language_manager(SupportedLanguage.ENGLISH)
    manager._initialize_services()

    discussion_state = QuarantineTestFixture.create_test_discussion_state()
    context = QuarantineTestFixture.create_test_participant_contexts(num_contexts=1)[0]

    QuarantineTestValidators.assert_agent_config_complete(config.agents[0])

    manager.discussion_service.get_participant_statement_with_retry = AsyncMock(return_value=("__QUARANTINED__timeout", ""))

    statement, *_ = await manager._process_participant_statement(
        participants[0],
        context,
        config.agents[0],
        discussion_state,
        round_num=1,
        speaking_order_position=0,
        process_logger=None,
    )

    assert "unavailable" in discussion_state.public_history.lower()


@pytest.mark.component
@pytest.mark.asyncio
async def test_quarantined_statement_not_added_to_history():
    settings = QuarantineTestFixture.create_test_phase2_settings(quarantine_enabled=True)
    config = QuarantineTestFixture.create_test_experiment_config(num_agents=2, phase2_settings=settings)
    participants = [QuarantineTestFixture.create_mock_participant_agent(agent_cfg) for agent_cfg in config.agents]
    utility_agent = QuarantineTestFixture.create_mock_utility_agent()

    manager = Phase2Manager(participants, utility_agent, config)
    manager.language_manager = create_language_manager(SupportedLanguage.ENGLISH)
    manager._initialize_services()

    discussion_state = QuarantineTestFixture.create_test_discussion_state()
    initial_history = "Existing discussion"
    discussion_state.public_history = initial_history

    manager.discussion_service.get_participant_statement_with_retry = AsyncMock(return_value=("__QUARANTINED__Agent failed", ""))

    statement, *_ = await manager._process_participant_statement(
        participants[0],
        QuarantineTestFixture.create_test_participant_contexts(num_contexts=1)[0],
        config.agents[0],
        discussion_state,
        round_num=1,
        speaking_order_position=0,
        process_logger=None,
    )

    if statement.startswith("__QUARANTINED__"):
        neutral_msg = manager.language_manager.get("prompts.phase2_agent_unavailable", participant_name=participants[0].name)
        discussion_state.add_statement(participants[0].name, neutral_msg, manager.language_manager)

    assert "failed" not in discussion_state.public_history.lower()
    assert "unavailable" in discussion_state.public_history.lower()
    assert len(discussion_state.public_history) > len(initial_history)
