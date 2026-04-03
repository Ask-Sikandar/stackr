from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.access import get_project_for_user
from apps.leads.models import IntentEvent, Lead
from services.factory import get_agent, get_llm_client_for_project
from services.interfaces.intent_classifier import Intent

from .models import Conversation, Message, MessageRole
from .serializers import ChatRequestSerializer, ConversationSerializer


def _get_or_create_lead(lead_id, project) -> Lead:
    lead, created = Lead.objects.get_or_create(lead_id=lead_id, defaults={"project": project})
    if not created and lead.project_id != project.id:
        raise PermissionError("Lead belongs to a different project.")
    return lead


def _get_or_create_conversation(lead: Lead) -> Conversation:
    # Reuse the latest conversation if it exists (one session per lead for POC)
    conv = lead.conversations.order_by("-started_at").first()
    if conv is None:
        conv = Conversation.objects.create(lead=lead)
    return conv


def _update_lead_score(lead: Lead, intent_str: str, delta: int, message_preview: str) -> None:
    try:
        intent = Intent(intent_str)
    except ValueError:
        intent = Intent.GENERAL
    lead.score += delta
    lead.last_intent = str(intent)
    lead.save(update_fields=["score", "last_intent", "last_seen_at"])
    IntentEvent.objects.create(
        lead=lead,
        intent=str(intent),
        message_preview=message_preview[:120],
        score_delta=delta,
    )


class ChatView(APIView):
    """
    POST /api/ai/chat/
    Body: { "lead_id": "<uuid>", "message": "..." }
    Returns a structured response with sources, components, and lead score.
    """

    def post(self, request: Request) -> Response:
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lead_id = serializer.validated_data["lead_id"]
        project_id = serializer.validated_data["project_id"]
        user_message = serializer.validated_data["message"]

        try:
            project = get_project_for_user(request.user, project_id)
            agent = get_agent()
            llm_client = get_llm_client_for_project(project)
            agent_response = agent.handle_message(user_message, llm_client=llm_client)

            with transaction.atomic():
                lead = _get_or_create_lead(lead_id, project)
                conv = _get_or_create_conversation(lead)

                # Save user turn
                Message.objects.create(
                    conversation=conv,
                    role=MessageRole.USER,
                    content=user_message,
                )
                # Save assistant turn
                Message.objects.create(
                    conversation=conv,
                    role=MessageRole.ASSISTANT,
                    content=agent_response.content,
                    intent=agent_response.intent,
                    sources=agent_response.sources,
                    components=agent_response.components,
                    handoff_triggered=agent_response.handoff_triggered,
                )
                _update_lead_score(lead, agent_response.intent, agent_response.lead_score_delta, user_message)

            return Response(
                {
                    **agent_response.to_dict(),
                    "project_id": project.id,
                    "lead_score": lead.score,
                },
                status=status.HTTP_200_OK,
            )

        except PermissionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return Response(
                {"error": "Assistant unavailable. Please try again.", "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class ChatHistoryView(APIView):
    """GET /api/ai/chat/history/<lead_id>/ — full conversation history for a lead"""

    def get(self, request: Request, lead_id) -> Response:
        project_id = request.query_params.get("project_id")
        if project_id is None:
            raise ValidationError({"project_id": "This query parameter is required."})

        try:
            project = get_project_for_user(request.user, int(project_id))
        except ValueError as exc:
            raise ValidationError({"project_id": "Invalid project id."}) from exc
        try:
            lead = Lead.objects.get(lead_id=lead_id, project=project)
        except Lead.DoesNotExist:
            return Response({"error": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)

        conversations = lead.conversations.prefetch_related("messages").all()
        serializer = ConversationSerializer(conversations, many=True)
        return Response({"lead_id": str(lead_id), "project_id": project.id, "conversations": serializer.data})
