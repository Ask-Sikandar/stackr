from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChunkData:
    content: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
    # metadata keys:
    #   section_title (str)  — nearest heading above this chunk
    #   chunk_type   (str)  — "paragraph" | "table" | "list"
    #   char_start   (int)  — character offset in original document


class IChunker(ABC):
    """
    Contract for splitting document text into semantically meaningful chunks.
    Concrete implementations: SemanticChunker.
    """

    @abstractmethod
    def chunk(self, content: str, chunk_size: int = 500, overlap: int = 50) -> list[ChunkData]:
        """Split content into chunks of approximately chunk_size characters with overlap."""
        ...
