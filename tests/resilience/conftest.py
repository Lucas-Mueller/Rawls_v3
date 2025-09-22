"""Shared fixtures supporting resilience scenarios across managers and services."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import AsyncIterator

import pytest


@pytest.fixture
def failing_language_manager():
    """Language manager stub that always fails, simulating missing translations."""

    class _FailingLanguageManager:
        def get(self, key: str, **kwargs):  # pragma: no cover - intentional failure path
            raise KeyError(key)

    return _FailingLanguageManager()


@pytest.fixture
def timeout_utility_agent():
    """Utility agent stub whose parsing helpers raise timeouts on first invocation."""

    class _TimeoutUtilityAgent(SimpleNamespace):
        async def parse_principle_choice_enhanced(self, *_args, **_kwargs):
            raise asyncio.TimeoutError("simulated utility timeout")

        async def parse_principle_ranking_enhanced(self, *_args, **_kwargs):
            raise asyncio.TimeoutError("simulated ranking timeout")

    return _TimeoutUtilityAgent()


@pytest.fixture
def malformed_json_transcript() -> str:
    """Provides malformed JSON content used to test robust parsing paths."""

    return '{"principle": "maximizing_average", "constraint_amount": }'
