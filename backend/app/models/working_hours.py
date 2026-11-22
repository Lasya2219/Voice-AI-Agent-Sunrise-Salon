from sqlalchemy import (
    Integer, Time, ForeignKey, ForeignKeyConstraint,
    CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class WorkingHours(Base):
    __tablename__ = "working_hours"

    id: Mapped[int] = mapped_column(primary_key=True)

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False
    )

    stylist_id: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)

    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "stylist_id"],
            ["stylists.business_id", "stylists.id"],
            ondelete="CASCADE"
        ),
        CheckConstraint("weekday >= 0 AND weekday <= 6"),
        CheckConstraint("end_time > start_time"),
    )