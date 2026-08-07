from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.utcnow()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
