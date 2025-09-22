"""Contract tests for `MemoryService`."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.services.memory_service import MemoryService, MemoryEventType
from config.phase2_settings import Phase2Settings

pytestmark = pytest.mark.contracts


@dataclass
class StubLanguageManager:
    calls: list

    def get(self, key: str, **kwargs) -> str:
        self.calls.append((key, kwargs))
        if key == "missing":
            raise KeyError(key)
        return key.format(**kwargs) if kwargs else key


class StubUtilityAgent:
    async def parse_principle_ranking_enhanced(self, text_response: str):  # pragma: no cover - unused in tests
        raise NotImplementedError


@pytest.fixture
def language_manager():
    return StubLanguageManager(calls=[])


@pytest.fixture
def memory_service(language_manager):
    settings = Phase2Settings.get_default()
    service = MemoryService(language_manager=language_manager, utility_agent=StubUtilityAgent(), settings=settings)
    return service


def test_apply_content_truncation(memory_service):
    long_text = "A" * 500
    truncated = memory_service.apply_content_truncation(long_text, MemoryEventType.DISCUSSION_PUBLIC_MESSAGE)
    assert len(truncated) <= memory_service.statement_max_chars


def test_get_localized_message_fallback(memory_service, language_manager):
    message = memory_service._get_localized_message("missing")
    assert message == "[MISSING: missing]"
    assert language_manager.calls[-1][0] == "missing"
*** End Patch
