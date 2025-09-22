import pytest

from utils.language_manager import LanguageManager, SupportedLanguage


def test_translation_keys_available_for_supported_languages():
    manager = LanguageManager()
    for language in SupportedLanguage:
        manager.set_language(language)
        text = manager.get("common.principle_names.maximizing_floor")
        assert text


def test_missing_key_raises_key_error():
    manager = LanguageManager()
    manager.set_language(SupportedLanguage.ENGLISH)
    with pytest.raises(KeyError):
        manager.get("nonexistent.section.key")
