"""
Gemini API client using OpenAI-compatible endpoint.

This module provides integration of Google's Gemini API using their
OpenAI-compatible endpoint, allowing seamless use with the OpenAI Agents SDK.

Based on: https://ai.google.dev/gemini-api/docs/openai
"""

import os
import logging
from functools import lru_cache
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_gemini_client() -> AsyncOpenAI:
    """
    Get singleton Gemini client using OpenAI-compatible endpoint.

    Returns:
        AsyncOpenAI client configured for Gemini

    Raises:
        ValueError: If GEMINI_API_KEY is not set
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable not set. "
            "Please set it to use Gemini models."
        )

    # Use OpenAI client with Gemini's OpenAI-compatible endpoint
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    logger.info("Successfully initialized Gemini client with OpenAI-compatible endpoint")
    return client


def is_gemini_available() -> bool:
    """
    Check if Gemini API is available and configured.

    Returns:
        True if Gemini can be used, False otherwise
    """
    return os.getenv("GEMINI_API_KEY") is not None