from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Kolkata", nullable=False
    )

    slot_duration_minutes: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )

    cancellation_window_minutes: Mapped[int] = mapped_column(
        Integer, default=120, nullable=False
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )