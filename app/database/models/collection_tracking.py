from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CollectionTracking(Base):
    __tablename__ = "collection_trackings"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "contract_address",
            name="uq_collection_tracking_user_contract",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    contract_address: Mapped[str] = mapped_column(
        String(42),
        nullable=False,
        index=True,
    )

    collection_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    blockchain: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ethereum",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )