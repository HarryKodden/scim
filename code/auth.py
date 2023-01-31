# auth.py

import os
from fastapi import status, HTTPException, Depends, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader

api_keys = [
    os.environ.get("API_KEY", "secret"),
]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def api_key_auth(
    bearer_token: str = Depends(oauth2_scheme),
    api_key_header: str = Security(api_key_header),
):
    if bearer_token in api_keys:
        return bearer_token

    if api_key_header in api_keys:
        return api_key_header

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Forbidden"
    )
