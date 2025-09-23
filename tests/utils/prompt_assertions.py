"""Helper assertions for prompt validation used in tests."""
from __future__ import annotations

from typing import Iterable, Union


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


def assert_prompt_key_elements(prompt: str, key_elements: Iterable[str]) -> None:
    """Assert that all key elements appear in the prompt (order-independent).

    This is useful for testing prompt content without being brittle to exact formatting,
    word order, or minor phrasing changes. Each element should be a meaningful fragment
    that indicates the prompt contains the expected semantic content.

    Args:
        prompt: The prompt text to validate
        key_elements: Key terms/phrases that should be present in the prompt

    Example:
        assert_prompt_key_elements(result, [
            "formal voting",
            "consensus",
            "justice principle",
            "1 for Yes",
            "0 for No"
        ])
    """
    missing_elements = []
    for element in key_elements:
        if element not in prompt:
            missing_elements.append(element)

    if missing_elements:
        raise AssertionError(
            f"Prompt missing key elements: {missing_elements}\nPrompt: {prompt}"
        )


def assert_multilingual_equivalence(prompt: str, key_terms: Iterable[str], language: str = "unknown") -> None:
    """Assert that multilingual prompts contain equivalent key terms.

    This validates that translated prompts contain the essential semantic content
    without requiring exact string matches across languages.

    Args:
        prompt: The prompt text to validate
        key_terms: Essential terms/concepts that should be present
        language: Language identifier for better error messages

    Example:
        # English
        assert_multilingual_equivalence(result, ["voting", "consensus", "Yes", "No"], "English")
        # Spanish
        assert_multilingual_equivalence(result, ["votación", "consenso", "Sí", "No"], "Spanish")
    """
    missing_terms = []
    for term in key_terms:
        if term not in prompt:
            missing_terms.append(term)

    if missing_terms:
        raise AssertionError(
            f"{language} prompt missing key terms: {missing_terms}\nPrompt: {prompt}"
        )


def assert_memory_content_reasonable(content: str, max_reasonable_length: int = None) -> None:
    """Assert that memory content is reasonable without exact character counting.

    This validates memory content structure and length reasonableness without
    being brittle to exact character counts or minor formatting changes.

    Args:
        content: Memory content to validate
        max_reasonable_length: Optional maximum length check (flexible threshold)

    Example:
        assert_memory_content_reasonable(result, max_reasonable_length=50000)
    """
    if not content or not content.strip():
        raise AssertionError("Memory content is empty or contains only whitespace")

    # Check for reasonable length if specified
    if max_reasonable_length and len(content) > max_reasonable_length:
        raise AssertionError(
            f"Memory content length ({len(content)}) exceeds reasonable maximum ({max_reasonable_length})"
        )

    # Basic structure validation - should have some meaningful content
    if len(content.strip()) < 10:
        raise AssertionError(f"Memory content too short to be meaningful: {content!r}")


def assert_prompt_structure_preserved(prompt: str, expected_sections: Iterable[str]) -> None:
    """Assert that prompt maintains expected structural sections.

    This validates that prompts contain expected structural elements without
    being brittle to exact content or formatting.

    Args:
        prompt: The prompt text to validate
        expected_sections: Section headers or markers that should be present

    Example:
        assert_prompt_structure_preserved(result, [
            "Round", "Your statement:", "Internal reasoning:"
        ])
    """
    missing_sections = []
    for section in expected_sections:
        if section not in prompt:
            missing_sections.append(section)

    if missing_sections:
        raise AssertionError(
            f"Prompt missing expected sections: {missing_sections}\nPrompt: {prompt}"
        )
