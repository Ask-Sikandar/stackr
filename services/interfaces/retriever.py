from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    content: str
    document_title: str
    chunk_index: int
    score: float  # cosine similarity, higher = more relevant
    metadata: dict = field(default_factory=dict)


class IRetriever(ABC):
    """
    Contract for finding the most relevant chunks for a query.
    Concrete implementations: PgVectorRetriever, MockRetriever.
    """

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """Return the top_k most relevant chunks for the given query."""
        ...
