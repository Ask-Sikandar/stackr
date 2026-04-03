from django.db import models
from pgvector.django import VectorField
import uuid


class SourceType(models.TextChoices):
    MARKDOWN = "markdown", "Markdown"
    PDF = "pdf", "PDF"
    TEXT = "text", "Text"


class IngestionStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class Document(models.Model):
    """
    Represents a raw product document ingested into the system.
    After ingestion, it is chunked and each chunk is embedded.
    """

    title = models.CharField(max_length=255)
    content = models.TextField()
    source_type = models.CharField(max_length=20, choices=SourceType.choices, default=SourceType.MARKDOWN)
    file_url = models.URLField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    project = models.ForeignKey(
        "accounts.Project",
        related_name="documents",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return self.title


class Chunk(models.Model):
    """
    A semantic chunk of a Document with its embedding vector.

    Chunking strategy (see services/chunking.py for full rationale):
    - Split first by paragraph boundaries (double newlines) to preserve semantic units.
    - If a paragraph exceeds CHUNK_SIZE chars, split further at sentence boundaries.
    - Tables (lines matching | ... |) are kept as atomic chunks to avoid row splits.
    - 50-char overlap is appended from the start of the next chunk to preserve context.
    - Metadata records section_title (last heading seen) and chunk_type for filtering.
    """

    document = models.ForeignKey(Document, related_name="chunks", on_delete=models.CASCADE)
    content = models.TextField()
    # 384 dimensions matches all-MiniLM-L6-v2; update if you swap embedding models
    embedding = VectorField(dimensions=384, null=True)
    chunk_index = models.IntegerField()
    metadata = models.JSONField(default=dict)
    # metadata keys: section_title (str), chunk_type (paragraph|table|list), char_start (int)

    class Meta:
        ordering = ["document", "chunk_index"]
        unique_together = [("document", "chunk_index")]

    def __str__(self) -> str:
        return f"{self.document.title} — chunk {self.chunk_index}"


class IngestionJob(models.Model):
    """
    Tracks asynchronous ingestion requests for documents.
    """

    job_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    document = models.ForeignKey(Document, related_name="ingestion_jobs", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=IngestionStatus.choices, default=IngestionStatus.QUEUED)
    task_id = models.CharField(max_length=255, blank=True, default="")
    retries = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-queued_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["document", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} — {self.status} ({self.job_id})"
