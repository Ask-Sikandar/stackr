from django.contrib import admin

from .models import Chunk, Document, IngestionJob


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "source_type", "processed", "uploaded_at"]
    list_filter = ["processed", "source_type"]
    search_fields = ["title"]


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ["document", "chunk_index", "metadata"]
    list_filter = ["document"]
    raw_id_fields = ["document"]


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ["job_id", "document", "status", "retries", "queued_at", "finished_at"]
    list_filter = ["status"]
    search_fields = ["job_id", "document__title", "task_id"]
    raw_id_fields = ["document"]
