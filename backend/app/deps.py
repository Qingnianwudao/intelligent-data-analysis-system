from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings

security = HTTPBearer(auto_error=False)


def get_current_subject(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Authorization Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    s = get_settings()
    try:
        payload = jwt.decode(
            creds.credentials,
            s.jwt_secret,
            algorithms=[s.jwt_algorithm],
        )
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Token 无效")
        return str(sub)
    except JWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
