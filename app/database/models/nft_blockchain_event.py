
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class NFTBlockchainEvent(Base):
    __tablename__ = "nft_blockchain_events"

    __table_args__ = (
        UniqueConstraint(
            "chain_id",
            "block_hash",
            "transaction_hash",
            "log_index",
            "batch_index",
            name="uq_nft_blockchain_event_identity",
        ),
        Index(
            "ix_nft_blockchain_events_chain_block",
            "chain_id",
            "block_number",
        ),
        Index(
            "ix_nft_blockchain_events_chain_canonical",
            "chain_id",
            "is_canonical",
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

    transaction_hash: Mapped[str] = mapped_column(
        String(66),
        nullable=False,
    )

    log_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Ordinary logs use 0. Batch logs use their decoded
    # item index, allowing each item to be stored separately.
    batch_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    is_canonical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
