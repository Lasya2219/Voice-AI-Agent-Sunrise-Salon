from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class StylistService(Base):
    __tablename__ = "stylist_services"

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"),
        primary_key=True
    )

    stylist_id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "stylist_id"],
            ["stylists.business_id", "stylists.id"],
            ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["business_id", "service_id"],
            ["services.business_id", "services.id"],
            ondelete="CASCADE"
        ),
    )