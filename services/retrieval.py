"""
PgVectorRetriever — cosine similarity search over Chunk embeddings.

Uses pgvector's <=> operator (cosine distance) via the pgvector Django ORM extension.
pgvector was chosen over a separate vector store (ChromaDB, Qdrant) because:
- Django already uses PostgreSQL; no extra service or connection pool
- Embedding + metadata live in the same transaction (no partial-failure risk)
- SQL joins let us filter by document FK in the same query as the similarity search
- Scales to millions of vectors before needing a dedicated ANN index
"""

from pgvector.django import CosineDistance

from apps.documents.models import Chunk
from .interfaces.embedder import IEmbedder
from .interfaces.retriever import IRetriever, RetrievedChunk


class PgVectorRetriever(IRetriever):
    def __init__(self, embedder: IEmbedder) -> None:
        self._embedder = embedder

    def retrieve(self, query: str, top_k: int = 3, project_id: int | None = None) -> list[RetrievedChunk]:
        query_vector = self._embedder.embed(query)

        chunks_qs = Chunk.objects.select_related("document").exclude(embedding=None)
        if project_id is not None:
            chunks_qs = chunks_qs.filter(document__project_id=project_id)

        rows = chunks_qs.annotate(distance=CosineDistance("embedding", query_vector)).order_by("distance")[:top_k]

        results: list[RetrievedChunk] = []
        for chunk in rows:
            results.append(
                RetrievedChunk(
                    content=chunk.content,
                    document_title=chunk.document.title,
                    chunk_index=chunk.chunk_index,
                    score=round(1 - float(chunk.distance), 4),  # convert distance → similarity
                    metadata=chunk.metadata,
                )
            )
        return results
