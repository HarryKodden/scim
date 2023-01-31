# auth.py

import os
from fastapi import status, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

api_keys = [
    os.environ.get("API_KEY", "secret"),
]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # use token authentication

def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    if api_key not in api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Forbidden"
        )
