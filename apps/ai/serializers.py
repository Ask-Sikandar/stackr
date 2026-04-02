from rest_framework import serializers

from apps.leads.models import Lead

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "role",
            "content",
            "intent",
            "sources",
            "components",
            "handoff_triggered",
            "created_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "started_at", "messages"]


class ChatRequestSerializer(serializers.Serializer):
    lead_id = serializers.UUIDField()
    message = serializers.CharField(min_length=1, max_length=2000)


class ChatResponseSerializer(serializers.Serializer):
    """Mirrors AgentResponse.to_dict() + conversation context."""

    message_id = serializers.UUIDField()
    content = serializers.CharField()
    intent = serializers.CharField()
    sources = serializers.ListField()
    components = serializers.ListField()
    lead_score = serializers.IntegerField()
    handoff_triggered = serializers.BooleanField()
