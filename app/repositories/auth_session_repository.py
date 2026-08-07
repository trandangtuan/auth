import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.auth_session import AuthSession


class AuthSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, session_id: str | uuid.UUID) -> AuthSession | None:
        if isinstance(session_id, str):
            try:
                session_id = uuid.UUID(session_id)
            except ValueError:
                return None

        result = await self.session.execute(select(AuthSession).where(AuthSession.id == session_id))
        return result.scalars().first()

    async def get_by_refresh_token_hash(self, refresh_token_hash: str) -> AuthSession | None:
        result = await self.session.execute(
            select(AuthSession).where(AuthSession.refresh_token_hash == refresh_token_hash)
        )
        return result.scalars().first()

    async def get_by_user_and_session(self, user_id: str | uuid.UUID, session_id: str | uuid.UUID) -> AuthSession | None:
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return None
        if isinstance(session_id, str):
            try:
                session_id = uuid.UUID(session_id)
            except ValueError:
                return None

        result = await self.session.execute(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.id == session_id,
            )
        )
        return result.scalars().first()

    async def create(
        self,
        user_id: str | uuid.UUID,
        refresh_token_hash: str,
        expires_at,
        device_name: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
        current_token_jti: uuid.UUID | None = None,
    ) -> AuthSession:
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        auth_session = AuthSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
            current_token_jti=current_token_jti or uuid.uuid4(),
        )
        self.session.add(auth_session)
        await self.session.flush()
        return auth_session

    async def rotate_refresh_token(
        self,
        session_id: str | uuid.UUID,
        new_refresh_token_hash: str,
        new_expires_at,
        current_token_jti: uuid.UUID | None = None,
    ) -> AuthSession | None:
        session = await self.get_by_id(session_id)
        if not session:
            return None

        session.refresh_token_hash = new_refresh_token_hash
        session.expires_at = new_expires_at
        session.current_token_jti = current_token_jti or uuid.uuid4()
        session.last_used_at = datetime.now(timezone.utc)
        self.session.add(session)
        await self.session.flush()
        return session
