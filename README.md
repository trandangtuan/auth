# Multi User AI Client - Authentication Module

This repository contains a working authentication microservice built with FastAPI, SQLite, SQLAlchemy Async, Alembic, Pydantic v2, JWT, Argon2, and Docker Compose.

## Features

- User registration
- Login with email or username
- Logout and logout-all
- Access token / refresh token rotation
- Password reset flow
- Change password
- Email verification
- Session management
- Account lockout after failed login attempts
- Rate limiting for critical endpoints

## Local Setup

1. Copy `.env.example` to `.env` and adjust values.
2. Start services:
   ```bash
   docker compose up --build
   ```
3. Run migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
4. The API server will be available at `http://localhost:8000`.

## API Endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password`
- `POST /api/auth/validate-reset-token`
- `POST /api/auth/reset-password`
- `POST /api/auth/change-password`
- `POST /api/auth/resend-verification-email`
- `POST /api/auth/verify-email`
- `GET /api/auth/sessions`
- `DELETE /api/auth/sessions/{session_id}`
- `POST /oauth/authorize`
- `POST /oauth/token`
- `GET /api/auth/google/login`
- `GET /api/auth/google/callback`
- `GET /profile`
- `GET /logout`
- `GET /api/auth/sso/check`
- `GET /sso/login`

## OAuth Provider Simulation

This backend includes a simple OAuth 2.0 authorization code flow for external apps.- Google OAuth login flow for end users.
- `POST /oauth/authorize` - redirect to the provided `redirect_uri` with an authorization code.
- `POST /oauth/token` - exchange the code for an access token.

## SSO Session Support

This backend supports SSO session checks across multiple applications. External apps can redirect users to `/api/auth/sso/check?next=<return_url>`.

- If the user already has an active SSO session cookie, they are redirected back to the app immediately.
- If the user does not have an active SSO session, they are redirected to `/sso/login?next=<return_url>`.
- After successful login, the user is redirected back to the original `next` URL.

## Testing

Run tests with:

```bash
pytest -q
```
