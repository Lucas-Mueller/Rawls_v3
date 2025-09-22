"""Deterministic stub implementation for `agents.Runner.run` used in tests."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Iterable, Optional


@dataclass
class StubResponse:
    """Simple container matching the subset of Runner results consumed by tests."""

    final_output: str
    metadata: Optional[dict] = None


class StubbedRunner:
    """Deterministic response queue keyed by agent name."""

    def __init__(self) -> None:
        self._scripts: Dict[str, Deque[str]] = {}
        self._default_queue: Deque[str] = deque()

    def register(self, agent_name: str, responses: Iterable[str]) -> None:
        """Register scripted responses for an agent."""

        queue = deque(responses)
        self._scripts[agent_name.lower()] = queue

    def register_default(self, responses: Iterable[str]) -> None:
        """Register fallback responses consumed when no agent-specific script exists."""

        self._default_queue = deque(responses)

    async def run(self, agent: Any, prompt: str, context: Optional[dict] = None) -> StubResponse:
        """Return the next scripted response, raising when a queue is exhausted."""

        agent_name = getattr(agent, "name", None) or "__default__"
        key = agent_name.lower() if isinstance(agent_name, str) else "__default__"

        queue = self._scripts.get(key, self._default_queue)
        if not queue:
            raise RuntimeError(
                f"StubbedRunner script exhausted for agent '{agent_name}'. "
                "Register additional responses via stubbed_runner.register()."
            )

        return StubResponse(final_output=queue.popleft())

    # Convenience for synchronous usage in unit tests
    def run_sync(self, agent: Any, prompt: str, context: Optional[dict] = None) -> StubResponse:
        """Synchronous wrapper to support non-async code paths in unit tests."""

        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.run(agent, prompt, context))
