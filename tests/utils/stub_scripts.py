"""Helpers for loading scripted agent transcripts used by acceptance tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from .stubbed_runner import StubbedRunner

TRANSCRIPTS_ROOT = Path(__file__).parent.parent / "data" / "acceptance"


def load_transcript(name: str) -> Dict[str, List[str]]:
    """Load a transcript JSON file by name from `tests/data/acceptance/*`."""

    path = TRANSCRIPTS_ROOT / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Transcript '{name}' not found at {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Transcript files must contain an object keyed by agent name.")

    for agent, messages in data.items():
        if not isinstance(messages, list):
            raise ValueError(f"Transcript for agent '{agent}' must be a list of messages.")
    return data


def register_transcript(stubbed_runner: StubbedRunner, transcript: Dict[str, Iterable[str]]) -> None:
    """Register a transcript mapping agent name → iterable of messages."""

    for agent, messages in transcript.items():
        stubbed_runner.register(agent, messages)


def load_and_register(stubbed_runner: StubbedRunner, name: str) -> None:
    """Load a transcript by name and register it with the provided stubbed runner."""

    transcript = load_transcript(name)
    register_transcript(stubbed_runner, transcript)
