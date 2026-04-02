"""
OllamaLLMClient — HTTP client for the local Ollama inference server.

Ollama exposes a simple HTTP API:
  POST /api/generate  {"model": "...", "prompt": "...", "stream": bool}

Streaming mode returns NDJSON: one JSON object per line, each with a "response"
field containing the next token(s).  We iterate the response body line-by-line
and yield tokens — the WebSocket consumer forwards each token to the client.

httpx is used (not requests) because the WS consumer is async and we need
an async-compatible client for stream().
"""

import json
from collections.abc import Generator

import httpx
from django.conf import settings

from .interfaces.llm_client import ILLMClient


class OllamaLLMClient(ILLMClient):
    def __init__(self) -> None:
        self._base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        self._model = getattr(settings, "OLLAMA_MODEL", "llama3.2:3b")

    # ------------------------------------------------------------------
    # Blocking complete — used by REST endpoint
    # ------------------------------------------------------------------

    def complete(self, prompt: str) -> str:
        response = httpx.post(
            f"{self._base_url}/api/generate",
            json={"model": self._model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json().get("response", "")

    # ------------------------------------------------------------------
    # Streaming — used by WebSocket consumer
    # ------------------------------------------------------------------

    def stream(self, prompt: str) -> Generator[str, None, None]:
        with httpx.stream(
            "POST",
            f"{self._base_url}/api/generate",
            json={"model": self._model, "prompt": prompt, "stream": True},
            timeout=120,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done", False):
                    break
