"""Targeted tests for `UtilityAgent` parsing logic using stubbed LLM output."""

from __future__ import annotations

import json
from typing import Iterable

import pytest

from experiment_agents.utility_agent import UtilityAgent
from models.principle_types import JusticePrinciple
from utils.error_handling import ExperimentError
from utils.language_manager import create_language_manager, SupportedLanguage


def queue_parser_outputs(stubbed_runner, responses: Iterable[dict], agent_name: str = "Response Parser") -> None:
    """Register a sequence of JSON payloads for the parser agent."""

    stubbed_runner.register(
        agent_name,
        [
            json.dumps(
                {
                    "principle": response["principle"],
                    "constraint_amount": response.get("constraint_amount"),
                    "certainty": response.get("certainty", "sure"),
                }
            )
            for response in responses
        ],
    )


@pytest.fixture
def make_utility_agent():
    """Factory for constructing a utility agent in the desired language."""

    def _factory(language: SupportedLanguage) -> UtilityAgent:
        manager = create_language_manager(language)
        return UtilityAgent(
            utility_model="stub-model",
            temperature=0.0,
            experiment_language=language.value,
            language_manager=manager,
        )

    return _factory


class TestPrincipleChoiceParsing:
    """Validate principle choice parsing across languages and scenarios."""

    @pytest.mark.parametrize(
        "language,principles",
        [
            (
                SupportedLanguage.ENGLISH,
                [
                    {"principle": "maximizing_floor"},
                    {"principle": "maximizing_average"},
                    {"principle": "maximizing_average_floor_constraint", "constraint_amount": 60000},
                ],
            ),
            (
                SupportedLanguage.SPANISH,
                [
                    {"principle": "maximizing_average", "certainty": "very_sure"},
                    {"principle": "maximizing_average_floor_constraint", "constraint_amount": 45000},
                ],
            ),
            (
                SupportedLanguage.MANDARIN,
                [
                    {"principle": "maximizing_average_range_constraint"},
                ],
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_multilingual_parsing(
        self,
        language: SupportedLanguage,
        principles: list[dict],
        make_utility_agent,
        stubbed_runner,
    ) -> None:
        """Utility agent should respect stubbed responses regardless of language."""

        agent = make_utility_agent(language)
        queue_parser_outputs(stubbed_runner, principles)

        for payload in principles:
            result = await agent.parse_principle_choice_enhanced("placeholder input")
            assert result.principle == JusticePrinciple(payload["principle"])
            assert result.constraint_amount == payload.get("constraint_amount")

    @pytest.mark.asyncio
    async def test_validation_error_bubbles_up(self, make_utility_agent, stubbed_runner) -> None:
        """Invalid certainty values returned by the model should raise an ExperimentError."""

        agent = make_utility_agent(SupportedLanguage.ENGLISH)
        queue_parser_outputs(
            stubbed_runner,
            [
                {
                    "principle": "maximizing_floor",
                    "certainty": "impossible",
                }
            ],
        )

        with pytest.raises(ExperimentError):
            await agent.parse_principle_choice_enhanced("bad certainty")

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises(self, make_utility_agent, stubbed_runner) -> None:
        """When the stub supplies malformed JSON repeatedly the agent should escalate."""

        agent = make_utility_agent(SupportedLanguage.ENGLISH)
        stubbed_runner.register("Response Parser", ["not json" for _ in range(3)])

        with pytest.raises(ExperimentError):
            await agent.parse_principle_choice_enhanced("defective output", max_retries=3)


class TestPrincipleRankingParsing:
    """Validate ranking parsing using the stubbed runner."""

    def queue_ranking_outputs(self, stubbed_runner, payloads: Iterable[dict]) -> None:
        stubbed_runner.register(
            "Response Parser",
            [
                json.dumps(payload)
                for payload in payloads
            ],
        )

    @pytest.mark.asyncio
    async def test_ranking_success(self, make_utility_agent, stubbed_runner) -> None:
        agent = make_utility_agent(SupportedLanguage.ENGLISH)
        rankings = {
            "rankings": [
                {"principle": "maximizing_floor", "rank": 1},
                {"principle": "maximizing_average", "rank": 2},
                {"principle": "maximizing_average_floor_constraint", "rank": 3},
                {"principle": "maximizing_average_range_constraint", "rank": 4},
            ],
            "certainty": "sure",
        }
        stubbed_runner.register("Response Parser", [json.dumps(rankings)])

        result = await agent.parse_principle_ranking_enhanced("ranking statement")
        assert [r.rank for r in result.rankings] == [1, 2, 3, 4]
        assert result.certainty.name.lower() == "sure"

    @pytest.mark.asyncio
    async def test_ranking_invalid_payload(self, make_utility_agent, stubbed_runner) -> None:
        agent = make_utility_agent(SupportedLanguage.ENGLISH)
        stubbed_runner.register("Response Parser", [json.dumps({"rankings": [], "certainty": "sure"})])

        with pytest.raises(ExperimentError):
            await agent.parse_principle_ranking_enhanced("invalid ranking")
