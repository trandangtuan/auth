from datetime import datetime
from app.core.security import create_random_token, hash_token, now_utc, get_expiration
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.user_repository import UserRepository
from app.models.password_reset_token import PasswordResetToken
from app.core.security import validate_password_strength, hash_password, verify_password


class PasswordService:
    def __init__(self, user_repo: UserRepository, reset_repo: PasswordResetRepository) -> None:
        self.user_repo = user_repo
        self.reset_repo = reset_repo

    async def create_reset_token(self, user_id: str, request_ip: str | None = None) -> str:
        raw_token = create_random_token()
        token_hash = hash_token(raw_token)
        await self.reset_repo.invalidate_old_tokens(user_id)
        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=get_expiration(minutes=15),
            request_ip=request_ip,
        )
        await self.reset_repo.create(reset_token)
        return raw_token

    async def validate_reset_token(self, raw_token: str) -> PasswordResetToken | None:
        token_hash = hash_token(raw_token)
        token = await self.reset_repo.get_by_token_hash(token_hash)
        if not token or token.used_at or token.expires_at < now_utc():
            return None
        return token

    async def reset_password(
        self,
        token_obj: PasswordResetToken,
        new_password: str,
        confirm_password: str,
    ) -> None:
        if new_password != confirm_password:
            raise ValueError("AUTH_PASSWORD_MISMATCH")
        validate_password_strength(new_password)
        user = await self.user_repo.get_by_id(token_obj.user_id)
        if not user or not user.is_active:
            raise ValueError("AUTH_ACCOUNT_DISABLED")
        if verify_password(new_password, user.password_hash):
            raise ValueError("AUTH_NEW_PASSWORD_SAME_AS_OLD")
        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        token_obj.used_at = datetime.utcnow()
        self.user_repo.session.add(user)
        self.reset_repo.session.add(token_obj)
        await self.user_repo.session.flush()
