import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, utc_now


class AuthSession(Base, TimestampMixin):
    __tablename__ = "auth_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(Text, nullable=False)
    refresh_token_family_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    current_token_jti = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)

    device_name = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoke_reason = Column(String(255), nullable=True)

    user = relationship("User", backref="sessions")
