"""Pytest suite validating translation completeness and consistency."""
from __future__ import annotations

from typing import Dict, Any, Set

import pytest

from utils.language_manager import LanguageManager, SupportedLanguage

pytestmark = pytest.mark.contracts


@pytest.fixture(scope="module")
def loaded_translations() -> Dict[SupportedLanguage, Dict[str, Any]]:
    manager = LanguageManager()
    translations = {}
    for language in SupportedLanguage:
        translations[language] = manager.load_language(language)
    return translations


def test_principle_names_consistency(loaded_translations):
    expected_principles = {
        "maximizing_floor",
        "maximizing_average",
        "maximizing_average_floor_constraint",
        "maximizing_average_range_constraint",
    }

    for language, translations in loaded_translations.items():
        principle_names = translations["common"]["principle_names"]
        assert set(principle_names.keys()) == expected_principles

        if language == SupportedLanguage.MANDARIN:
            assert principle_names["maximizing_floor"] == "最大化最低收入"
            assert principle_names["maximizing_average"] == "最大化平均收入"
            assert principle_names["maximizing_average_floor_constraint"] == "在最低收入约束条件下最大化平均收入"
            assert principle_names["maximizing_average_range_constraint"] == "在范围约束条件下最大化平均收入"
        elif language == SupportedLanguage.SPANISH:
            assert principle_names["maximizing_floor"] == "Maximizar el ingreso mínimo"
            assert principle_names["maximizing_average"] == "Maximizar el ingreso promedio"

        if language != SupportedLanguage.ENGLISH:
            forbidden_terms = {
                SupportedLanguage.MANDARIN: ["地板"],
                SupportedLanguage.SPANISH: ["suelo"],
            }.get(language, [])
            for key, value in principle_names.items():
                if "floor" in key:
                    for forbidden in forbidden_terms:
                        assert forbidden.lower() not in value.lower()


def _collect_keys(data: Dict[str, Any], prefix: str = "") -> Set[str]:
    keys: Set[str] = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(_collect_keys(value, full_key))
    return keys


def test_translation_completeness(loaded_translations):
    english = loaded_translations[SupportedLanguage.ENGLISH]
    english_keys = _collect_keys(english)

    for language in [SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN]:
        language_keys = _collect_keys(loaded_translations[language])
        missing = english_keys - language_keys
        extra = language_keys - english_keys
        assert not missing, f"Missing keys in {language.value}: {missing}"
        assert not extra, f"Extra keys in {language.value}: {extra}"


def _assert_no_empty(translations: Any, language_name: str, path: str = "") -> None:
    if isinstance(translations, dict):
        for key, value in translations.items():
            current_path = f"{path}.{key}" if path else key
            _assert_no_empty(value, language_name, current_path)
    elif isinstance(translations, str):
        assert translations.strip(), f"Empty translation in {language_name} at {path}"


def test_no_empty_translations(loaded_translations):
    for language, translations in loaded_translations.items():
        _assert_no_empty(translations, language.value)


def test_principle_consistency_in_prompts(loaded_translations):
    translations = loaded_translations[SupportedLanguage.MANDARIN]
    ranking_prompt = translations["prompts"]["phase1_round0_initial_ranking"]
    expected_terms = [
        "最大化最低收入",
        "最大化平均收入",
        "在最低收入约束条件下最大化平均收入",
        "在范围约束条件下最大化平均收入",
    ]
    for term in expected_terms:
        assert term in ranking_prompt
    assert "最大限度地利用地板" not in ranking_prompt
    assert "最大化平均值" not in ranking_prompt
