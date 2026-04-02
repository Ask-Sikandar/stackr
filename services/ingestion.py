"""
Document ingestion pipeline.

ingest_document(document_id) is the public entry point:
1. Load Document from DB
2. Chunk content using IChunker
3. Generate embeddings in batch (one forward pass, not N)
4. Bulk-create Chunk rows
5. Mark document.processed = True

Dependency injection via factory.get_*() — the concrete classes are
resolved from settings.SERVICE_CLASSES so tests can inject mocks.
"""

from django.db import transaction

from apps.documents.models import Chunk, Document
from .factory import get_chunker, get_embedder


def ingest_document(document_id: int) -> list[Chunk]:
    """
    Chunk, embed, and persist a Document.  Returns the created Chunk list.
    Raises Document.DoesNotExist if the id is invalid.
    """
    document = Document.objects.get(pk=document_id)
    chunker = get_chunker()
    embedder = get_embedder()

    chunk_data = chunker.chunk(document.content)
    if not chunk_data:
        return []

    texts = [cd.content for cd in chunk_data]
    embeddings = embedder.embed_batch(texts)

    with transaction.atomic():
        # Delete stale chunks if re-ingesting
        document.chunks.all().delete()

        chunks = Chunk.objects.bulk_create(
            [
                Chunk(
                    document=document,
                    content=cd.content,
                    embedding=emb,
                    chunk_index=cd.chunk_index,
                    metadata=cd.metadata,
                )
                for cd, emb in zip(chunk_data, embeddings)
            ]
        )
        document.processed = True
        document.save(update_fields=["processed"])

    return chunks


def chunk_document(document: Document, chunk_size: int = 500) -> list[Chunk]:
    """
    Convenience wrapper used in tests — chunks without persisting embeddings.
    Returns unsaved Chunk instances so tests can assert on count / document FK.
    """
    chunker = get_chunker()
    chunk_data = chunker.chunk(document.content, chunk_size=chunk_size)
    return [
        Chunk(
            document=document,
            content=cd.content,
            chunk_index=cd.chunk_index,
            metadata=cd.metadata,
        )
        for cd in chunk_data
    ]
