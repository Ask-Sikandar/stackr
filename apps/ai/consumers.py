"""
ChatConsumer — bidirectional WebSocket with real-time token streaming.

Message protocol (all JSON):
  Client → Server:
        { "type": "chat", "message": "...", "lead_id": "...", "project_id": 1, "access_token": "..." }

  Server → Client:
    { "type": "typing",  "status": true }          — LLM is thinking
    { "type": "stream",  "token": "word " }         — each streamed token
    { "type": "message", ...AgentResponse fields,
                         "lead_score": int }         — final structured response
    { "type": "error",   "message": "..." }         — something went wrong

Streaming flow:
1. Receive user message
2. Send typing indicator
3. Run agent.stream_message() in a thread-pool executor (it's a sync generator)
4. Each token and the final AgentResponse are communicated back to the async
   consumer via asyncio.Queue — the queue is the bridge between the thread
   and the event loop.
5. Persist turns and update lead score synchronously in the executor thread.
"""

import asyncio
import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction
from django.contrib.auth.models import User
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.access import get_project_for_user
from apps.leads.models import IntentEvent, Lead
from services.agent import AgentHandler, AgentResponse
from services.factory import get_agent, get_llm_client_for_project

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

        project = None
        project_id = data.get("project_id")
        access_token = data.get("access_token")

        if project_id is not None or access_token is not None:
            try:
                project = await sync_to_async(_resolve_project_from_ws_payload)(project_id, access_token)
            except (ValueError, PermissionDenied) as exc:
                await self._send_error(str(exc))
                return

        await self._handle_chat(user_message, project=project)

    # ------------------------------------------------------------------
    # Core streaming handler
    # ------------------------------------------------------------------

    async def _handle_chat(self, user_message: str, project=None) -> None:
        await self._send_json({"type": "typing", "status": True})

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        # Run the sync streaming generator in a thread pool.
        # Tokens and the final AgentResponse are pushed into the queue
        # so the async consumer can forward them without blocking the event loop.
        def _run_stream() -> None:
            try:
                agent: AgentHandler = get_agent()
                llm_client = get_llm_client_for_project(project) if project is not None else None
                custom_instructions = project.custom_instructions if project is not None else None
                for item in agent.stream_message(
                    user_message,
                    llm_client=llm_client,
                    custom_instructions=custom_instructions,
                ):
                    if isinstance(item, AgentResponse):
                        asyncio.run_coroutine_threadsafe(
                            queue.put(("response", item)), loop
                        ).result()
                    else:
                        asyncio.run_coroutine_threadsafe(
                            queue.put(("token", item)), loop
                        ).result()
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(
                    queue.put(("error", str(exc))), loop
                ).result()
            finally:
                asyncio.run_coroutine_threadsafe(
                    queue.put(("done", None)), loop
                ).result()

        # Start the thread; don't await yet — drain the queue concurrently
        executor_future = loop.run_in_executor(None, _run_stream)

        final_response: AgentResponse | None = None

        try:
            while True:
                msg_type, data = await queue.get()

                if msg_type == "token":
                    await self._send_json({"type": "stream", "token": data})

                elif msg_type == "response":
                    final_response = data

                elif msg_type == "error":
                    await self._send_error(f"Assistant error: {data}")
                    break

                elif msg_type == "done":
                    break

        finally:
            await asyncio.wrap_future(executor_future)  # ensure thread is clean

        await self._send_json({"type": "typing", "status": False})

        if final_response:
            lead = await sync_to_async(_persist_and_score)(
                self.lead_id,
                user_message,
                final_response,
                project,
            )
            payload = {
                "type": "message",
                **final_response.to_dict(),
                "lead_score": lead.score,
            }
            if project is not None:
                payload["project_id"] = project.id
            await self._send_json(payload)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _send_json(self, data: dict) -> None:
        await self.send(text_data=json.dumps(data))

    async def _send_error(self, message: str) -> None:
        await self._send_json({"type": "error", "message": message})


# ---------------------------------------------------------------------------
# DB persistence — runs in thread via sync_to_async
# ---------------------------------------------------------------------------

@transaction.atomic
def _persist_and_score(lead_id: str, user_message: str, response: AgentResponse, project=None) -> Lead:
    if project is not None:
        lead, created = Lead.objects.get_or_create(lead_id=lead_id, defaults={"project": project})
        if not created and lead.project_id != project.id:
            raise PermissionError("Lead belongs to a different project.")
    else:
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


def _resolve_project_from_ws_payload(project_id, access_token):
    if project_id is None or access_token is None:
        raise ValueError("Both project_id and access_token are required for tenant-scoped WebSocket chat.")

    try:
        token = AccessToken(str(access_token))
    except Exception as exc:
        raise ValueError("Invalid access token.") from exc

    user_id = token.get("user_id")
    if user_id is None:
        raise ValueError("Invalid access token payload.")

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist as exc:
        raise PermissionDenied("User for token was not found.") from exc

    try:
        project_id_int = int(project_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid project_id.") from exc

    return get_project_for_user(user, project_id_int)
