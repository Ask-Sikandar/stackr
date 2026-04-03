from abc import ABC, abstractmethod

from .retriever import RetrievedChunk


class IPromptBuilder(ABC):
    """Contract for assembling LLM prompts from query + retrieved context."""

    @abstractmethod
    def build(
        self,
        query: str,
        context: list[RetrievedChunk],
        custom_instructions: str | None = None,
    ) -> str:
        """Return a fully assembled prompt string ready to send to the LLM."""
        ...
