import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, utc_now


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    request_ip = Column(String(64), nullable=True)

    user = relationship("User", backref="password_reset_tokens")
