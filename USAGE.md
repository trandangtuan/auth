# Hướng dẫn sử dụng Authentication Module

## Khởi động môi trường

1. Sao chép file cấu hình:
   ```bash
   cp .env.example .env
   ```
2. Chỉnh sửa `.env` nếu cần.
3. Khởi động dịch vụ bằng Docker Compose:
   ```bash
   docker compose up --build
   ```
4. Chạy migration:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
5. Mở ứng dụng tại:
   ```
   http://localhost:8000
   ```

## Các endpoint chính

- `POST /api/auth/register` - Đăng ký người dùng mới.
- `POST /api/auth/login` - Đăng nhập với email hoặc username.
- `POST /api/auth/refresh` - Làm mới access token.
- `POST /api/auth/logout` - Đăng xuất.
- `POST /api/auth/logout-all` - Đăng xuất tất cả thiết bị.
- `GET /api/auth/me` - Lấy thông tin người dùng hiện tại.
- `POST /api/auth/forgot-password` - Yêu cầu đặt lại mật khẩu.
- `POST /api/auth/validate-reset-token` - Kiểm tra tính hợp lệ token đặt lại mật khẩu.
- `POST /api/auth/reset-password` - Đặt lại mật khẩu.
- `POST /api/auth/change-password` - Đổi mật khẩu khi đăng nhập.
- `POST /api/auth/resend-verification-email` - Gửi lại email xác thực.
- `POST /api/auth/verify-email` - Xác thực email.
- `GET /api/auth/sessions` - Liệt kê phiên đăng nhập.
- `DELETE /api/auth/sessions/{session_id}` - Thu hồi một phiên.
- `GET /api/auth/sso/check` - Kiểm tra SSO hiện có và redirect về ứng dụng.
- `GET /sso/login` - Form đăng nhập SSO.
- `POST /api/auth/logout` - Đăng xuất SSO.

## Sử dụng SSO

1. Ứng dụng thứ ba chuyển hướng người dùng tới:
   ```
   /api/auth/sso/check?next=https://app.example.com/callback
   ```
2. Nếu đã đăng nhập, backend sẽ redirect về `next` ngay.
3. Nếu chưa đăng nhập, backend sẽ redirect tới `/sso/login?next=...`.
4. Sau khi login thành công, backend sẽ trả về `next` và đặt cookie SSO.

## Sử dụng API đăng ký

Request:
```json
{
  "email": "user@example.com",
  "username": "demo",
  "password": "StrongPassword123!",
  "confirm_password": "StrongPassword123!",
  "full_name": "Nguyễn Văn A"
}
```

## Sử dụng API đăng nhập

Request:
```json
{
  "login": "user@example.com",
  "password": "StrongPassword123!",
  "device_name": "Chrome on Ubuntu"
}
```

## Ghi chú

- Backend hiện tại không dùng Redis. Token blacklist và rate limiting không được cấu hình trong phiên bản này.
- Reset password token chỉ lưu hash trong database.
- Access token là JWT, refresh token không lưu trong database dưới dạng plaintext.
- Trong môi trường phát triển, reset token có thể được trả về trực tiếp để test.
