# events/keys.py

"""RSA signing material for SET delivery (OpenID SSF / easyssf receivers)."""

from __future__ import annotations

import base64
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_CACHED: Optional["SigningKey"] = None


@dataclass(frozen=True)
class SigningKey:
    """Private key used to sign SETs, with a public JWK for verification."""

    private_key_pem: str
    algorithm: str
    key_id: str

    def public_jwk(self) -> Dict[str, Any]:
        private_key = serialization.load_pem_private_key(
            self.private_key_pem.encode("utf-8"),
            password=None,
        )
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise ValueError("SET signing key must be an RSA private key")
        public_numbers = private_key.public_key().public_numbers()

        def _b64url_uint(value: int) -> str:
            length = (value.bit_length() + 7) // 8
            return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode(
                "ascii"
            )

        return {
            "kty": "RSA",
            "use": "sig",
            "alg": self.algorithm,
            "kid": self.key_id,
            "n": _b64url_uint(public_numbers.n),
            "e": _b64url_uint(public_numbers.e),
        }


def _read_private_key_pem() -> Optional[str]:
    pem = os.environ.get("SET_SIGNING_PRIVATE_KEY")
    if pem:
        return pem.replace("\\n", "\n")
    path = os.environ.get("SET_SIGNING_PRIVATE_KEY_FILE")
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    return None


def _generate_rsa_pem() -> str:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def load_signing_key(force_reload: bool = False) -> Optional[SigningKey]:
    """
    Load RSA signing material when configured.

    Prefer SET_SIGNING_PRIVATE_KEY / SET_SIGNING_PRIVATE_KEY_FILE. When
    SET_SIGNING_GENERATE_RSA=true and no key is provided, generate an ephemeral
    2048-bit key (demo / compose only; not for multi-instance production).
    """
    global _CACHED
    with _LOCK:
        if _CACHED is not None and not force_reload:
            return _CACHED

        pem = _read_private_key_pem()
        generate = os.environ.get("SET_SIGNING_GENERATE_RSA", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if not pem and generate:
            logger.warning(
                "SET_SIGNING_GENERATE_RSA is enabled: generating an ephemeral RSA key; "
                "receivers must fetch JWKS from this process"
            )
            pem = _generate_rsa_pem()
        if not pem:
            _CACHED = None
            return None

        algorithm = os.environ.get("SET_SIGNING_ALGORITHM", "RS256")
        if algorithm.upper().startswith("HS"):
            algorithm = "RS256"
        key_id = os.environ.get("SET_SIGNING_KEY_ID", "scim-set-1")
        _CACHED = SigningKey(private_key_pem=pem, algorithm=algorithm, key_id=key_id)
        return _CACHED


def jwks_document() -> Dict[str, Any]:
    """Public JWK Set for SET verification, or empty keys when RSA is not configured."""
    key = load_signing_key()
    if key is None:
        return {"keys": []}
    return {"keys": [key.public_jwk()]}


def reset_signing_key_cache() -> None:
    """Test helper: drop the cached RSA key so the next load reads the environment again."""
    global _CACHED
    with _LOCK:
        _CACHED = None
