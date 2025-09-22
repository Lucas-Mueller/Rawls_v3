"""Resilience scenarios for `VotingService`."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from core.services.voting_service import VotingService
from config.phase2_settings import Phase2Settings

pytestmark = pytest.mark.resilience


@dataclass
class StubLanguageManager:
    def get(self, key: str, **kwargs) -> str:
        return key


@dataclass
class StubUtilityAgent:
    response: tuple

    def detect_numerical_agreement(self, response: str):
        return self.response


@pytest.fixture
def participant():
    return SimpleNamespace(name="AgentA", agent=SimpleNamespace(name="AgentA"))


@pytest.fixture
def participant_context():
    return SimpleNamespace(interaction_type=None, current_round_number=1)


@pytest.mark.asyncio
async def test_vote_prompt_timeout_defaults_to_continue(monkeypatch, participant, participant_context):
    async def _timeout(agent, prompt, context=None):
        await asyncio.sleep(0)
        raise asyncio.TimeoutError

    monkeypatch.setattr("experiment_agents.utility_agent.run_without_tracing", _timeout)

    service = VotingService(
        language_manager=StubLanguageManager(),
        utility_agent=StubUtilityAgent(response=(False, None)),
        settings=Phase2Settings.get_default(),
    )

    result = await service.prompt_for_vote_initiation(participant, participant_context, max_retries=1)
    assert result is False


def test_missing_translation_returns_placeholder(failing_language_manager):
    service = VotingService(
        language_manager=failing_language_manager,
        utility_agent=StubUtilityAgent(response=(False, None)),
        settings=Phase2Settings.get_default(),
    )

    message = service._get_localized_message("foo")
    assert message == "[MISSING: foo]"
*** End Patch
