import asyncio

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from utils.firebase.firebase_admin import firebase_auth

_bearer = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency that verifies a Firebase ID token from the Authorization header.
    Returns the decoded token dict on success; raises 401 on any failure.

    Usage in a route:
        @router.post("/...")
        async def handler(token: dict = Depends(verify_token)):
            uid = token["uid"]
    """
    id_token = credentials.credentials
    try:
        decoded = await asyncio.to_thread(firebase_auth.verify_id_token, id_token)
        return decoded
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
