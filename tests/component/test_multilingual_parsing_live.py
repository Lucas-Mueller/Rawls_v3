"""Live component tests for multilingual parsing behaviour."""
from __future__ import annotations

import pytest

from tests.support import build_utility_agent, parametrize_languages
from tests.support.prompt_catalog import (
    BALLOT_CHOICE_AVERAGE,
    BALLOT_CHOICE_FLOOR,
    BALLOT_CONSTRAINT_RANGE,
    PRINCIPLE_CHOICE_SIMPLE,
    prompt_map,
)
from utils.language_manager import SupportedLanguage


def _language_enum(language: SupportedLanguage | str) -> SupportedLanguage:
    if isinstance(language, SupportedLanguage):
        return language
    normalized = language.strip().lower()
    for enum_value in SupportedLanguage:
        if enum_value.value.lower() == normalized:
            return enum_value
    raise ValueError(f"Unsupported language: {language}")


@pytest.mark.component
@pytest.mark.live
@pytest.mark.requires_openai
@pytest.mark.asyncio
@parametrize_languages()
async def test_principle_choice_parsing(language: SupportedLanguage):
    agent = await build_utility_agent("gpt-4.1-nano", 0.0, language)

    sample_statements = prompt_map(PRINCIPLE_CHOICE_SIMPLE)

    result = await agent.parse_principle_choice_enhanced(sample_statements[language])
    assert result is not None
    assert result.principle is not None


@pytest.mark.component
@pytest.mark.live
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_cross_language_ballot_consistency():
    ballots = []
    for prompt_key in (BALLOT_CHOICE_FLOOR, BALLOT_CHOICE_AVERAGE):
        prompts = prompt_map(prompt_key)
        ballots.append({lang.value.lower(): prompts[lang] for lang in SupportedLanguage})

    for ballot_set in ballots:
        parsed_principles = []
        for lang_str, ballot in ballot_set.items():
            language = _language_enum(lang_str)
            agent = await build_utility_agent("gpt-4.1-nano", 0.0, language)
            parsed = await agent.parse_principle_choice_llm(ballot)
            parsed_principles.append(parsed.get("principle"))
            is_consistent = await agent.validate_ballot_parsing_consistency(ballot, parsed, language=language.value.lower())
            assert is_consistent
        unique = {p for p in parsed_principles if p}
        assert len(unique) == 1


@pytest.mark.component
@pytest.mark.live
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_constraint_amount_parsing():
    prompts = prompt_map(BALLOT_CONSTRAINT_RANGE)
    cases = [
        (prompts[SupportedLanguage.ENGLISH], SupportedLanguage.ENGLISH, 25000),
        (prompts[SupportedLanguage.SPANISH], SupportedLanguage.SPANISH, 18000),
        (prompts[SupportedLanguage.MANDARIN], SupportedLanguage.MANDARIN, 22000),
    ]

    for ballot, language, expected in cases:
        agent = await build_utility_agent("gpt-4.1-nano", 0.0, language)
        parsed = await agent.parse_principle_choice_llm(ballot)
        assert parsed.get("constraint_amount") == expected
        is_consistent = await agent.validate_ballot_parsing_consistency(ballot, parsed, language=language.value.lower())
        assert is_consistent
