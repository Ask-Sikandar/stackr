from abc import ABC, abstractmethod
from collections.abc import Generator


class ILLMClient(ABC):
    """
    Contract for interacting with a language model.
    Concrete implementations: OllamaLLMClient, MockLLMClient.

    Separating complete() and stream() lets callers choose their mode:
    - REST endpoint uses complete() for a single JSON response
    - WebSocket consumer uses stream() to push tokens as they arrive
    """

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Return the full completion as a single string (blocking)."""
        ...

    @abstractmethod
    def stream(self, prompt: str) -> Generator[str, None, None]:
        """Yield completion tokens one-by-one as they are generated."""
        ...
