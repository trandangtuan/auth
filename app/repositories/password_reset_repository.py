from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.password_reset_token import PasswordResetToken


class PasswordResetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self.session.execute(
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalars().first()

    async def invalidate_old_tokens(self, user_id: str) -> None:
        await self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .values(used_at=datetime.utcnow())
        )
