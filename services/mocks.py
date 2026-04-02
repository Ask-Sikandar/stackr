"""
Mock service implementations for tests.

These satisfy all interface contracts without loading ML models or hitting
external services.  Injected via settings.SERVICE_CLASSES in config/settings/test.py.
"""

from collections.abc import Generator

from .interfaces.embedder import IEmbedder
from .interfaces.llm_client import ILLMClient
from .interfaces.retriever import IRetriever, RetrievedChunk


class MockEmbedder(IEmbedder):
    """Returns a deterministic 384-dim vector (all 0.1)."""

    _DIMS = 384

    def embed(self, text: str) -> list[float]:
        # Vary slightly by text length so similarity tests are meaningful
        base = 0.1 + (len(text) % 10) * 0.01
        return [base] * self._DIMS

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    @property
    def dimensions(self) -> int:
        return self._DIMS


class MockRetriever(IRetriever):
    """Returns two canned chunks regardless of query."""

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                content="40ft standard container: $3,850. 20ft: $2,100.",
                document_title="Pricing Sheet",
                chunk_index=0,
                score=0.92,
                metadata={"section_title": "Pricing", "chunk_type": "paragraph"},
            ),
            RetrievedChunk(
                content="We deliver to all 48 contiguous states including Texas.",
                document_title="Delivery Policy",
                chunk_index=1,
                score=0.85,
                metadata={"section_title": "Coverage", "chunk_type": "paragraph"},
            ),
        ]


class MockLLMClient(ILLMClient):
    """Returns a canned response instantly — no HTTP calls."""

    _RESPONSE = (
        "A 40ft standard container is priced at $3,850 [Source: Pricing Sheet]. "
        "We do deliver to Texas with a 3-7 day lead time [Source: Delivery Policy]."
    )

    def complete(self, prompt: str) -> str:
        return self._RESPONSE

    def stream(self, prompt: str) -> Generator[str, None, None]:
        for word in self._RESPONSE.split():
            yield word + " "
