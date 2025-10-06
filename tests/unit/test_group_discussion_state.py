"""Unit coverage for GroupDiscussionState isolation and validation rules."""
from __future__ import annotations

from typing import List
from unittest.mock import MagicMock

import pytest

from core.phase2_manager import Phase2Manager
from models.experiment_types import GroupDiscussionState


@pytest.mark.unit
class TestGroupDiscussionStateBehaviour:
    """Tests targeting discussion state isolation safeguards."""

    def test_experiment_ids_are_unique(self):
        state_one = GroupDiscussionState()
        state_two = GroupDiscussionState()
        assert state_one.experiment_id != state_two.experiment_id

    def test_add_statement_enforces_valid_participants(self):
        state = GroupDiscussionState(valid_participants=["Agent_1", "Agent_2"])
        state.round_number = 1
        state.add_statement("Agent_1", "Valid statement")
        with pytest.raises(ValueError):
            state.add_statement("Ghost", "Should be rejected")
        assert "Agent_1" in state.public_history
        assert "Ghost" not in state.public_history

    def test_validation_disabled_when_participants_none(self):
        state = GroupDiscussionState()
        state.round_number = 2
        state.add_statement("Random", "Works without validation")
        state.add_statement("Another", "Still accepted")
        assert len(state.statements) == 2

    def test_public_history_isolated_between_states(self):
        first = GroupDiscussionState(valid_participants=["Agent_1"])
        second = GroupDiscussionState(valid_participants=["Agent_2"])
        first.add_statement("Agent_1", "Statement for experiment A")
        second.add_statement("Agent_2", "Statement for experiment B")
        assert "experiment A" in first.public_history
        assert "experiment B" in second.public_history
        assert "experiment B" not in first.public_history


@pytest.mark.unit
@pytest.mark.asyncio
async def test_phase2_manager_assigns_valid_participants(monkeypatch):
    captured_states: List[GroupDiscussionState] = []

    class TrackingGroupDiscussionState(GroupDiscussionState):
        def __init__(self):
            super().__init__()
            captured_states.append(self)

    monkeypatch.setattr("core.phase2_manager.GroupDiscussionState", TrackingGroupDiscussionState)

    config = MagicMock()
    agent_config_one = MagicMock()
    agent_config_one.name = "Agent_1"
    agent_config_two = MagicMock()
    agent_config_two.name = "Agent_2"
    config.agents = [agent_config_one, agent_config_two]
    config.phase2_rounds = 0

    participant_one = MagicMock()
    participant_one.name = "Agent_1"
    participant_two = MagicMock()
    participant_two.name = "Agent_2"
    participants = [participant_one, participant_two]
    utility_agent = MagicMock()

    manager = Phase2Manager(participants, utility_agent, experiment_config=config)
    manager._initialize_services = MagicMock()

    contexts = [MagicMock(), MagicMock()]

    await manager._run_group_discussion(config, contexts, logger=None, process_logger=None)

    assert captured_states, "Expected the manager to create a discussion state"
    assert captured_states[0].valid_participants == ["Agent_1", "Agent_2"]
