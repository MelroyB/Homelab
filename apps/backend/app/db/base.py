from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData()

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class DictReprMixin:
    def to_dict(self) -> dict[str, Any]:
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns  # type: ignore[attr-defined]
        }
