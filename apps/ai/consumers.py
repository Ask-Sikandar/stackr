"""
ChatConsumer — bidirectional WebSocket with real-time token streaming.

Message protocol (all JSON):
  Client → Server:
    { "type": "chat", "message": "...", "lead_id": "..." }

  Server → Client:
    { "type": "typing",  "status": true }          — LLM is thinking
    { "type": "stream",  "token": "word " }         — each streamed token
    { "type": "message", ...AgentResponse fields,
                         "lead_score": int }         — final structured response
    { "type": "error",   "message": "..." }         — something went wrong

Streaming flow:
1. Receive user message
2. Send typing indicator
3. Classify intent + retrieve context (fast — no LLM)
4. Stream Ollama tokens via agent.stream_message(), forwarding each over WS
5. After last token, build and send the final structured AgentResponse
6. Persist both message turns and update lead score in DB (async via sync_to_async)
"""

import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction

from apps.leads.models import IntentEvent, Lead
from services.agent import AgentResponse
from services.factory import get_agent
from services.interfaces.intent_classifier import Intent

from .models import Conversation, Message, MessageRole


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        self.lead_id = self.scope["url_route"]["kwargs"]["lead_id"]
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        pass

    async def receive(self, text_data: str) -> None:
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON")
            return

        if data.get("type") != "chat":
            return

        user_message = data.get("message", "").strip()
        if not user_message:
            await self._send_error("Empty message")
            return

        await self._handle_chat(user_message)

    # ------------------------------------------------------------------
    # Core chat handler
    # ------------------------------------------------------------------

    async def _handle_chat(self, user_message: str) -> None:
        # 1. Typing indicator
        await self._send_json({"type": "typing", "status": True})

        try:
            agent = await sync_to_async(get_agent)()
            full_content = ""
            final_response: AgentResponse | None = None

            # 2. Stream tokens from LLM
            async def _stream():
                nonlocal full_content, final_response
                # stream_message is a sync generator — wrap it
                gen = await sync_to_async(agent.stream_message)(user_message)
                # Iterate synchronously inside a thread
                for item in gen:
                    if isinstance(item, AgentResponse):
                        final_response = item
                    else:
                        full_content += item
                        await self.channel_layer.send(
                            self.channel_name,
                            {"type": "send_token", "token": item},
                        )

            await sync_to_async(_stream_sync)(agent, user_message, self)

        except Exception as exc:
            await self._send_json({"type": "typing", "status": False})
            await self._send_error(f"Assistant error: {exc}")
            return

        # 3. Persist & score
        if final_response:
            lead = await sync_to_async(_persist_and_score)(
                self.lead_id, user_message, final_response
            )
            # 4. Send final structured message
            await self._send_json(
                {
                    "type": "message",
                    **final_response.to_dict(),
                    "lead_score": lead.score,
                }
            )

        await self._send_json({"type": "typing", "status": False})

    # ------------------------------------------------------------------
    # WebSocket send helpers
    # ------------------------------------------------------------------

    async def send_token(self, event: dict) -> None:
        await self._send_json({"type": "stream", "token": event["token"]})

    async def _send_json(self, data: dict) -> None:
        await self.send(text_data=json.dumps(data))

    async def _send_error(self, message: str) -> None:
        await self._send_json({"type": "error", "message": message})


# ---------------------------------------------------------------------------
# Sync helpers (run in thread via sync_to_async)
# ---------------------------------------------------------------------------

def _stream_sync(agent, user_message: str, consumer: "ChatConsumer") -> tuple[str, AgentResponse | None]:
    """
    Iterates the sync generator from agent.stream_message().
    Sends each token via the consumer's channel layer synchronously.
    Returns (full_content, final_response).
    """
    import asyncio

    loop = asyncio.get_event_loop()
    full_content = ""
    final_response = None

    for item in agent.stream_message(user_message):
        if isinstance(item, AgentResponse):
            final_response = item
        else:
            full_content += item
            # Schedule a coroutine send on the event loop
            asyncio.run_coroutine_threadsafe(
                consumer._send_json({"type": "stream", "token": item}), loop
            )

    return full_content, final_response


@transaction.atomic
def _persist_and_score(lead_id: str, user_message: str, response: AgentResponse) -> Lead:
    lead, _ = Lead.objects.get_or_create(lead_id=lead_id)
    conv = lead.conversations.order_by("-started_at").first()
    if conv is None:
        conv = Conversation.objects.create(lead=lead)

    Message.objects.create(conversation=conv, role=MessageRole.USER, content=user_message)
    Message.objects.create(
        conversation=conv,
        role=MessageRole.ASSISTANT,
        content=response.content,
        intent=response.intent,
        sources=response.sources,
        components=response.components,
        handoff_triggered=response.handoff_triggered,
    )

    lead.score += response.lead_score_delta
    lead.last_intent = response.intent
    lead.save(update_fields=["score", "last_intent", "last_seen_at"])

    IntentEvent.objects.create(
        lead=lead,
        intent=response.intent,
        message_preview=user_message[:120],
        score_delta=response.lead_score_delta,
    )
    return lead
