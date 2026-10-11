# routers/ssf.py

"""Minimal OpenID SSF discovery endpoints for RFC 9967 SET receivers such as easyssf."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from events.config import load_event_config
from events.keys import jwks_document
from routers import BASE_PATH

router = APIRouter(tags=["SSF"])


def _issuer_base() -> str:
    cfg = load_event_config()
    issuer = (cfg.issuer or "").rstrip("/")
    if issuer.startswith("http://") or issuer.startswith("https://"):
        return issuer
    # Fallback when SET_ISSUER is a bare name: advertise relative to this process.
    return f"http://localhost:8000{BASE_PATH}".rstrip("/") or "http://localhost:8000"


@router.get("/.well-known/jwks.json", include_in_schema=False)
@router.get("/jwks", include_in_schema=True)
def jwks():
    return JSONResponse(jwks_document())


@router.get("/.well-known/ssf-configuration", include_in_schema=True)
def ssf_configuration():
    """
    Minimal transmitter metadata so OpenID SSF receivers can discover the JWK Set.

    This service delivers SCIM Events (RFC 9967) over RFC 8935 push; it does not
    implement SSF stream management.
    """
    base = _issuer_base()
    return {
        "issuer": load_event_config().issuer,
        "jwks_uri": f"{base}/.well-known/jwks.json",
        "delivery_methods_supported": [
            "urn:ietf:rfc:8935",
        ],
    }
