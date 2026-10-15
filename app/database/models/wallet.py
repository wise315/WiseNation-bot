from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    chain_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chains.id"),
        nullable=False,
    )

    address: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    label: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    wallet_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    encrypted_private_key: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )