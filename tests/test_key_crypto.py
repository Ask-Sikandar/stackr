from apps.accounts.crypto import decrypt_secret, encrypt_secret


def test_encrypt_decrypt_roundtrip():
    raw = "sk-private-key-123456"
    encrypted = encrypt_secret(raw)

    assert encrypted != raw
    assert encrypted.startswith("enc::")
    assert decrypt_secret(encrypted) == raw


def test_decrypt_secret_supports_legacy_plaintext_value():
    assert decrypt_secret("legacy-plain-key") == "legacy-plain-key"
