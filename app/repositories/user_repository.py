import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str | uuid.UUID) -> User | None:
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return None

        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_by_email_or_username(self, login: str) -> User | None:
        login_lower = login.strip().lower()
        result = await self.session.execute(
            select(User).where((User.email == login_lower) | (User.username == login_lower))
        )
        return result.scalars().first()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def save(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
