import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, utc_now


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String(255), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    is_email_verified = Column(Boolean, nullable=False, default=False)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
