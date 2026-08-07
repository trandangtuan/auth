import json
import os
from functools import lru_cache
from typing import Any
from pydantic import AnyUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Multi User AI Client"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    AUTH_MAX_LOGIN_ATTEMPTS: int = 5
    AUTH_LOCK_MINUTES: int = 15

    AUTH_REFRESH_TOKEN_TRANSPORT: str = "cookie"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_COOKIE_DOMAIN: str | None = None
    AUTH_RETURN_RESET_TOKEN_IN_RESPONSE: bool = False

    OAUTH_CLIENT_ID: str = "demo-client"
    OAUTH_CLIENT_SECRET: str = "demo-secret"
    OAUTH_REDIRECT_URIS: list[str] = [
        "http://localhost/auth/callback",
        "http://localhost:5174/oauth/callback",
    ]
    OAUTH_CODE_EXPIRE_SECONDS: int = 300

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_AUTH_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    GOOGLE_AUTH_SCOPES: list[str] = ["openid", "email", "profile"]
    GOOGLE_AUTH_BASE_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL: str = "https://openidconnect.googleapis.com/v1/userinfo"

    SSO_COOKIE_NAME: str = "sso_session"
    SSO_COOKIE_EXPIRE_DAYS: int = 7
    SSO_ALLOWED_REDIRECT_URIS: list[str] = ["http://localhost:5174/oauth/callback"]

    FRONTEND_URL: str = "http://localhost:5173"
    PASSWORD_RESET_URL: str = "http://localhost:5173/reset-password"
    EMAIL_VERIFICATION_URL: str = "http://localhost:5173/verify-email"

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v: str) -> str:
        if v.startswith("replace-with") or len(v) < 32:
            if os.getenv("APP_ENV") == "production":
                raise ValueError("JWT secret key is too weak for production")
        return v

    @validator("AUTH_COOKIE_SECURE")
    def validate_cookie_security(cls, v: bool) -> bool:
        if os.getenv("APP_ENV") == "production" and not v:
            raise ValueError("AUTH_COOKIE_SECURE must be true in production")
        return v

    @validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v: list[str]) -> list[str]:
        if os.getenv("APP_ENV") == "production" and "*" in v:
            raise ValueError("CORS '*' with credentials is forbidden in production")
        return v

    @validator("OAUTH_REDIRECT_URIS", pre=True)
    def normalize_oauth_redirects(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @validator("GOOGLE_AUTH_SCOPES", pre=True)
    def normalize_google_scopes(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @validator("SSO_ALLOWED_REDIRECT_URIS", pre=True)
    def normalize_sso_redirects(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return [item.strip() for item in v.split(",") if item.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
