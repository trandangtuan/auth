from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from app.core.config import settings
from app.core.security import create_random_token, now_utc, get_expiration, hash_token

router = APIRouter()

oauth_codes: dict[str, dict] = {}


def validate_client(client_id: str, redirect_uri: str) -> None:
    if client_id != settings.OAUTH_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CLIENT")
    if redirect_uri not in settings.OAUTH_REDIRECT_URIS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_REDIRECT_URI")


@router.post("/oauth/authorize", response_model=None)
async def oauth_authorize(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    response_type: str = Form(...),
    state: str | None = Form(None),
):
    validate_client(client_id, redirect_uri)
    if response_type != "code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_response_type")
    code = create_random_token()
    expires_at = get_expiration(seconds=settings.OAUTH_CODE_EXPIRE_SECONDS)
    oauth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "expires_at": expires_at,
        "used": False,
    }
    params = f"?code={code}"
    if state:
        params += f"&state={state}"
    return RedirectResponse(url=f"{redirect_uri}{params}")


@router.post("/oauth/token", response_model=None)
async def oauth_token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
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
    return JSONResponse({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": "openid profile email",
    })
