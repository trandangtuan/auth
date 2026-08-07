import uuid
from datetime import timedelta
from urllib.parse import quote, unquote, urlencode, urlparse, urlunparse
from fastapi import APIRouter, HTTPException, Request, Form, Body, status, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import secrets
from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import (
    hash_password,
    hash_token,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_random_token,
    create_sso_token,
    decode_sso_token,
    now_utc,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.auth_session_repository import AuthSessionRepository

router = APIRouter()


def make_response(data: dict | None = None, message: str = "", status_code: int = 200) -> JSONResponse:
    return JSONResponse({"success": True, "data": data or {}, "message": message}, status_code=status_code)


def normalize_return_url(return_url: str | None) -> str | None:
    if not return_url:
        return None
    parsed = urlparse(return_url)
    if parsed.scheme == "" and parsed.netloc == "" and parsed.path.startswith("/") and not parsed.path.startswith("//"):
        return return_url
    if parsed.scheme not in {"http", "https"}:
        return None
    normalized = urlunparse(parsed._replace(query="", fragment=""))
    for allowed in settings.SSO_ALLOWED_REDIRECT_URIS:
        if normalized.startswith(allowed.rstrip("/")):
            return return_url
    return None


async def _generate_unique_username(base: str, user_repo: UserRepository) -> str:
    candidate = base.lower()
    while True:
        conflict = await user_repo.get_by_email_or_username(candidate)
        if not conflict:
            return candidate
        candidate = f"{base}-{secrets.token_hex(2)}"


def _get_refresh_token_from_request(request: Request, refresh_token: str | None = None) -> str | None:
    token = refresh_token
    if settings.AUTH_REFRESH_TOKEN_TRANSPORT == "cookie":
        token = request.cookies.get("refresh_token") or token
    return token


def _set_refresh_token_cookie(response: JSONResponse | RedirectResponse, refresh_token: str) -> None:
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )


async def _get_or_create_google_user(email: str, name: str | None, db: AsyncSession) -> User:
    user_repo = UserRepository(db)
    existing = await user_repo.get_by_email_or_username(email)
    if existing:
        if not existing.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AUTH_ACCOUNT_DISABLED")
        return existing

    username_base = email.split("@")[0]
    username = await _generate_unique_username(username_base, user_repo)
    user = User(
        email=email.lower(),
        username=username,
        full_name=name,
        password_hash=hash_password(create_random_token()),
        is_active=True,
        is_email_verified=True,
    )
    await user_repo.create(user)
    return user


