from types import SimpleNamespace

from services import metering


class _DummyUsageManager:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)


class _FailingUsageManager:
    def create(self, **kwargs):
        raise RuntimeError("db unavailable")


class _DummyProjectQuery:
    def __init__(self, organization_id: int | None):
        self.organization_id = organization_id

    def values_list(self, *args, **kwargs):
        return self

    def first(self):
        return self.organization_id


class _DummyProjectManager:
    def __init__(self, organization_id: int | None):
        self.organization_id = organization_id

    def filter(self, **kwargs):
        return _DummyProjectQuery(self.organization_id)


def test_record_usage_event_persists_when_org_is_given(monkeypatch):
    usage_manager = _DummyUsageManager()
    monkeypatch.setattr(metering, "UsageEvent", SimpleNamespace(objects=usage_manager))

    ok = metering.record_usage_event(
        event_type="chat.response",
        organization_id=7,
        project_id=9,
        quantity=3,
        metadata={"intent": "pricing"},
    )

    assert ok is True
    assert len(usage_manager.calls) == 1
    assert usage_manager.calls[0]["organization_id"] == 7
    assert usage_manager.calls[0]["project_id"] == 9
    assert usage_manager.calls[0]["quantity"] == 3


def test_record_usage_event_resolves_org_from_project(monkeypatch):
    usage_manager = _DummyUsageManager()
    monkeypatch.setattr(metering, "UsageEvent", SimpleNamespace(objects=usage_manager))
    monkeypatch.setattr(
        metering,
        "Project",
        SimpleNamespace(objects=_DummyProjectManager(organization_id=42)),
    )

    ok = metering.record_usage_event(
        event_type="ingestion.succeeded",
        project_id=22,
        quantity=5,
    )

    assert ok is True
    assert usage_manager.calls[0]["organization_id"] == 42
    assert usage_manager.calls[0]["project_id"] == 22


def test_record_usage_event_is_noop_without_org_or_project(monkeypatch):
    usage_manager = _DummyUsageManager()
    monkeypatch.setattr(metering, "UsageEvent", SimpleNamespace(objects=usage_manager))

    ok = metering.record_usage_event(event_type="chat.response")

    assert ok is False
    assert usage_manager.calls == []


def test_record_usage_event_swallows_persistence_errors(monkeypatch):
    monkeypatch.setattr(metering, "UsageEvent", SimpleNamespace(objects=_FailingUsageManager()))

    ok = metering.record_usage_event(
        event_type="chat.response",
        organization_id=1,
    )

    assert ok is False
