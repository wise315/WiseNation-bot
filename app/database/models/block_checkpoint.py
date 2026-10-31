
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class BlockCheckpoint(Base):
    __tablename__ = "block_checkpoints"

    __table_args__ = (
        UniqueConstraint(
            "chain_id",
            name="uq_block_checkpoints_chain_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    chain_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    last_processed_block: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    block_hash: Mapped[str | None] = mapped_column(
        String(66),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
