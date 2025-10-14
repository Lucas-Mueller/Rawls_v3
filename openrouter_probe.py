"""Quick probe script to inspect raw OpenRouter responses for specific models.

Usage:
    python openrouter_probe.py deepseek/deepseek-v3.2-exp

Environment:
    Requires OPENROUTER_API_KEY to be set (same credential the project uses).
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import httpx


API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MESSAGES = [
    {"role": "system", "content": "You are a laconic assistant."},
    {
        "role": "user",
        "content": (
            "Please respond with one short sentence summarizing why justice matters "
            "in society."
        ),
    },
]


async def fetch_raw_response(model: str, stream: bool = False) -> None:
    """Call OpenRouter directly and dump headers/body to stdout."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY must be set to call OpenRouter.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Keep a neutral user agent so we can differentiate from the main runner.
        "User-Agent": "RawlsV3/OpenRouterProbe",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": DEFAULT_MESSAGES,
        "temperature": 0.0,
        # Mirror the non-streaming calls in the main pipeline.
        "stream": stream,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.post(API_URL, headers=headers, json=payload)

    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Headers: {dict(response.headers)}")

    body_preview = response.text[:2000]
    print("Body preview:")
    print(body_preview)

    try:
        parsed = response.json()
    except Exception as exc:  # noqa: BLE001
        print(f"\nJSON parsing failed: {exc!r}")
        return

    print("\nParsed JSON keys:", list(parsed.keys()))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python openrouter_probe.py <model-name> [--stream]")
        raise SystemExit(1)

    model_name = sys.argv[1]
    use_stream = "--stream" in sys.argv[2:]

    asyncio.run(fetch_raw_response(model_name, stream=use_stream))


if __name__ == "__main__":
    main()
