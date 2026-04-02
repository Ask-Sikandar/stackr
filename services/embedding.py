"""
SentenceTransformerEmbedder — wraps the all-MiniLM-L6-v2 model.

The model is loaded once at class instantiation and cached via the factory
(services/factory.py uses @lru_cache).  Loading on every request would add
~2s latency and waste GPU/CPU.

Model choice: all-MiniLM-L6-v2
- 384 dimensions (small, fast)
- Good cosine similarity on domain-specific FAQ text
- No API key required, runs fully locally
- Benchmark: ~63% on SBERT STS tasks — adequate for RAG retrieval
"""

from sentence_transformers import SentenceTransformer

from .interfaces.embedder import IEmbedder


class SentenceTransformerEmbedder(IEmbedder):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)
        self._dims = self._model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, convert_to_numpy=True, batch_size=32).tolist()

    @property
    def dimensions(self) -> int:
        return self._dims  # type: ignore[return-value]
