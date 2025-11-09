"""Live component checks for multilingual parsing via the utility agent."""
from __future__ import annotations

import pytest

from models import JusticePrinciple
from tests.support import build_utility_agent, parametrize_languages
from tests.support.prompt_catalog import (
    BALLOT_CONSTRAINT_FLOOR,
    BALLOT_CONSTRAINT_RANGE,
    PRINCIPLE_CHOICE_SIMPLE,
    PRINCIPLE_RANKING_ORDERED,
    get_prompt,
)
from utils.language_manager import SupportedLanguage


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
@parametrize_languages()
async def test_principle_choice_parsing_returns_canonical_enum(language: SupportedLanguage, openai_api_key):
    """Ensure principle choices map to canonical enums across locales."""
    agent = await build_utility_agent("gpt-4.1-mini", 0.0, language)
    statement = get_prompt(PRINCIPLE_CHOICE_SIMPLE, language)

    choice = await agent.parse_principle_choice_enhanced(statement)

    assert choice.principle == JusticePrinciple.MAXIMIZING_FLOOR
    assert choice.certainty is not None
    assert choice.reasoning == statement


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_constraint_amount_parsing_multilingual(openai_api_key):
    """Validate constraint extraction for floor/range prompts in all languages."""
    scenarios = [
        (
            BALLOT_CONSTRAINT_FLOOR,
            JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
            {
                SupportedLanguage.ENGLISH: 25000,
                SupportedLanguage.SPANISH: 25000,
                SupportedLanguage.MANDARIN: 25000,
            },
        ),
        (
            BALLOT_CONSTRAINT_RANGE,
            JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
            {
                SupportedLanguage.ENGLISH: 25000,
                SupportedLanguage.SPANISH: 18000,
                SupportedLanguage.MANDARIN: 22000,
            },
        ),
    ]

    for prompt_key, expected_principle, expected_amounts in scenarios:
        for language, expected_amount in expected_amounts.items():
            agent = await build_utility_agent("gpt-4.1-mini", 0.0, language)
            ballot = get_prompt(prompt_key, language)

            choice = await agent.parse_principle_choice_enhanced(ballot)

            assert choice.principle == expected_principle
            assert choice.constraint_amount is not None
            assert int(choice.constraint_amount) == expected_amount


@pytest.mark.component
@pytest.mark.live
@pytest.mark.slow
@pytest.mark.requires_openai
@pytest.mark.asyncio
@parametrize_languages()
async def test_principle_ranking_parsing(language: SupportedLanguage, openai_api_key):
    """Rankings should cover all principles and preserve ordering."""
    agent = await build_utility_agent("gpt-4.1-mini", 0.0, language)
    ranking_prompt = get_prompt(PRINCIPLE_RANKING_ORDERED, language)

    ranking = await agent.parse_principle_ranking_enhanced(ranking_prompt)

    expected_order = [
        JusticePrinciple.MAXIMIZING_FLOOR,
        JusticePrinciple.MAXIMIZING_AVERAGE,
        JusticePrinciple.MAXIMIZING_AVERAGE_FLOOR_CONSTRAINT,
        JusticePrinciple.MAXIMIZING_AVERAGE_RANGE_CONSTRAINT,
    ]

    parsed_order = [entry.principle for entry in ranking.rankings]
    assert parsed_order == expected_order
    assert ranking.certainty is not None
