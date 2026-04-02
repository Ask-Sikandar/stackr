from rest_framework import serializers

from .models import IntentEvent, Lead


class IntentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntentEvent
        fields = ["intent", "message_preview", "score_delta", "created_at"]


class LeadSerializer(serializers.ModelSerializer):
    intent_events = IntentEventSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id",
            "lead_id",
            "created_at",
            "last_seen_at",
            "score",
            "last_intent",
            "message_count",
            "intent_events",
        ]

    def get_message_count(self, obj: Lead) -> int:
        return sum(c.messages.count() for c in obj.conversations.all())


class LeadListSerializer(serializers.ModelSerializer):
    """Lightweight for dashboard list — no nested events."""

    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = ["id", "lead_id", "score", "last_intent", "last_seen_at", "message_count"]

    def get_message_count(self, obj: Lead) -> int:
        return sum(c.messages.count() for c in obj.conversations.all())