async def _build_google_auth_url(next: str | None = None) -> str:
    state = quote(next or "", safe="")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_AUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(settings.GOOGLE_AUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{settings.GOOGLE_AUTH_BASE_URL}?{urlencode(params)}"


@router.get("/health", response_model=None)
async def health_check():
    return make_response({"status": "ok"}, "Health check passed")


@router.get("/sso/check", response_model=None)
async def sso_check(
    request: Request,
    next: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    sso_cookie = request.cookies.get(settings.SSO_COOKIE_NAME)
    if sso_cookie:
        try:
            payload = decode_sso_token(sso_cookie)
            if payload.get("type") == "sso":
                user = await UserRepository(db).get_by_id(payload.get("sub"))
                if user and user.is_active:
                    redirect_target = normalize_return_url(next)
                    return RedirectResponse(url=redirect_target or "/", status_code=status.HTTP_303_SEE_OTHER)
        except JWTError:
            pass
    target = "/sso/login"
    if next:
        target += f"?next={quote(next, safe='')}"
    return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", response_model=None)
async def logout(
    next: str | None = Form(None),
):
    redirect_target = normalize_return_url(next)
    response = RedirectResponse(url=redirect_target or "/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(
        settings.SSO_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    response.delete_cookie(
        "refresh_token",
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    return response


@router.post("/refresh", response_model=None)
async def refresh(
    request: Request,
    refresh_token: str | None = Body(None),
    db: AsyncSession = Depends(get_db_session),
):
    token = _get_refresh_token_from_request(request, refresh_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_REFRESH_TOKEN_REQUIRED")

    session_repo = AuthSessionRepository(db)
    session = await session_repo.get_by_refresh_token_hash(hash_token(token))
    if not session or not session.is_active or session.expires_at < now_utc():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_REFRESH_TOKEN_INVALID")

    user = await UserRepository(db).get_by_id(session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_ACCOUNT_DISABLED")

    new_refresh_token = create_refresh_token()
    new_refresh_token_hash = hash_token(new_refresh_token)
    expires_at = now_utc() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await session_repo.rotate_refresh_token(session.id, new_refresh_token_hash, expires_at, current_token_jti=uuid.uuid4())

    access_token = create_access_token(str(user.id), str(session.id))
    response_data = {"access_token": access_token}
    if settings.AUTH_REFRESH_TOKEN_TRANSPORT != "cookie":
        response_data["refresh_token"] = new_refresh_token

    response = make_response(response_data, "Token refreshed")
    if settings.AUTH_REFRESH_TOKEN_TRANSPORT == "cookie":
        _set_refresh_token_cookie(response, new_refresh_token)
    return response


@router.get("/google/login", response_model=None)
async def google_login(
    next: str | None = None,
):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_OAUTH_NOT_CONFIGURED")

    redirect_target = normalize_return_url(next)
    auth_url = await _build_google_auth_url(redirect_target)
    return RedirectResponse(url=auth_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/google/callback", response_model=None)
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_OAUTH_NO_CODE")

    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_OAUTH_NOT_CONFIGURED")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            settings.GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_AUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_OAUTH_TOKEN_EXCHANGE_FAILED")

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_OAUTH_NO_ACCESS_TOKEN")

        userinfo_response = await client.get(
            settings.GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_OAUTH_USERINFO_FAILED")

    profile = userinfo_response.json()
    email = profile.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GOOGLE_OAUTH_NO_EMAIL")

    user = await _get_or_create_google_user(email, profile.get("name"), db)
    session_repo = AuthSessionRepository(db)
    refresh_token = create_refresh_token()
    refresh_token_hash = hash_token(refresh_token)
    expires_at = now_utc() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    auth_session = await session_repo.create(
        user.id,
        refresh_token_hash,
        expires_at,
        device_name="Google OAuth",
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        current_token_jti=uuid.uuid4(),
    )
    access_token = create_access_token(str(user.id), str(auth_session.id))
    sso_token = create_sso_token(str(user.id))
    redirect_target = normalize_return_url(unquote(state or ""))
    response = RedirectResponse(url=redirect_target or "/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        settings.SSO_COOKIE_NAME,
        sso_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=settings.SSO_COOKIE_EXPIRE_DAYS * 24 * 3600,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    if settings.AUTH_REFRESH_TOKEN_TRANSPORT == "cookie":
        _set_refresh_token_cookie(response, refresh_token)
    return response


@router.post("/login", response_model=None)
async def login(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    device_name: str | None = Form(None),
    next: str | None = Form(None),
    db: AsyncSession = Depends(get_db_session),
):
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email_or_username(login)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_INVALID_CREDENTIALS")

    session_repo = AuthSessionRepository(db)
    refresh_token = create_refresh_token()
    refresh_token_hash = hash_token(refresh_token)
    expires_at = now_utc() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    auth_session = await session_repo.create(
        user.id,
        refresh_token_hash,
        expires_at,
        device_name=device_name,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        current_token_jti=uuid.uuid4(),
    )
    access_token = create_access_token(str(user.id), str(auth_session.id))
    sso_token = create_sso_token(str(user.id))

    response: JSONResponse | RedirectResponse
    redirect_target = normalize_return_url(next)
    if redirect_target:
        response = RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)
    else:
        response = make_response({"user_id": str(user.id), "access_token": access_token, "refresh_token": refresh_token}, "Login successful")

    response.set_cookie(
        settings.SSO_COOKIE_NAME,
        sso_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=settings.SSO_COOKIE_EXPIRE_DAYS * 24 * 3600,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    if settings.AUTH_REFRESH_TOKEN_TRANSPORT == "cookie":
        _set_refresh_token_cookie(response, refresh_token)
    return response
