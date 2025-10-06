from __future__ import annotations
import os
from functools import lru_cache
from openai import AsyncOpenAI

@lru_cache(maxsize=1)
def get_openrouter_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )