"""Language matrix utilities for parametrised multilingual testing."""
from __future__ import annotations

import os
from typing import Iterable, List, Sequence

import pytest

from utils.language_manager import SupportedLanguage

ALL_LANGUAGES: Sequence[SupportedLanguage] = (
    SupportedLanguage.ENGLISH,
    SupportedLanguage.SPANISH,
    SupportedLanguage.MANDARIN,
)

PRIMARY_LANGUAGE_ENV = "LIVE_PRIMARY_LANGUAGE"
ALL_LANGUAGES_ENV = "LIVE_LANGUAGES"
TRUTHY = {"1", "true", "yes", "on", "all"}


def _resolve_primary_language() -> SupportedLanguage:
    raw = os.getenv(PRIMARY_LANGUAGE_ENV)
    if not raw:
        return SupportedLanguage.ENGLISH
    normalized = raw.strip().lower()
    for language in SupportedLanguage:
        if language.value.lower() == normalized or language.name.lower() == normalized:
            return language
    return SupportedLanguage.ENGLISH


def _use_all_languages() -> bool:
    raw = os.getenv(ALL_LANGUAGES_ENV)
    if raw is None:
        return False
    return raw.strip().lower() in TRUTHY


def _default_language_matrix() -> Sequence[SupportedLanguage]:
    if _use_all_languages():
        return ALL_LANGUAGES
    primary = _resolve_primary_language()
    return (primary,)


# Default order used by smoke tests (single locale unless explicitly expanded)
DEFAULT_LANGUAGE_MATRIX: Sequence[SupportedLanguage] = _default_language_matrix()


def language_ids(languages: Iterable[SupportedLanguage]) -> List[str]:
    """Return readable pytest ids for a sequence of languages."""
    return [language.name.lower() for language in languages]


def parametrize_languages(
    languages: Sequence[SupportedLanguage] | None = None,
    *,
    ids: Sequence[str] | None = None,
):
    """Convenience wrapper around ``pytest.mark.parametrize`` for languages."""
    selected = languages or _default_language_matrix()
    return pytest.mark.parametrize(
        "language",
        selected,
        ids=ids or language_ids(selected),
    )


def iter_languages(
    include: Sequence[SupportedLanguage] | None = None,
) -> Iterable[SupportedLanguage]:
    """Yield languages respecting the configured defaults."""
    if include:
        for language in include:
            yield language
        return
    for language in _default_language_matrix():
        yield language
