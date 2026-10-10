from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt

from app.config import get_settings
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    s = get_settings()
    if s.auth_demo_mode:
        sub = body.username.strip() or "demo"
    else:
        if body.username != s.login_username or body.password != s.login_password:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
        sub = body.username
    expire = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expire_minutes)
    token = jwt.encode(
        {"sub": sub, "exp": expire},
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )
    return TokenResponse(access_token=token)
