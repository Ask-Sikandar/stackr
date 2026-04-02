"""
Tests for the document ingestion pipeline.

Uses mock services (no model loading, no pgvector) as configured in settings/test.py.
The real SemanticChunker and MockEmbedder are used so chunking logic is fully tested
but no GPU/network dependencies are required.
"""
import math

import pytest

from apps.documents.models import Chunk, Document
from services.ingestion import chunk_document, ingest_document
from services.mocks import MockEmbedder
from tests.conftest import requires_postgres


# ---------------------------------------------------------------------------
# Chunk creation
# ---------------------------------------------------------------------------


@requires_postgres
@pytest.mark.django_db
def test_chunk_creation(sample_document):
    chunks = chunk_document(sample_document, chunk_size=500)

    assert len(chunks) > 0, "document should produce at least one chunk"
    assert all(c.document_id == sample_document.id for c in chunks), (
        "every chunk must reference the source document"
    )


@requires_postgres
@pytest.mark.django_db
def test_chunk_creation_short_document():
    doc = Document.objects.create(
        title="Tiny Doc",
        content="A very short document.",
    )
    chunks = chunk_document(doc, chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0].content == "A very short document."


@requires_postgres
@pytest.mark.django_db
def test_chunk_respects_size_limit(sample_document):
    """No chunk content should exceed chunk_size + overlap characters."""
    chunk_size = 200
    overlap = 50
    chunks = chunk_document(sample_document, chunk_size=chunk_size)
    for chunk in chunks:
        # Allow for the overlap suffix added by _apply_overlap
        assert len(chunk.content) <= chunk_size + overlap + 10, (
            f"Chunk too long: {len(chunk.content)} chars"
        )


@requires_postgres
@pytest.mark.django_db
def test_chunk_metadata_has_required_keys(sample_document):
    chunks = chunk_document(sample_document, chunk_size=500)
    for chunk in chunks:
        assert "section_title" in chunk.metadata
        assert "chunk_type" in chunk.metadata


@requires_postgres
@pytest.mark.django_db
def test_table_chunk_kept_atomic():
    """Table rows should be emitted as a single chunk, not split."""
    content = (
        "## Pricing Table\n\n"
        "| Size | Price |\n"
        "|------|-------|\n"
        "| 20ft | $2,100 |\n"
        "| 40ft | $3,850 |\n\n"
        "Some paragraph after the table."
    )
    doc = Document.objects.create(title="Table Doc", content=content)
    chunks = chunk_document(doc, chunk_size=500)

    # Find the table chunk
    table_chunks = [c for c in chunks if c.metadata.get("chunk_type") == "table"]
    assert len(table_chunks) >= 1, "Should have at least one table chunk"
    # All table rows should be in one chunk (not split)
    combined = " ".join(c.content for c in table_chunks)
    assert "20ft" in combined and "40ft" in combined


# ---------------------------------------------------------------------------
# Embedding similarity
# ---------------------------------------------------------------------------


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def generate_embedding(text: str) -> list[float]:
    """Use MockEmbedder directly so this test runs without sentence-transformers loaded."""
    return MockEmbedder().embed(text)


def test_embedding_similarity():
    emb1 = generate_embedding("shipping container prices")
    emb2 = generate_embedding("container pricing information")
    sim = cosine_similarity(emb1, emb2)
    assert sim > 0.5, f"Expected similarity > 0.5, got {sim:.3f}"


def test_embedding_dimensions():
    embedder = MockEmbedder()
    vec = embedder.embed("test")
    assert len(vec) == 384
    assert embedder.dimensions == 384


def test_embedding_batch_consistency():
    embedder = MockEmbedder()
    texts = ["hello", "world", "container"]
    batch = embedder.embed_batch(texts)
    assert len(batch) == 3
    for i, text in enumerate(texts):
        single = embedder.embed(text)
        assert batch[i] == single, "Batch result should match single embed"


# ---------------------------------------------------------------------------
# Full ingest_document pipeline
# ---------------------------------------------------------------------------


@requires_postgres
@pytest.mark.django_db
def test_ingest_document_marks_processed(sample_document):
    assert not sample_document.processed
    ingest_document(sample_document.id)
    sample_document.refresh_from_db()
    assert sample_document.processed


@requires_postgres
@pytest.mark.django_db
def test_ingest_document_creates_db_chunks(sample_document):
    ingest_document(sample_document.id)
    count = Chunk.objects.filter(document=sample_document).count()
    assert count > 0


@requires_postgres
@pytest.mark.django_db
def test_ingest_document_idempotent(sample_document):
    """Re-ingesting should delete old chunks and create fresh ones."""
    ingest_document(sample_document.id)
    first_count = Chunk.objects.filter(document=sample_document).count()

    ingest_document(sample_document.id)
    second_count = Chunk.objects.filter(document=sample_document).count()

    assert first_count == second_count, "Re-ingestion should produce the same chunk count"


@requires_postgres
@pytest.mark.django_db
def test_ingest_nonexistent_document_raises():
    with pytest.raises(Document.DoesNotExist):
        ingest_document(99999)
