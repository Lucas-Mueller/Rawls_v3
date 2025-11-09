"""Language matrix utilities for parametrised multilingual testing."""
from __future__ import annotations

from typing import Iterable, List, Sequence, Optional, Union

import pytest

from utils.language_manager import SupportedLanguage

ALL_LANGUAGES: Sequence[SupportedLanguage] = (
    SupportedLanguage.ENGLISH,
    SupportedLanguage.SPANISH,
    SupportedLanguage.MANDARIN,
)

LANGUAGE_OVERRIDE: Sequence[SupportedLanguage] | None = None
PRIMARY_OVERRIDE: SupportedLanguage | None = None


def _resolve_primary_language() -> SupportedLanguage:
    if PRIMARY_OVERRIDE is not None:
        return PRIMARY_OVERRIDE
    if LANGUAGE_OVERRIDE:
        return LANGUAGE_OVERRIDE[0]
    return SupportedLanguage.ENGLISH


def _default_language_matrix() -> Sequence[SupportedLanguage]:
    if LANGUAGE_OVERRIDE:
        return LANGUAGE_OVERRIDE
    return (_resolve_primary_language(),)


# Default order used by smoke tests (single locale unless explicitly expanded)
DEFAULT_LANGUAGE_MATRIX: Sequence[SupportedLanguage] = tuple()


def configure_language_options(
    *,
    languages: Sequence[SupportedLanguage] | None = None,
    primary: SupportedLanguage | None = None,
) -> None:
    """Configure language overrides supplied via pytest options."""

    global LANGUAGE_OVERRIDE, PRIMARY_OVERRIDE, DEFAULT_LANGUAGE_MATRIX

    LANGUAGE_OVERRIDE = tuple(languages) if languages else None
    PRIMARY_OVERRIDE = primary
    DEFAULT_LANGUAGE_MATRIX = _default_language_matrix()


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


def _get_smart_language_selection(
    full_multilingual: bool = False,
    primary_plus_one: bool = True,
    single_language: bool = False
) -> Sequence[SupportedLanguage]:
    """Get intelligent language selection based on test importance flags."""
    if LANGUAGE_OVERRIDE:
        return LANGUAGE_OVERRIDE

    if full_multilingual:
        return ALL_LANGUAGES
    if single_language:
        return (_resolve_primary_language(),)
    if primary_plus_one:
        primary = _resolve_primary_language()
        other_languages = [lang for lang in ALL_LANGUAGES if lang != primary]
        if other_languages:
            secondary = (
                SupportedLanguage.SPANISH
                if SupportedLanguage.SPANISH in other_languages
                else other_languages[0]
            )
            return (primary, secondary)
        return (primary,)
    return _default_language_matrix()


def smart_parametrize_languages(
    full_multilingual: bool = False,
    primary_plus_one: bool = True,
    single_language: bool = False,
    *,
    ids: Optional[Sequence[str]] = None,
):
    """Intelligent language selection based on test importance flags."""
    selected_languages = _get_smart_language_selection(
        full_multilingual=full_multilingual,
        primary_plus_one=primary_plus_one,
        single_language=single_language,
    )

    return pytest.mark.parametrize(
        "language",
        selected_languages,
        ids=ids or language_ids(selected_languages),
    )


configure_language_options()


def current_language_matrix() -> Sequence[SupportedLanguage]:
    """Return the currently configured language matrix."""

    return _default_language_matrix()


# Legacy alias for backward compatibility
def parametrize_languages_smart(
    level: str = "balanced",
    *,
    ids: Optional[Sequence[str]] = None,
):
    """Legacy interface for smart language parametrization."""
    if level == "minimal":
        return smart_parametrize_languages(single_language=True, ids=ids)
    if level == "comprehensive":
        return smart_parametrize_languages(full_multilingual=True, ids=ids)
    return smart_parametrize_languages(primary_plus_one=True, ids=ids)


def get_language_count_for_mode(mode: str) -> int:
    """Get expected language count for a given test mode."""
    if mode == "ultra_fast":
        return 1
    if mode == "dev":
        return 2
    if mode == "ci":
        return 2
    if mode == "full":
        return len(ALL_LANGUAGES)
    return 2
