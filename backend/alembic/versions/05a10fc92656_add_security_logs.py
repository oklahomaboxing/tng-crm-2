"""add security logs

Revision ID: 05a10fc92656
Revises: 071557b429a9
Create Date: 2026-07-11 22:29:17.301524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05a10fc92656'
down_revision: Union[str, Sequence[str], None] = '071557b429a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "security_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("endpoint", sa.String(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_security_logs_id"),
        "security_logs",
        ["id"],
        unique=False,
    )

    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login_ip", sa.String(), nullable=True),
    )
def downgrade() -> None:
    op.drop_column("users", "last_login_ip")
    op.drop_column("users", "last_login")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")

    op.drop_index(
        op.f("ix_security_logs_id"),
        table_name="security_logs",
    )
    op.drop_table("security_logs")