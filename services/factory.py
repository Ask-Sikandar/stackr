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
from .llm import FallbackLLMClient, GeminiLLMClient, OllamaLLMClient, OpenAILLMClient


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


def _provider_chain(primary: str, backup: str) -> list[str]:
    chain: list[str] = []
    for provider in [primary, backup]:
        normalized = (provider or "").strip().lower()
        if normalized and normalized not in chain:
            chain.append(normalized)
    return chain


def _build_provider_client(provider: str, api_key: str | None = None) -> ILLMClient:
    provider = provider.lower()
    if provider == "ollama":
        return OllamaLLMClient()
    if provider == "openai":
        key = api_key or getattr(settings, "OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OpenAI provider configured but OPENAI_API_KEY is missing.")
        return OpenAILLMClient(api_key=key)
    if provider == "gemini":
        key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        if not key:
            raise ValueError("Gemini provider configured but GEMINI_API_KEY is missing.")
        return GeminiLLMClient(api_key=key)
    raise ValueError(f"Unsupported LLM provider: {provider}")


def get_llm_client_for_project(project) -> ILLMClient:
    from apps.accounts.models import OrganizationLLMKey

    org = project.organization
    preferred_chain = _provider_chain(project.llm_primary_provider, project.llm_backup_provider)
    platform_chain = _provider_chain(
        getattr(settings, "LLM_PRIMARY_PROVIDER", "ollama"),
        getattr(settings, "LLM_BACKUP_PROVIDER", ""),
    )
    if not preferred_chain:
        preferred_chain = platform_chain

    clients: list[tuple[str, ILLMClient]] = []

    if org.use_private_llm_credentials:
        for provider in preferred_chain:
            key_obj = OrganizationLLMKey.objects.filter(
                organization=org,
                provider=provider,
                is_active=True,
            ).first()
            if key_obj is None:
                continue
            try:
                clients.append((f"private:{provider}", _build_provider_client(provider, api_key=key_obj.api_key)))
            except ValueError:
                continue

        if clients and not org.allow_platform_fallback:
            if len(clients) == 1:
                return clients[0][1]
            return FallbackLLMClient(clients)

        if not clients and not org.allow_platform_fallback:
            raise RuntimeError(
                "Private LLM key usage is enabled but no active private provider keys are configured."
            )

    platform_candidates = preferred_chain + [p for p in platform_chain if p not in preferred_chain]
    for provider in platform_candidates:
        try:
            clients.append((f"platform:{provider}", _build_provider_client(provider)))
        except ValueError:
            continue

    if not clients:
        raise RuntimeError("No LLM providers are configured for this project.")

    if len(clients) == 1:
        return clients[0][1]
    return FallbackLLMClient(clients)


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
