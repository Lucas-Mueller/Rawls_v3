"""Focused pytest suite for Phase 2 voting helpers."""
from __future__ import annotations

import pytest

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import CertaintyLevel, JusticePrinciple
from utils.language_manager import create_language_manager, SupportedLanguage
from core.phase2_manager import Phase2Manager
from tests.utils.stubbed_runner import StubbedRunner
from tests.utils.stub_scripts import register_transcript


@pytest.fixture
async def utility_agent_factory():
    agents = {}

    async def _create(language: SupportedLanguage) -> UtilityAgent:
        if language in agents:
            return agents[language]
        agent = UtilityAgent(
            utility_model="stub-model",
            temperature=0.0,
            experiment_language=language.value,
            language_manager=create_language_manager(language),
        )
        agents[language] = agent
        return agent

    return _create


@pytest.mark.asyncio
async def test_multilingual_choice_parsing_with_voting_context(monkeypatch, utility_agent_factory):
    runner = StubbedRunner()
    monkeypatch.setattr("agents.Runner.run", runner.run)

    register_transcript(
        runner,
        {
            "Response Parser": [
                '{"principle": "maximizing_floor", "constraint_amount": null, "certainty": "very_sure"}',
                '{"principle": "maximizing_average", "constraint_amount": null, "certainty": "sure"}',
            ]
        },
    )

    english_agent = await utility_agent_factory(SupportedLanguage.ENGLISH)
    result_en = await english_agent.parse_principle_choice_enhanced("We should vote now.")
    assert result_en.principle == JusticePrinciple.MAXIMIZING_FLOOR
    assert result_en.certainty == CertaintyLevel.very_sure

    spanish_agent = await utility_agent_factory(SupportedLanguage.SPANISH)
    result_es = await spanish_agent.parse_principle_choice_enhanced("Propongo que votemos")
    assert result_es.principle == JusticePrinciple.MAXIMIZING_AVERAGE


@pytest.mark.asyncio
async def test_ranking_parsing_disambiguates_vote_prompts(monkeypatch, utility_agent_factory):
    runner = StubbedRunner()
    monkeypatch.setattr("agents.Runner.run", runner.run)

    register_transcript(
        runner,
        {
            "Response Parser": [
                '''{"rankings": [
                    {"principle": "maximizing_average_floor_constraint", "rank": 1},
                    {"principle": "maximizing_average_range_constraint", "rank": 2},
                    {"principle": "maximizing_average", "rank": 3},
                    {"principle": "maximizing_floor", "rank": 4}
                ], "certainty": "sure"}'''
            ]
        },
    )

    mandarin_agent = await utility_agent_factory(SupportedLanguage.MANDARIN)
    result = await mandarin_agent.parse_principle_ranking_enhanced("我们应该投票")
    assert result.rankings[0].principle == JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("let's vote", True),
        ("we should proceed to vote", True),
        ("ready to vote?", True),
        ("discuss further", False),
        ("i like maximizing the floor", False),
    ],
)
def test_voting_trigger_detection(phrase, expected):
    manager = Phase2Manager(participants=[], utility_agent=None)
    assert manager._is_voting_trigger_phrase(phrase) is expected
