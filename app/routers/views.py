from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import urlencode
from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import decode_sso_token
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.routers.auth import normalize_return_url

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _template_context(request: Request) -> dict:
    next_url = request.query_params.get("next", "")
    google_login_url = "/api/auth/google/login"
    if next_url:
        google_login_url += f"?{urlencode({'next': next_url})}"
    return {
        "request": request,
        "next_url": next_url,
        "google_login_url": google_login_url,
    }


async def _get_current_user(request: Request, db: AsyncSession) -> User | None:
    sso_cookie = request.cookies.get(settings.SSO_COOKIE_NAME)
    if not sso_cookie:
        return None
    try:
        payload = decode_sso_token(sso_cookie)
    except JWTError:
        return None
    user = await UserRepository(db).get_by_id(payload.get("sub"))
    if not user or not user.is_active:
        return None
    return user


@router.get("/register", response_class=HTMLResponse)
async def register_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "register.html", _template_context(request))


@router.get("/login", response_class=HTMLResponse)
async def login_view(
    request: Request,
    next: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    current_user = await _get_current_user(request, db)
    if current_user:
        redirect_target = normalize_return_url(next)
        return RedirectResponse(url=redirect_target or "/profile", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", _template_context(request))


@router.get("/sso/login", response_class=HTMLResponse)
async def sso_login_view(
    request: Request,
    next: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    current_user = await _get_current_user(request, db)
    if current_user:
        redirect_target = normalize_return_url(next)
        return RedirectResponse(url=redirect_target or "/profile", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", _template_context(request))


@router.get("/logout", response_model=None)
async def logout_view(request: Request) -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(
        settings.SSO_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )
    return response


@router.get("/profile", response_class=HTMLResponse)
async def profile_view(request: Request, db: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    current_user = await _get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "profile.html", {"request": request, "user": current_user})


@router.get("/oauth/register", response_class=HTMLResponse)
async def oauth_register_view(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "oauth_register.html")
