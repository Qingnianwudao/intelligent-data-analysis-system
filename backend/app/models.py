from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppSession(Base):
    __tablename__ = "app_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    messages: Mapped[list["AppMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="AppMessage.id"
    )


class AppMessage(Base):
    __tablename__ = "app_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("app_sessions.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text, default="")
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["AppSession"] = relationship(back_populates="messages")
