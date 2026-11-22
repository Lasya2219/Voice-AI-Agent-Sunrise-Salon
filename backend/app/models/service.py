from sqlalchemy import (
    String, Integer, Boolean, Numeric, Text,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Service(Base):
    __tablename__ = "services"

    __table_args__ = (
        UniqueConstraint("business_id", "name"),
        UniqueConstraint("business_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_price_from: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)