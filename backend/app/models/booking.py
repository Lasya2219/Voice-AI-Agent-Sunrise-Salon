from sqlalchemy import (
    Integer, String, DateTime, Boolean, ForeignKey,
    ForeignKeyConstraint, CheckConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )

    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    stylist_id: Mapped[int] = mapped_column(Integer, nullable=False)
    service_id: Mapped[int] = mapped_column(Integer, nullable=False)

    start_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    end_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default="confirmed", nullable=False
    )

    cancelled_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    late_cancel: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "customer_id"],
            ["customers.business_id", "customers.id"]
        ),
        ForeignKeyConstraint(
            ["business_id", "stylist_id"],
            ["stylists.business_id", "stylists.id"]
        ),
        ForeignKeyConstraint(
            ["business_id", "service_id"],
            ["services.business_id", "services.id"]
        ),
        CheckConstraint("end_time > start_time"),
        CheckConstraint(
            "status IN ('confirmed', 'cancelled', 'done')"
        ),
    )