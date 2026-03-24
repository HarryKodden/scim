# auth.py

import os
import logging
from fastapi import status, HTTPException, Depends, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader

api_keys = [
    os.environ.get("API_KEY", "secret"),
]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
logger = logging.getLogger(__name__)


def api_key_auth(
    bearer_token: str = Depends(oauth2_scheme),
    api_key_header: str = Security(api_key_header),
):
    bearer_valid = bearer_token in api_keys
    api_key_valid = api_key_header in api_keys

    logger.debug(
        "[AUTH] bearer_present=%s bearer_valid=%s x_api_key_present=%s x_api_key_valid=%s",
        bool(bearer_token),
        bearer_valid,
        bool(api_key_header),
        api_key_valid,
    )

    if bearer_valid:
        return bearer_token

    if api_key_valid:
        return api_key_header

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Forbidden"
    )
