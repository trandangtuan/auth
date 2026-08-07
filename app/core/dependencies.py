from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import decode_access_token
from app.models.user import User
from app.models.auth_session import AuthSession
from app.repositories.user_repository import UserRepository
from app.repositories.auth_session_repository import AuthSessionRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCESS_TOKEN_INVALID")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCESS_TOKEN_INVALID")
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCESS_TOKEN_INVALID")
    user_id = payload.get("sub")
    session_id = payload.get("session_id")
    if not user_id or not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCESS_TOKEN_INVALID")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCOUNT_DISABLED")
    session_repo = AuthSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_SESSION_REVOKED")
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AUTH_ACCOUNT_DISABLED")
    return current_user


async def get_current_verified_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AUTH_EMAIL_NOT_VERIFIED")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="RESOURCE_FORBIDDEN")
    return current_user


async def get_current_auth_session(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> AuthSession:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCESS_TOKEN_INVALID")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCESS_TOKEN_INVALID")

    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCESS_TOKEN_INVALID")

    session_repo = AuthSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_SESSION_REVOKED")
    return session
