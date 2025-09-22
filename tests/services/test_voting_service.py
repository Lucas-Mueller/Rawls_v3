"""Contract tests for `VotingService`."""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from core.services.voting_service import VotingService
from config.phase2_settings import Phase2Settings
from tests.utils.stubbed_runner import StubbedRunner
from tests.utils.stub_scripts import register_transcript

pytestmark = pytest.mark.contracts


@dataclass
class StubLanguageManager:
    prompts: dict

    def get(self, key: str, **kwargs) -> str:
        template = self.prompts[key]
        return template.format(**kwargs)


@dataclass
class StubUtilityAgent:
    responses: list

    def detect_numerical_agreement(self, response: str):
        return self.responses.pop(0)


@dataclass
class StubLogger:
    infos: list
    warnings: list

    def log_info(self, message: str) -> None:  # pragma: no cover - log-only helper
        self.infos.append(message)

    def log_warning(self, message: str) -> None:  # pragma: no cover - log-only helper
        self.warnings.append(message)


@pytest.fixture
def language_manager():
    return StubLanguageManager(
        prompts={
            "prompts.vote_initiation_prompt": "Do you want to vote?",
            "prompts.vote_initiation_with_statement_prompt": "Statement: {agent_recent_statement}",
            "prompts.vote_initiation_with_reasoning_prompt": "Reasoning: {internal_reasoning}",
            "prompts.vote_initiation_with_statement_and_reasoning_prompt": "Stmt {agent_recent_statement} / Reason {internal_reasoning}",
            "voting_prompts.retry_instruction": "Please answer yes or no.",
        }
    )


@pytest.fixture
def participant():
    return SimpleNamespace(name="AgentA", agent=SimpleNamespace(name="AgentA"))


@pytest.fixture
def participant_context():
    return SimpleNamespace(interaction_type=None, current_round_number=1)


@pytest.mark.asyncio
async def test_prompt_for_vote_initiation_success(monkeypatch, language_manager, participant, participant_context):
    runner = StubbedRunner()
    register_transcript(runner, {"AgentA": ["Yes"]})
    monkeypatch.setattr("agents.Runner.run", runner.run)

    utility_agent = StubUtilityAgent(responses=[(True, None)])
    logger = StubLogger(infos=[], warnings=[])
    settings = Phase2Settings.get_default()
    settings.statement_timeout_seconds = 5

    service = VotingService(language_manager, utility_agent, settings=settings, logger=logger)

    result = await service.prompt_for_vote_initiation(
        participant,
        participant_context,
        agent_recent_statement="We should wrap up",
        internal_reasoning="Consensus is near",
    )

    assert result is True
    assert participant_context.interaction_type == "vote_prompt"
    assert any("Vote initiation prompt result" in info for info in logger.infos)


@pytest.mark.asyncio
async def test_prompt_for_vote_initiation_defaults_to_continue(monkeypatch, language_manager, participant, participant_context):
    runner = StubbedRunner()
    register_transcript(runner, {"AgentA": ["Maybe", "No"]})
    monkeypatch.setattr("agents.Runner.run", runner.run)

    utility_agent = StubUtilityAgent(responses=[(False, "Could not parse"), (False, None)])
    logger = StubLogger(infos=[], warnings=[])
    settings = Phase2Settings.get_default()
    settings.statement_timeout_seconds = 5

    service = VotingService(language_manager, utility_agent, settings=settings, logger=logger)

    result = await service.prompt_for_vote_initiation(
        participant,
        participant_context,
        max_retries=2,
    )

    assert result is False
    assert any("Invalid vote prompt response" in warning for warning in logger.warnings)
*** End Patch
