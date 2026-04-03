import uuid

from django.db import models


class Lead(models.Model):
    """
    Represents a website prospect.

    lead_id is exposed publicly (used in WS URL and chat API).
    score accumulates as the lead interacts:
        general=1, availability=5, pricing=10, conversion=25
    Reasoning: conversion signals are 25x more valuable than general noise.
    """

    lead_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    score = models.IntegerField(default=0)
    last_intent = models.CharField(max_length=20, blank=True, default="")
    project = models.ForeignKey(
        "accounts.Project",
        related_name="leads",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-score", "-last_seen_at"]

    def __str__(self) -> str:
        return f"Lead {self.lead_id} (score={self.score})"


class IntentEvent(models.Model):
    """
    Immutable log of every intent classification for a lead.
    Powers the intent-progression timeline on the Lead Dashboard.
    """

    lead = models.ForeignKey(Lead, related_name="intent_events", on_delete=models.CASCADE)
    intent = models.CharField(max_length=20)
    message_preview = models.CharField(max_length=120)
    score_delta = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.lead.lead_id} — {self.intent} (+{self.score_delta})"
