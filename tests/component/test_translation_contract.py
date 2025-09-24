"""Contract-style checks for translation consistency."""
from __future__ import annotations

import pytest

from utils.language_manager import SupportedLanguage
from tests.support import build_language_manager


@pytest.mark.component
@pytest.mark.parametrize("language", [SupportedLanguage.ENGLISH, SupportedLanguage.SPANISH, SupportedLanguage.MANDARIN])
def test_principle_translations_present(language):
    manager = build_language_manager(language)
    keys = [
        "common.principle_names.maximizing_floor",
        "common.principle_names.maximizing_average",
    ]
    for key in keys:
        value = manager.get(key)
        assert value
        assert "missing" not in value.lower()
