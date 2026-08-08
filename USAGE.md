# Hướng dẫn sử dụng Authentication Module

Tài liệu này tập trung vào luồng đăng nhập SSO, vì đây là phần quan trọng nhất khi kết nối Auth Service với các ứng dụng khác.

## Chạy local

```bash
docker compose up --build
docker compose exec backend alembic upgrade head
```

Mở:

```text
http://localhost:8000/login
```

## Cấu hình tối thiểu

Ví dụ cấu hình local trong `docker-compose.yml`:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
AUTH_REFRESH_TOKEN_TRANSPORT=cookie
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
AUTH_COOKIE_DOMAIN=
SSO_COOKIE_NAME=sso_session
SSO_ALLOWED_REDIRECT_URIS=["http://localhost:5174/oauth/callback"]
OAUTH_CLIENTS={"web-client":{"secret":"web-secret","redirect_uris":["http://localhost:5174/oauth/callback"]}}
CORS_ORIGINS=["http://localhost:5173"]
```

`SSO_ALLOWED_REDIRECT_URIS` dùng để chặn open redirect. Chỉ các URL nằm trong danh sách này mới được dùng làm `next`.

`OAUTH_CLIENTS` dùng cho OAuth authorization code flow. `redirect_uri` gửi lên phải khớp với một URL trong `redirect_uris` của client.

## Đăng nhập SSO cho app bên ngoài

App bên ngoài redirect người dùng đến:

```text
http://localhost:8000/api/auth/sso/check?next=http://localhost:5174/oauth/callback
```

Kết quả:

- Nếu đã có cookie `sso_session` hợp lệ, Auth Service redirect thẳng về `next`.
- Nếu chưa đăng nhập, Auth Service redirect tới `/sso/login?next=...`.
- Sau khi login thành công, Auth Service đặt cookie SSO và redirect về `next`.

Form login SSO gửi request:

```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

login=user@example.com&password=StrongPassword123!&next=http://localhost:5174/oauth/callback
```

Response thành công có redirect `303` về `next` và set cookie:

```text
sso_session=<jwt>; HttpOnly; Path=/
refresh_token=<token>; HttpOnly; Path=/
```

## OAuth authorization code flow

Dùng luồng này khi app cần lấy access token riêng và thông tin user.

### 1. Redirect tới authorize

```text
http://localhost:8000/oauth/authorize?client_id=web-client&redirect_uri=http://localhost:5174/oauth/callback&response_type=code&state=random-state
```

Nếu user đã có SSO, Auth Service redirect về:

```text
http://localhost:5174/oauth/callback?code=<code>&state=random-state
```

### 2. Đổi code lấy token

```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=<code>" \
  -d "redirect_uri=http://localhost:5174/oauth/callback" \
  -d "client_id=web-client" \
  -d "client_secret=web-secret"
```

Response:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 3600,
  "scope": "openid profile email",
  "user": {
    "sub": "...",
    "id": "...",
    "email": "user@example.com",
    "username": "demo",
    "name": "Nguyen Van A",
    "email_verified": true
  }
}
```

### 3. Lấy user info

```bash
curl http://localhost:8000/oauth/userinfo \
  -H "Authorization: Bearer <access_token>"
```

## API đăng ký

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "demo",
    "password": "StrongPassword123!",
    "confirm_password": "StrongPassword123!",
    "full_name": "Nguyen Van A"
  }'
```

Mật khẩu cần có ít nhất 8 ký tự, chữ thường, chữ hoa, số và ký tự đặc biệt.

## API đăng nhập thường

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "login=user@example.com" \
  -d "password=StrongPassword123!" \
  -d "device_name=Chrome on Ubuntu"
```

Nếu không truyền `next`, API trả JSON có `access_token`. Nếu có `next` hợp lệ, API redirect và set cookie SSO.

## Đăng xuất

Đăng xuất bằng web view:

```text
GET /logout
```

Đăng xuất bằng API:

```http
POST /api/auth/logout
Content-Type: application/x-www-form-urlencoded

next=http://localhost:5174/oauth/callback
```

API xóa `sso_session` và `refresh_token`, sau đó redirect về `next` nếu URL hợp lệ.

## Checklist kiểm lỗi SSO

- `next` hoặc `redirect_uri` phải nằm trong allowlist.
- Với OAuth, `client_id`, `client_secret` và `redirect_uri` phải khớp `OAUTH_CLIENTS`.
- Authorization code chỉ dùng một lần và hết hạn sau `OAUTH_CODE_EXPIRE_SECONDS`.
- Browser chỉ gửi cookie đúng domain/path/samesite. Khi production dùng HTTPS, bật `AUTH_COOKIE_SECURE=true`.
- Nếu nhiều app chạy trên subdomain, cấu hình `AUTH_COOKIE_DOMAIN` về domain chung, ví dụ `.example.com`.
- Không dùng `JWT_SECRET_KEY` demo ở production.

## Endpoint nhanh

- `GET /api/auth/sso/check` - kiểm tra phiên SSO và redirect.
- `POST /api/auth/login` - đăng nhập, đặt SSO cookie nếu login thành công.
- `POST /api/auth/logout` - xóa SSO cookie và refresh cookie.
- `GET /oauth/authorize` - tạo authorization code.
- `POST /oauth/token` - đổi code lấy access token.
- `GET /oauth/userinfo` - lấy thông tin user từ OAuth access token.
- `GET /api/auth/google/login` - bắt đầu Google OAuth.
- `GET /api/auth/google/callback` - callback Google OAuth.
