"""
Thin wrapper around Ollama's local API. Free, local inference - no API
key, no per-request cost. This is the 4th LLM use case in the app
(alongside intent parsing, personalization summarization, and the
nutrition-extraction fallback) - recipe generation, scoped deliberately:
the model picks ingredients and writes steps, but never does the macro
arithmetic itself (see app/core/recipe_generation.py).
"""

from __future__ import annotations

import json

import requests

from app.core.config import settings


class OllamaError(Exception):
    pass


def call_ollama(prompt: str, model: str | None = None, timeout: int = 60) -> str:
    """
    Sends a prompt to the local Ollama server and returns the raw text
    response. Raises OllamaError with a clear message on any failure -
    connection refused (Ollama not running), timeout, etc. - rather than
    letting a raw requests exception bubble up.
    """
    url = f"{settings.ollama_url}/api/generate"
    payload = {
        "model": model or settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
    except requests.ConnectionError as e:
        raise OllamaError(
            f"Could not connect to Ollama at {settings.ollama_url}. "
            f"Is Ollama running? (ollama serve, or open the Ollama app)"
        ) from e
    except requests.Timeout as e:
        raise OllamaError(f"Ollama request timed out after {timeout}s.") from e
    except requests.HTTPError as e:
        raise OllamaError(f"Ollama returned an error: {e}") from e

    data = resp.json()
    return data.get("response", "")


def parse_json_response(raw_text: str) -> dict:
    """
    LLM responses sometimes wrap JSON in markdown code fences or add
    stray text before/after - strip common wrapping before parsing.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise OllamaError(f"Ollama did not return valid JSON: {e}\nRaw response: {raw_text[:500]}") from e
