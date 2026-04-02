"""
Service factory — resolves concrete implementations from settings.SERVICE_CLASSES.

This is the Dependency Inversion glue layer:
- High-level modules (views, consumers, agent) call get_embedder() etc.
- The actual class is read from settings at runtime, not hard-coded.
- Tests set SERVICE_CLASSES to mock implementations → no model loading, no DB.

@lru_cache ensures each service is a singleton per process (no repeated model loads).
"""

from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string

from .interfaces.chunker import IChunker
from .interfaces.embedder import IEmbedder
from .interfaces.intent_classifier import IIntentClassifier
from .interfaces.llm_client import ILLMClient
from .interfaces.prompt_builder import IPromptBuilder
from .interfaces.retriever import IRetriever


def _load(key: str):
    cls_path = settings.SERVICE_CLASSES[key]
    return import_string(cls_path)


@lru_cache(maxsize=1)
def get_embedder() -> IEmbedder:
    return _load("EMBEDDER")()


@lru_cache(maxsize=1)
def get_chunker() -> IChunker:
    return _load("CHUNKER")()


@lru_cache(maxsize=1)
def get_retriever() -> IRetriever:
    cls = _load("RETRIEVER")
    # PgVectorRetriever needs an embedder; mocks don't
    import inspect
    sig = inspect.signature(cls.__init__)
    if "embedder" in sig.parameters:
        return cls(embedder=get_embedder())
    return cls()


@lru_cache(maxsize=1)
def get_llm_client() -> ILLMClient:
    return _load("LLM_CLIENT")()


@lru_cache(maxsize=1)
def get_prompt_builder() -> IPromptBuilder:
    from .prompt_builder import SalesPromptBuilder
    return SalesPromptBuilder()


@lru_cache(maxsize=1)
def get_intent_classifier() -> IIntentClassifier:
    return _load("INTENT_CLASSIFIER")()


def get_agent() -> "AgentHandler":  # noqa: F821
    from .agent import AgentHandler
    return AgentHandler(
        retriever=get_retriever(),
        llm_client=get_llm_client(),
        prompt_builder=get_prompt_builder(),
        intent_classifier=get_intent_classifier(),
    )


def reset_cache() -> None:
    """Clear all cached singletons. Used in tests that swap SERVICE_CLASSES."""
    get_embedder.cache_clear()
    get_chunker.cache_clear()
    get_retriever.cache_clear()
    get_llm_client.cache_clear()
    get_prompt_builder.cache_clear()
    get_intent_classifier.cache_clear()
