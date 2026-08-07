from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
from fastapi import APIRouter, HTTPException, status, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import create_random_token, now_utc, get_expiration, hash_token
from app.core.security import decode_sso_token
from app.repositories.user_repository import UserRepository

router = APIRouter()

oauth_codes: dict[str, dict] = {}
oauth_tokens: dict[str, dict] = {}


def validate_client(client_id: str, redirect_uri: str) -> None:
    if client_id != settings.OAUTH_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CLIENT")
    if redirect_uri not in settings.OAUTH_REDIRECT_URIS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_REDIRECT_URI")


def add_query_params(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(params)
    return urlunparse(parsed._replace(query=urlencode(query)))


async def get_sso_user(request: Request, db: AsyncSession):
    token = request.cookies.get(settings.SSO_COOKIE_NAME)
    if not token:
        return None
    try:
        payload = decode_sso_token(token)
    except JWTError:
        return None
    user = await UserRepository(db).get_by_id(payload.get("sub"))
    return user if user and user.is_active else None


async def create_authorization_response(
    request: Request,
    client_id: str,
    redirect_uri: str,
    response_type: str,
    state: str | None,
    db: AsyncSession,
) -> RedirectResponse:
    validate_client(client_id, redirect_uri)
    if response_type != "code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_response_type")

    user = await get_sso_user(request, db)
    if not user:
        authorize_url = request.url.path
        if request.url.query:
            authorize_url += f"?{request.url.query}"
        login_url = add_query_params("/login", {"next": authorize_url})
        return RedirectResponse(url=login_url, status_code=status.HTTP_303_SEE_OTHER)

    code = create_random_token()
    oauth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "user_id": str(user.id),
        "expires_at": get_expiration(seconds=settings.OAUTH_CODE_EXPIRE_SECONDS),
        "used": False,
    }
    params = {"code": code}
    if state:
        params["state"] = state
    return RedirectResponse(url=add_query_params(redirect_uri, params), status_code=status.HTTP_303_SEE_OTHER)


def serialize_user(user) -> dict[str, str | bool | None]:
    return {
        "sub": str(user.id),
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "name": user.full_name,
        "email_verified": user.is_email_verified,
    }


@router.get("/oauth/authorize", response_model=None)
async def oauth_authorize_get(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    return await create_authorization_response(request, client_id, redirect_uri, response_type, state, db)


@router.post("/oauth/authorize", response_model=None)
async def oauth_authorize(
    request: Request,
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    response_type: str = Form(...),
    state: str | None = Form(None),
    db: AsyncSession = Depends(get_db_session),
):
    return await create_authorization_response(request, client_id, redirect_uri, response_type, state, db)


@router.post("/oauth/token", response_model=None)
async def oauth_token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
):
    if grant_type != "authorization_code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_grant_type")
    validate_client(client_id, redirect_uri)
    if client_secret != settings.OAUTH_CLIENT_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_client")
    stored = oauth_codes.get(code)
    if not stored or stored["used"] or stored["client_id"] != client_id or stored["redirect_uri"] != redirect_uri:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant")
    if stored["expires_at"] < now_utc():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant")
    stored["used"] = True
    access_token = create_random_token()
    oauth_tokens[hash_token(access_token)] = {
        "user_id": stored["user_id"],
        "expires_at": get_expiration(seconds=3600),
    }
    user = await UserRepository(db).get_by_id(stored["user_id"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_grant")
    return JSONResponse({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": "openid profile email",
        "user": serialize_user(user),
    })


@router.get("/oauth/userinfo", response_model=None)
async def oauth_userinfo(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    token_data = oauth_tokens.get(hash_token(authorization[7:].strip()))
    if not token_data or token_data["expires_at"] < now_utc():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    user = await UserRepository(db).get_by_id(token_data["user_id"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    return JSONResponse(serialize_user(user))
