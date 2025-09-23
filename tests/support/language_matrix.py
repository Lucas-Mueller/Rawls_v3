"""Language matrix utilities for parametrised multilingual testing."""
from __future__ import annotations

from typing import Iterable, List, Sequence

import pytest

from utils.language_manager import SupportedLanguage

ALL_LANGUAGES: Sequence[SupportedLanguage] = (
    SupportedLanguage.ENGLISH,
    SupportedLanguage.SPANISH,
    SupportedLanguage.MANDARIN,
)

# Default order used by smoke tests (English first for familiarity)
DEFAULT_LANGUAGE_MATRIX: Sequence[SupportedLanguage] = ALL_LANGUAGES


def language_ids(languages: Iterable[SupportedLanguage]) -> List[str]:
    """Return readable pytest ids for a sequence of languages."""
    return [language.name.lower() for language in languages]


def parametrize_languages(
    languages: Sequence[SupportedLanguage] = DEFAULT_LANGUAGE_MATRIX,
    *,
    ids: Sequence[str] | None = None,
):
    """Convenience wrapper around ``pytest.mark.parametrize`` for languages."""
    return pytest.mark.parametrize(
        "language",
        languages,
        ids=ids or language_ids(languages),
    )


def iter_languages(
    include: Sequence[SupportedLanguage] | None = None,
) -> Iterable[SupportedLanguage]:
    """Yield languages respecting the configured defaults."""
    if include:
        for language in include:
            yield language
        return
    for language in DEFAULT_LANGUAGE_MATRIX:
        yield language
