"""Language matrix utilities for parametrised multilingual testing."""
from __future__ import annotations

import os
from typing import Iterable, List, Sequence, Optional, Union
from functools import wraps

import pytest

from utils.language_manager import SupportedLanguage

ALL_LANGUAGES: Sequence[SupportedLanguage] = (
    SupportedLanguage.ENGLISH,
    SupportedLanguage.SPANISH,
    SupportedLanguage.MANDARIN,
)

PRIMARY_LANGUAGE_ENV = "LIVE_PRIMARY_LANGUAGE"
ALL_LANGUAGES_ENV = "LIVE_LANGUAGES"
DEVELOPMENT_MODE_ENV = "DEVELOPMENT_MODE"
FULL_INTEGRATION_TESTS_ENV = "FULL_INTEGRATION_TESTS"
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


def _is_development_mode() -> bool:
    """Check if we're in development mode (default True)."""
    raw = os.getenv(DEVELOPMENT_MODE_ENV, "1")  # Default to development mode
    return raw.strip().lower() in TRUTHY


def _is_full_integration_enabled() -> bool:
    """Check if full integration tests are enabled."""
    raw = os.getenv(FULL_INTEGRATION_TESTS_ENV, "0")  # Default to disabled
    return raw.strip().lower() in TRUTHY


def _get_smart_language_selection(
    full_multilingual: bool = False,
    primary_plus_one: bool = True,
    single_language: bool = False
) -> Sequence[SupportedLanguage]:
    """Get intelligent language selection based on test importance and environment."""
    # Environment overrides take precedence
    if _use_all_languages() or _is_full_integration_enabled():
        return ALL_LANGUAGES

    if _is_development_mode() and not _is_full_integration_enabled():
        # In development mode, prefer minimal language sets unless explicitly requested
        if single_language or (not full_multilingual and not primary_plus_one):
            return (_resolve_primary_language(),)

    if full_multilingual:
        return ALL_LANGUAGES
    elif primary_plus_one:
        primary = _resolve_primary_language()
        # Select primary plus one other language (prefer Spanish for variety)
        other_languages = [lang for lang in ALL_LANGUAGES if lang != primary]
        if other_languages:
            # Prefer Spanish if available and not primary, otherwise first available
            secondary = (SupportedLanguage.SPANISH
                        if SupportedLanguage.SPANISH in other_languages
                        else other_languages[0])
            return (primary, secondary)
        else:
            return (primary,)
    elif single_language:
        return (_resolve_primary_language(),)
    else:
        # Default behavior - respect existing environment configuration
        return _default_language_matrix()


def smart_parametrize_languages(
    full_multilingual: bool = False,
    primary_plus_one: bool = True,
    single_language: bool = False,
    *,
    ids: Optional[Sequence[str]] = None,
):
    """Intelligent language selection based on test importance and environment.

    This decorator provides intelligent language parametrization that adapts based on:
    - Test importance level (full_multilingual > primary_plus_one > single_language)
    - Environment variables (DEVELOPMENT_MODE, FULL_INTEGRATION_TESTS, LIVE_LANGUAGES)
    - Performance optimization for development workflows

    Args:
        full_multilingual: Test all 3 languages (English, Spanish, Mandarin)
                          Use for critical integration tests only
        primary_plus_one: Test primary language + one other (default: True)
                         Good balance of coverage and speed for component tests
        single_language: Test only primary language
                        Use for development, unit tests, or when multilingual coverage isn't critical
        ids: Custom test IDs (optional)

    Environment Variables:
        DEVELOPMENT_MODE=1: Prefer minimal language sets (default)
        FULL_INTEGRATION_TESTS=1: Force full multilingual testing
        LIVE_LANGUAGES=1: Force all languages (existing behavior)
        LIVE_PRIMARY_LANGUAGE=<lang>: Set primary language

    Usage Examples:
        @smart_parametrize_languages(full_multilingual=True)  # 3 languages
        def test_critical_integration(language, harness):
            pass

        @smart_parametrize_languages(primary_plus_one=True)  # 2 languages (default)
        def test_component_behavior(language, harness):
            pass

        @smart_parametrize_languages(single_language=True)  # 1 language
        def test_unit_logic(language, harness):
            pass
    """
    selected_languages = _get_smart_language_selection(
        full_multilingual=full_multilingual,
        primary_plus_one=primary_plus_one,
        single_language=single_language
    )

    return pytest.mark.parametrize(
        "language",
        selected_languages,
        ids=ids or language_ids(selected_languages),
    )


# Legacy alias for backward compatibility
def parametrize_languages_smart(
    level: str = "balanced",
    *,
    ids: Optional[Sequence[str]] = None,
):
    """Legacy interface for smart language parametrization.

    Args:
        level: "minimal", "balanced", or "comprehensive"
        ids: Custom test IDs (optional)
    """
    if level == "minimal":
        return smart_parametrize_languages(single_language=True, ids=ids)
    elif level == "comprehensive":
        return smart_parametrize_languages(full_multilingual=True, ids=ids)
    else:  # balanced
        return smart_parametrize_languages(primary_plus_one=True, ids=ids)


def get_language_count_for_mode(mode: str) -> int:
    """Get expected language count for a given test mode.

    Args:
        mode: Test mode ("ultra_fast", "dev", "ci", "full")

    Returns:
        Number of languages that should be tested in this mode
    """
    if mode == "ultra_fast":
        return 1
    elif mode == "dev":
        return 2 if not _is_development_mode() else 1
    elif mode == "ci":
        return 2
    elif mode == "full":
        return 3
    else:
        return 2  # Default to balanced
