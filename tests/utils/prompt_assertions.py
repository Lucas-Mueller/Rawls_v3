"""Helper assertions for prompt validation used in tests."""
from __future__ import annotations

from typing import Iterable


def assert_prompt_contains(prompt: str, fragments: Iterable[str]) -> None:
    """Assert that all fragments appear in the prompt in order."""
    last_index = -1
    for fragment in fragments:
        idx = prompt.find(fragment)
        if idx == -1:
            raise AssertionError(f"Prompt missing fragment: {fragment!r}\nPrompt: {prompt}")
        if idx < last_index:
            raise AssertionError(
                f"Prompt fragment {fragment!r} appears out of order (index {idx} < {last_index})."
            )
        last_index = idx
