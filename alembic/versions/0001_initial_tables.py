
"""Create initial users, chains and wallets tables.

Revision ID: 0001_initial
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("subscription_tier", sa.String(), nullable=False),
        sa.Column("is_banned", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_users_telegram_id",
        "users",
        ["telegram_id"],
        unique=True,
    )

    op.create_table(
        "chains",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("rpc_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("chain_id"),
    )

    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("wallet_type", sa.String(), nullable=False),
        sa.Column("encrypted_private_key", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["chain_id"], ["chains.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_wallets_user_id",
        "wallets",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_wallets_address",
        "wallets",
        ["address"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wallets_address", table_name="wallets")
    op.drop_index("ix_wallets_user_id", table_name="wallets")
    op.drop_table("wallets")

    op.drop_table("chains")

    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
