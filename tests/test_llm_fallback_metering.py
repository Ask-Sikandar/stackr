import pytest

from services.llm import FallbackLLMClient


class _FailingClient:
    def complete(self, prompt: str) -> str:
        raise RuntimeError("boom")

    def stream(self, prompt: str):
        raise RuntimeError("boom")
        yield ""


class _SuccessClient:
    def complete(self, prompt: str) -> str:
        return "ok"

    def stream(self, prompt: str):
        yield "ok"


def test_fallback_complete_emits_failure_and_fallback_events(monkeypatch):
    events = []

    def _capture(**kwargs):
        events.append(kwargs)
        return True

    monkeypatch.setattr("services.llm.record_usage_event", _capture)

    client = FallbackLLMClient(
        clients=[("private:openai", _FailingClient()), ("platform:gemini", _SuccessClient())],
        organization_id=7,
        project_id=9,
    )

    assert client.complete("hello") == "ok"

    event_types = [e["event_type"] for e in events]
    assert "llm.provider_failed" in event_types
    assert "llm.provider_used" in event_types
    assert "llm.fallback_used" in event_types


def test_fallback_complete_emits_all_failed_event(monkeypatch):
    events = []

    def _capture(**kwargs):
        events.append(kwargs)
        return True

    monkeypatch.setattr("services.llm.record_usage_event", _capture)

    client = FallbackLLMClient(
        clients=[("private:openai", _FailingClient()), ("platform:gemini", _FailingClient())],
        organization_id=7,
        project_id=9,
    )

    with pytest.raises(RuntimeError):
        client.complete("hello")

    event_types = [e["event_type"] for e in events]
    assert "llm.all_failed" in event_types


def test_fallback_stream_emits_provider_used_without_fallback(monkeypatch):
    events = []

    def _capture(**kwargs):
        events.append(kwargs)
        return True

    monkeypatch.setattr("services.llm.record_usage_event", _capture)

    client = FallbackLLMClient(
        clients=[("platform:openai", _SuccessClient())],
        organization_id=7,
        project_id=9,
    )

    assert "".join(client.stream("hello")) == "ok"

    event_types = [e["event_type"] for e in events]
    assert "llm.provider_used" in event_types
    assert "llm.fallback_used" not in event_types
