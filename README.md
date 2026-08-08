# Authentication Module

Module xác thực cho hệ thống multi-app, xây bằng FastAPI, SQLAlchemy Async, SQLite, Alembic, Pydantic Settings, JWT, Argon2 và Docker Compose.

Trọng tâm của module là đăng nhập tập trung bằng SSO: người dùng đăng nhập một lần tại Auth Service, sau đó các ứng dụng khác có thể kiểm tra phiên SSO và nhận người dùng quay lại qua redirect an toàn.

## Chức năng chính

- Đăng ký tài khoản bằng email, username và mật khẩu.
- Đăng nhập bằng email hoặc username.
- Đăng nhập SSO bằng cookie `sso_session`.
- Kiểm tra SSO cho ứng dụng bên ngoài qua `/api/auth/sso/check`.
- OAuth 2.0 authorization code flow nội bộ qua `/oauth/authorize`, `/oauth/token`, `/oauth/userinfo`.
- Đăng nhập Google OAuth, tự tạo user nếu email chưa tồn tại.
- Access token JWT và refresh token rotation.
- Refresh token qua HTTP-only cookie hoặc body, tùy cấu hình.
- Đăng xuất SSO và xóa refresh cookie.
- Quản lý phiên đăng nhập.
- Quên mật khẩu, reset mật khẩu, đổi mật khẩu.
- Xác thực email.

## Khởi động nhanh

```bash
docker compose up --build
docker compose exec backend alembic upgrade head
```

API chạy tại:

```text
https://auth.tdshift.info
```

Trang đăng nhập:

```text
https://auth.tdshift.info/login
```

## Cấu hình quan trọng cho SSO

Các biến cần kiểm tra kỹ trong `docker-compose.yml` hoặc `.env`:

```env
JWT_SECRET_KEY=change-this-to-a-long-random-production-secret
OAUTH_CHAT_CLIENT_SECRET=change-this-to-the-same-secret-used-by-chat
AUTH_REFRESH_TOKEN_TRANSPORT=cookie
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
AUTH_COOKIE_DOMAIN=.tdshift.info
SSO_COOKIE_NAME=sso_session
SSO_COOKIE_EXPIRE_DAYS=7
SSO_ALLOWED_REDIRECT_URIS=["https://chat.tdshift.info/auth/callback"]
OAUTH_CLIENTS={"chat-ai":{"secret":"<same-as-OAUTH_CHAT_CLIENT_SECRET>","redirect_uris":["https://chat.tdshift.info/auth/callback"]}}
CORS_ORIGINS=["https://auth.tdshift.info","https://chat.tdshift.info"]
```

Lưu ý production:

- `JWT_SECRET_KEY` phải đủ dài, ngẫu nhiên và không dùng giá trị demo.
- `AUTH_COOKIE_SECURE=true` khi chạy HTTPS.
- `AUTH_COOKIE_DOMAIN` cần đúng domain chung nếu nhiều app dùng chung SSO trên subdomain.
- `SSO_ALLOWED_REDIRECT_URIS` phải chứa đúng URL app được phép nhận redirect.
- `OAUTH_CLIENTS.*.redirect_uris` phải khớp tuyệt đối với `redirect_uri` khi gọi OAuth.

## Luồng SSO

Ứng dụng bên ngoài chuyển người dùng tới Auth Service:

```text
GET /api/auth/sso/check?next=https://chat.tdshift.info/auth/callback
```

Nếu cookie `sso_session` hợp lệ, Auth Service redirect ngay về `next`.

Nếu chưa có phiên SSO, Auth Service redirect tới:

```text
/sso/login?next=https%3A%2F%2Fchat.tdshift.info%2Fauth%2Fcallback
```

Sau khi người dùng đăng nhập thành công, Auth Service đặt cookie `sso_session`, đặt cookie `refresh_token` nếu cấu hình dùng cookie, rồi redirect về `next`.

## Luồng OAuth nội bộ

OAuth flow dùng khi app bên ngoài muốn đổi authorization code lấy access token và user info.

1. App redirect trình duyệt tới:

   ```text
   GET /oauth/authorize?client_id=chat-ai&redirect_uri=https://chat.tdshift.info/auth/callback&response_type=code&state=abc
   ```

2. Nếu người dùng chưa đăng nhập SSO, Auth Service chuyển về `/login?next=...`.

3. Nếu đã đăng nhập, Auth Service redirect về `redirect_uri` kèm `code` và `state`.

4. App đổi code lấy token:

   ```bash
   curl -X POST https://auth.tdshift.info/oauth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=authorization_code" \
     -d "code=<code>" \
     -d "redirect_uri=https://chat.tdshift.info/auth/callback" \
     -d "client_id=chat-ai" \
     -d "client_secret=<OAUTH_CHAT_CLIENT_SECRET>"
   ```

5. App lấy user info:

   ```bash
   curl https://auth.tdshift.info/oauth/userinfo \
     -H "Authorization: Bearer <access_token>"
   ```

## Endpoint chính

### Auth API

- `GET /api/auth/health`
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
- `GET /api/auth/sso/check`
- `GET /api/auth/google/login`
- `GET /api/auth/google/callback`

### OAuth API

- `GET /oauth/authorize`
- `POST /oauth/authorize`
- `POST /oauth/token`
- `GET /oauth/userinfo`

### Web views

- `GET /login`
- `GET /sso/login`
- `GET /register`
- `GET /profile`
- `GET /logout`
- `GET /oauth/register`

## Lỗi thường gặp khi tích hợp SSO

- Đăng nhập xong không quay về app: kiểm tra `next` có nằm trong `SSO_ALLOWED_REDIRECT_URIS` không.
- `/oauth/token` trả `invalid_grant`: code đã dùng, hết hạn, sai `client_id`, hoặc sai `redirect_uri`.
- `/oauth/authorize` trả `INVALID_REDIRECT_URI`: `redirect_uri` không khớp cấu hình `OAUTH_CLIENTS`.
- Cookie không lưu trên browser: kiểm tra HTTPS, `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`, domain và port.
- Google login báo `GOOGLE_OAUTH_NOT_CONFIGURED`: thiếu `GOOGLE_CLIENT_ID` hoặc `GOOGLE_CLIENT_SECRET`.

## Kiểm tra

```bash
pytest -q
```
