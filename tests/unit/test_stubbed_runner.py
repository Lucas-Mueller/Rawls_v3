"""Unit tests for the shared `StubbedRunner` helper."""
from __future__ import annotations

import asyncio

import pytest

from tests.utils.stubbed_runner import StubResponse, StubbedRunner


@pytest.mark.asyncio
async def test_returns_registered_responses_in_order():
    runner = StubbedRunner()
    runner.register("AgentA", ["first", "second"])

    response1 = await runner.run(type("Agent", (), {"name": "AgentA"})(), "prompt")
    response2 = await runner.run(type("Agent", (), {"name": "AgentA"})(), "prompt")

    assert isinstance(response1, StubResponse)
    assert response1.final_output == "first"
    assert response2.final_output == "second"


@pytest.mark.asyncio
async def test_fallback_to_default_queue_when_agent_not_registered():
    runner = StubbedRunner()
    runner.register_default(["fallback"])

    response = await runner.run(type("Agent", (), {"name": "Unknown"})(), "prompt")
    assert response.final_output == "fallback"


@pytest.mark.asyncio
async def test_raises_when_queue_exhausted():
    runner = StubbedRunner()
    runner.register("AgentA", ["only"])

    await runner.run(type("Agent", (), {"name": "AgentA"})(), "prompt")
    with pytest.raises(RuntimeError):
        await runner.run(type("Agent", (), {"name": "AgentA"})(), "prompt")


def test_run_sync_wrapper():
    runner = StubbedRunner()
    runner.register("AgentA", ["sync"])

    agent = type("Agent", (), {"name": "AgentA"})()
    response = runner.run_sync(agent, "prompt")
    assert response.final_output == "sync"

    with pytest.raises(RuntimeError):
        runner.run_sync(agent, "prompt")
