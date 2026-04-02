"""
Test settings.
- Uses in-memory channel layer (no Redis required)
- Swaps real AI services for fast mocks via SERVICE_CLASSES
- Uses a separate test database
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# In-memory channel layer: no Redis needed during tests
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Override DB name for test isolation
DATABASES["default"]["NAME"] = "memox_test"  # noqa: F405

# Swap real services for mocks — keeps tests fast and offline
SERVICE_CLASSES = {  # noqa: F405
    "EMBEDDER": "services.mocks.MockEmbedder",
    "RETRIEVER": "services.mocks.MockRetriever",
    "LLM_CLIENT": "services.mocks.MockLLMClient",
    "CHUNKER": "services.chunking.SemanticChunker",  # real chunker, no I/O
    "INTENT_CLASSIFIER": "services.intent.KeywordIntentClassifier",  # real, no I/O
}

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
