from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CanonicalBlock(Base):
    __tablename__ = "canonical_blocks"

    __table_args__ = (
        UniqueConstraint(
            "chain_id",
            "block_number",
            name="uq_canonical_blocks_chain_block",
        ),
        Index(
            "ix_canonical_blocks_chain_block",
            "chain_id",
            "block_number",
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

    block_number: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    block_hash: Mapped[str] = mapped_column(
        String(66),
        nullable=False,
    )

    parent_hash: Mapped[str] = mapped_column(
        String(66),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )