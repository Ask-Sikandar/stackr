from abc import ABC, abstractmethod


class IEmbedder(ABC):
    """
    Contract for embedding text into a fixed-dimension float vector.
    Concrete implementations: SentenceTransformerEmbedder, MockEmbedder.
    """

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts in one forward pass (more efficient than looping)."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Vector dimensionality produced by this embedder."""
        ...
