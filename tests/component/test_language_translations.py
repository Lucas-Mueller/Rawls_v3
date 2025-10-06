"""Component tests validating core translation keys across locales."""
from __future__ import annotations

import pytest

from utils.language_manager import SupportedLanguage
from tests.support import build_language_manager


PRINCIPLE_KEYS = [
    "common.principle_names.maximizing_floor",
    "common.principle_names.maximizing_average",
    "common.principle_names.maximizing_average_floor_constraint",
    "common.principle_names.maximizing_average_range_constraint",
]

DISCUSSION_KEYS = [
    "discussion_format.round_speaker_format",
    "system_messages.voting.result_summary",
]


@pytest.mark.component
@pytest.mark.parametrize("language", list(SupportedLanguage))
def test_principle_names_have_translations(language: SupportedLanguage):
    manager = build_language_manager(language)
    for key in PRINCIPLE_KEYS:
        value = manager.get(key)
        assert value, f"Missing translation for {key} in {language.value}"
        assert "missing" not in value.lower()
        if language is SupportedLanguage.ENGLISH:
            assert key.split(".")[-1].replace("_", " ")[:5].lower() in value.lower()


@pytest.mark.component
@pytest.mark.parametrize("language", list(SupportedLanguage))
def test_discussion_messages_format_correct(language: SupportedLanguage):
    manager = build_language_manager(language)
    round_message = manager.get(
        "discussion_format.round_speaker_format",
        round_number=2,
        speaker_name="Alice",
        statement="Sample"
    )
    assert str(2) in round_message
    assert "Alice" in round_message

    summary = manager.get(
        "system_messages.voting.result_summary",
        consensus="Yes"
    )
    assert summary
    assert "Yes" in summary or language is not SupportedLanguage.ENGLISH
