from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import decode_sso_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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
    return templates.TemplateResponse(request, "register.html")


@router.get("/login", response_class=HTMLResponse)
async def login_view(request: Request, db: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    current_user = await _get_current_user(request, db)
    if current_user:
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html")


@router.get("/sso/login", response_class=HTMLResponse)
async def sso_login_view(request: Request, db: AsyncSession = Depends(get_db_session)) -> HTMLResponse:
    current_user = await _get_current_user(request, db)
    if current_user:
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html")


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
