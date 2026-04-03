"""
LLM clients and fallback router.

Supported providers:
- Ollama (local)
- OpenAI (chat completions API)
- Gemini (generateContent API)

FallbackLLMClient tries providers in order and automatically falls back if the
current provider fails. This enables project/org-level private keys with
platform-level backup providers.
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


class OpenAILLMClient(ILLMClient):
    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self._api_key = api_key
        self._model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        self._base_url = (base_url or getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self._timeout = timeout or int(getattr(settings, "LLM_TIMEOUT_SECONDS", 120))

    def complete(self, prompt: str) -> str:
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    def stream(self, prompt: str) -> Generator[str, None, None]:
        content = self.complete(prompt)
        if content:
            yield content


class GeminiLLMClient(ILLMClient):
    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required.")
        self._api_key = api_key
        self._model = model or getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        self._base_url = (base_url or getattr(settings, "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")).rstrip("/")
        self._timeout = timeout or int(getattr(settings, "LLM_TIMEOUT_SECONDS", 120))

    def complete(self, prompt: str) -> str:
        response = httpx.post(
            f"{self._base_url}/models/{self._model}:generateContent",
            params={"key": self._api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    def stream(self, prompt: str) -> Generator[str, None, None]:
        content = self.complete(prompt)
        if content:
            yield content


class FallbackLLMClient(ILLMClient):
    """
    Tries configured providers in order until one succeeds.
    """

    def __init__(self, clients: list[tuple[str, ILLMClient]]) -> None:
        if not clients:
            raise ValueError("At least one LLM client is required for fallback routing.")
        self._clients = clients

    def complete(self, prompt: str) -> str:
        errors: list[str] = []
        for label, client in self._clients:
            try:
                return client.complete(prompt)
            except Exception as exc:  # pragma: no cover - provider-specific failures
                errors.append(f"{label}: {exc}")
        raise RuntimeError("All LLM providers failed: " + " | ".join(errors))

    def stream(self, prompt: str) -> Generator[str, None, None]:
        errors: list[str] = []
        for label, client in self._clients:
            try:
                yielded = False
                for token in client.stream(prompt):
                    yielded = True
                    yield token
                if not yielded:
                    content = client.complete(prompt)
                    if content:
                        yield content
                return
            except Exception as exc:  # pragma: no cover - provider-specific failures
                errors.append(f"{label}: {exc}")
        raise RuntimeError("All LLM providers failed: " + " | ".join(errors))
