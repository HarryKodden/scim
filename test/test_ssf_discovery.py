# test/test_ssf_discovery.py

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from events.config import load_event_config
from events.keys import jwks_document, load_signing_key, reset_signing_key_cache
from events.signing import prepare_set_delivery_body


def test_generate_rsa_exposes_jwks_and_signs_secevent(monkeypatch):
    reset_signing_key_cache()
    monkeypatch.delenv("SET_SIGNING_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("SET_SIGNING_PRIVATE_KEY_FILE", raising=False)
    monkeypatch.delenv("SET_SIGNING_SECRET", raising=False)
    monkeypatch.setenv("SET_SIGNING_GENERATE_RSA", "true")
    monkeypatch.setenv("SET_ISSUER", "http://scim:8000")

    cfg = load_event_config()
    assert cfg.signing_enabled
    assert cfg.signing_key is not None
    assert cfg.signing_algorithm == "RS256"

    body, content_type = prepare_set_delivery_body(
        {"iss": "http://scim:8000", "jti": "demo-jti", "events": {}},
        cfg,
    )
    assert content_type == "application/secevent+jwt"
    header = jwt.get_unverified_header(body)
    assert header["typ"] == "secevent+jwt"
    assert header["alg"] == "RS256"
    assert "kid" in header

    jwks = jwks_document()
    assert len(jwks["keys"]) == 1
    assert jwks["keys"][0]["kid"] == header["kid"]

    public_key = serialization.load_pem_private_key(
        cfg.signing_key.private_key_pem.encode("utf-8"),
        password=None,
    ).public_key()
    decoded = jwt.decode(
        body,
        public_key,
        algorithms=["RS256"],
        options={"require": ["iss", "jti"]},
    )
    assert decoded["iss"] == "http://scim:8000"
    reset_signing_key_cache()


def test_ssf_configuration_and_jwks_endpoints(test_app, monkeypatch):
    reset_signing_key_cache()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    monkeypatch.setenv("SET_SIGNING_PRIVATE_KEY", pem)
    monkeypatch.setenv("SET_ISSUER", "http://scim:8000")
    monkeypatch.delenv("SET_SIGNING_GENERATE_RSA", raising=False)

    meta = test_app.get("/.well-known/ssf-configuration")
    assert meta.status_code == 200
    assert meta.json()["issuer"] == "http://scim:8000"
    assert meta.json()["jwks_uri"].endswith("/.well-known/jwks.json")

    jwks = test_app.get("/.well-known/jwks.json")
    assert jwks.status_code == 200
    assert len(jwks.json()["keys"]) == 1
    assert jwks.json()["keys"][0]["kty"] == "RSA"
    assert load_signing_key() is not None
    reset_signing_key_cache()
