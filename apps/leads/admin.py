from django.contrib import admin

from .models import IntentEvent, Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["lead_id", "project", "score", "last_intent", "last_seen_at"]
    ordering = ["-score"]


@admin.register(IntentEvent)
class IntentEventAdmin(admin.ModelAdmin):
    list_display = ["lead", "intent", "score_delta", "created_at"]
    list_filter = ["intent"]
