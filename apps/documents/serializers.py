from rest_framework import serializers

from .models import Chunk, Document, IngestionJob


class ChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chunk
        fields = ["id", "chunk_index", "content", "metadata"]


class DocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "content",
            "source_type",
            "file_url",
            "uploaded_at",
            "processed",
            "chunk_count",
        ]
        read_only_fields = ["uploaded_at", "processed", "chunk_count"]

    def get_chunk_count(self, obj: Document) -> int:
        return obj.chunks.count()


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — omits full content."""

    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "title", "source_type", "uploaded_at", "processed", "chunk_count"]
        read_only_fields = ["uploaded_at", "processed"]

    def get_chunk_count(self, obj: Document) -> int:
        return obj.chunks.count()


class IngestionJobSerializer(serializers.ModelSerializer):
    document_id = serializers.IntegerField(source="document.id", read_only=True)

    class Meta:
        model = IngestionJob
        fields = [
            "job_id",
            "document_id",
            "status",
            "task_id",
            "retries",
            "error_message",
            "queued_at",
            "started_at",
            "finished_at",
        ]
