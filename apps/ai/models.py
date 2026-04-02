import uuid

from django.db import models

from apps.leads.models import Lead


class Conversation(models.Model):
    """A chat session for a lead. One lead can have many conversations."""

    lead = models.ForeignKey(Lead, related_name="conversations", on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Conversation {self.pk} — lead {self.lead.lead_id}"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"


class Message(models.Model):
    """
    A single turn in a conversation.

    `sources` stores a list of {"title", "excerpt", "score", "chunk_index"} dicts.
    `components` stores structured UI components:
        {"type": "product_comparison", "data": {...}}
        {"type": "cta", "label": "...", "action": "..."}
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content = models.TextField()
    intent = models.CharField(max_length=20, blank=True, default="")
    sources = models.JSONField(default=list)
    components = models.JSONField(default=list)
    handoff_triggered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"[{self.role}] {self.content[:60]}"
