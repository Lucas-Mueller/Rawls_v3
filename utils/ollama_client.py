"""Ollama AsyncOpenAI client helper."""
from __future__ import annotations

import os
import logging
from functools import lru_cache
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ollama_client() -> AsyncOpenAI:
    """Return a cached AsyncOpenAI client configured for Ollama."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    api_key = os.getenv("OLLAMA_API_KEY", "ollama")

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    logger.info("Initialized Ollama client for base URL %s", base_url)
    return client
