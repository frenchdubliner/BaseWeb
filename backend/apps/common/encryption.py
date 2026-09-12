"""
Field-level encryption at rest, keyed by the ENCRYPTION_KEY environment
variable (never SECRET_KEY). Used for sensitive PII such as phone numbers.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _derive_fernet_key(raw_key: str) -> bytes:
    """
    Accepts either a proper Fernet key (32 url-safe base64 bytes) or an
    arbitrary secret string, and always returns a valid Fernet key by
    hashing arbitrary input down to 32 bytes.
    """
    try:
        Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)
        return raw_key.encode() if isinstance(raw_key, str) else raw_key
    except Exception:
        digest = hashlib.sha256(raw_key.encode()).digest()
        return base64.urlsafe_b64encode(digest)


def get_fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not configured.")
    return Fernet(_derive_fernet_key(settings.ENCRYPTION_KEY))


class EncryptedCharField(models.CharField):
    """
    Transparently encrypts values with Fernet (AES128-CBC + HMAC) before
    writing to the database, and decrypts on read. Ciphertext is stored as
    base64 text, so max_length is padded generously.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 512)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return get_fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            # Not encrypted (legacy/plaintext) data - return as-is rather
            # than crashing the request.
            return value
