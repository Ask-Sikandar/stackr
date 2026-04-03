import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

_ENC_PREFIX = "enc::"


def _derive_fernet_key(seed: str) -> bytes:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    configured_key = getattr(settings, "LLM_KEY_ENCRYPTION_KEY", "").strip()
    key_material = configured_key.encode("utf-8") if configured_key else _derive_fernet_key(
        f"{settings.SECRET_KEY}:llm-key-encryption"
    )

    try:
        return Fernet(key_material)
    except Exception as exc:  # pragma: no cover - defensive config guard
        raise RuntimeError("Invalid LLM_KEY_ENCRYPTION_KEY value.") from exc


def encrypt_secret(secret: str) -> str:
    if not secret:
        return secret
    token = _get_fernet().encrypt(secret.encode("utf-8")).decode("utf-8")
    return f"{_ENC_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    if not value:
        return value

    # Backward compatibility for previously stored plaintext keys.
    if not value.startswith(_ENC_PREFIX):
        return value

    token = value[len(_ENC_PREFIX) :]
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt stored key.") from exc
