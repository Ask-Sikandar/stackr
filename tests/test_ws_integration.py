import uuid

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.ai.models import Message
from apps.leads.models import Lead
from config.asgi import application
from services.agent import AgentResponse
from tests.conftest import requires_postgres


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ws_chat_with_project_token_uses_project_routing(
    sample_user,
    sample_project,
    monkeypatch,
):
    capture = {}
    llm_marker = object()

    def _set_custom_instructions() -> None:
        sample_project.organization.custom_instructions = "Use enterprise tone."
        sample_project.organization.save(update_fields=["custom_instructions"])
        sample_project.custom_instructions = "Respond with short bullets only."
        sample_project.save(update_fields=["custom_instructions"])

    await sync_to_async(_set_custom_instructions)()

    class FakeAgent:
        def stream_message(self, message, llm_client=None, custom_instructions=None):
            capture["message"] = message
            capture["llm_client"] = llm_client
            capture["custom_instructions"] = custom_instructions
            yield "hello "
            yield AgentResponse(
                message_id="msg-1",
                content="assistant-final",
                intent="pricing",
                sources=[],
                components=[],
                lead_score_delta=10,
                handoff_triggered=False,
            )

    import apps.ai.consumers as consumers

    monkeypatch.setattr(consumers, "get_agent", lambda: FakeAgent())
    monkeypatch.setattr(consumers, "get_llm_client_for_project", lambda project: llm_marker)

    lead_id = str(uuid.uuid4())
    token = str(AccessToken.for_user(sample_user))
    communicator = WebsocketCommunicator(application, f"/ws/chat/{lead_id}/")

    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "type": "chat",
            "message": "Need a quote",
            "lead_id": lead_id,
            "project_id": sample_project.id,
            "access_token": token,
        }
    )

    packets: list[dict] = []
    for _ in range(12):
        packet = await communicator.receive_json_from(timeout=1)
        packets.append(packet)
        if packet.get("type") == "message":
            break

    await communicator.disconnect()

    final_packets = [p for p in packets if p.get("type") == "message"]
    assert final_packets
    final = final_packets[-1]
    assert final["project_id"] == sample_project.id
    assert final["content"] == "assistant-final"
    assert any(p.get("type") == "typing" and p.get("status") is True for p in packets)
    assert any(p.get("type") == "typing" and p.get("status") is False for p in packets)
    assert any(p.get("type") == "stream" for p in packets)

    assert capture["message"] == "Need a quote"
    assert capture["llm_client"] is llm_marker
    assert capture["custom_instructions"] is not None
    assert "[Organization Instructions]" in capture["custom_instructions"]
    assert "Use enterprise tone." in capture["custom_instructions"]
    assert "[Project Instructions]" in capture["custom_instructions"]
    assert "Respond with short bullets only." in capture["custom_instructions"]

    def _lead_snapshot() -> tuple[int | None, int, int]:
        lead = Lead.objects.get(lead_id=lead_id)
        msg_count = Message.objects.filter(conversation__lead=lead).count()
        return lead.project_id, lead.score, msg_count

    project_id, score, msg_count = await sync_to_async(_lead_snapshot)()
    assert project_id == sample_project.id
    assert score == 10
    assert msg_count == 2


@requires_postgres
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ws_chat_rejects_partial_tenant_payload(sample_project):
    lead_id = str(uuid.uuid4())
    communicator = WebsocketCommunicator(application, f"/ws/chat/{lead_id}/")

    connected, _ = await communicator.connect()
    assert connected

    await communicator.send_json_to(
        {
            "type": "chat",
            "message": "Need pricing",
            "lead_id": lead_id,
            "project_id": sample_project.id,
        }
    )

    packet = await communicator.receive_json_from(timeout=1)
    await communicator.disconnect()

    assert packet["type"] == "error"
    assert "Both project_id and access_token" in packet["message"]

    exists = await sync_to_async(lambda: Lead.objects.filter(lead_id=lead_id).exists())()
    assert exists is False