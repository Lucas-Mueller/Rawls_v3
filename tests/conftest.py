"""Shared pytest fixtures for deterministic, tracing-free test runs."""
from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pytest

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional dependency
    np = None  # type: ignore

from tests.utils.stubbed_runner import StubResponse, StubbedRunner
from tests.utils.stub_scripts import TRANSCRIPTS_ROOT
from tests.integration.fixtures.experiment_fixtures import ExperimentTestFixture

@pytest.fixture(autouse=True)
def disable_tracing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tracing is disabled for every test run."""

    monkeypatch.setenv("OPENAI_AGENTS_DISABLE_TRACING", "1")
    monkeypatch.setenv("OPENAI_DISABLE_TRACING", "true")

    try:
        from agents import set_tracing_disabled  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        return

    set_tracing_disabled(True)


@pytest.fixture(autouse=True)
def stub_create_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace temperature-aware agent creation with lightweight stubs."""

    @dataclass
    class _StubAgent:
        name: str
        model: str
        instructions: str = ""

    async def _create_agent_with_temperature_retry(
        agent_class: Any,
        model_string: str,
        temperature: float,
        agent_kwargs: Optional[Dict[str, Any]] = None,
        cache: Any = None,
    ) -> Tuple[_StubAgent, Dict[str, Any]]:
        agent_kwargs = agent_kwargs or {}
        agent = _StubAgent(
            name=agent_kwargs.get("name", "Stub Agent"),
            model=model_string,
            instructions=agent_kwargs.get("instructions", ""),
        )
        info = {
            "model": model_string,
            "temperature": temperature,
            "from_cache": False,
            "supported": True,
        }
        return agent, info

    monkeypatch.setattr(
        "utils.dynamic_model_capabilities.create_agent_with_temperature_retry",
        _create_agent_with_temperature_retry,
    )

    @dataclass
    class _StubParticipant:
        config: Any
        name: str

        async def async_init(self) -> None:  # pragma: no cover - trivial stub
            return None

        async def update_memory(self, *args, **kwargs) -> str:
            return "Updated memory"

    async def _create_participants(
        configs: List[Any],
        experiment_config: Any = None,
        language_manager: Any = None,
        temperature_cache: Any = None,
    ) -> List[_StubParticipant]:
        return [_StubParticipant(config=c, name=c.name) for c in configs]

    monkeypatch.setattr(
        "experiment_agents.participant_agent.create_participant_agents_with_dynamic_temperature",
        _create_participants,
    )


@pytest.fixture(autouse=True)
def seed_rng(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide deterministic randomness for tests."""

    seed = int(os.getenv("PYTEST_RANDOM_SEED", "1337"))
    random.seed(seed)
    monkeypatch.setattr(random, "random", random.random)

    if np is not None:
        np.random.seed(seed)


@pytest.fixture
def stubbed_runner(monkeypatch: pytest.MonkeyPatch) -> StubbedRunner:
    """Patch `agents.Runner.run` with a deterministic scripted stub."""

    runner = StubbedRunner()

    async def _stub(agent: Any, prompt: str, context: Optional[dict] = None) -> StubResponse:
        return await runner.run(agent, prompt, context)

    monkeypatch.setattr("agents.Runner.run", _stub)
    return runner


@pytest.fixture
async def reset_asyncio_loop() -> None:
    """Ensure pending asyncio tasks do not leak across tests."""

    try:
        yield
    finally:
        loop = asyncio.get_event_loop()
        pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


@pytest.fixture
def transcripts_root() -> str:
    """Expose acceptance transcript directory to tests."""

    return str(TRANSCRIPTS_ROOT)


@pytest.fixture
def minimal_experiment_config():
    """Provide a minimal experiment configuration for unit tests."""

    return ExperimentTestFixture.create_minimal_config(num_agents=2)
