"""add docusign contract fields

Revision ID: d5c9a7b1e204
Revises: 63c5555c46c4
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5c9a7b1e204"
down_revision: Union[str, Sequence[str], None] = "63c5555c46c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "boxing_contracts",
        sa.Column(
            "docusign_envelope_id",
            sa.String(),
            nullable=True,
            server_default="",
        ),
    )
    op.add_column(
        "boxing_contracts",
        sa.Column(
            "docusign_status",
            sa.String(),
            nullable=True,
            server_default="",
        ),
    )
    op.add_column(
        "boxing_contracts",
        sa.Column(
            "docusign_signing_url",
            sa.Text(),
            nullable=True,
            server_default="",
        ),
    )
    op.add_column(
        "boxing_contracts",
        sa.Column(
            "docusign_sent_at",
            sa.DateTime(),
            nullable=True,
        ),
    )
    op.add_column(
        "boxing_contracts",
        sa.Column(
            "docusign_signed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )
    op.add_column(
        "boxing_contracts",
        sa.Column(
            "docusign_last_synced_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_boxing_contracts_docusign_envelope_id",
        "boxing_contracts",
        ["docusign_envelope_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_boxing_contracts_docusign_envelope_id",
        table_name="boxing_contracts",
    )

    op.drop_column(
        "boxing_contracts",
        "docusign_last_synced_at",
    )
    op.drop_column(
        "boxing_contracts",
        "docusign_signed_at",
    )
    op.drop_column(
        "boxing_contracts",
        "docusign_sent_at",
    )
    op.drop_column(
        "boxing_contracts",
        "docusign_signing_url",
    )
    op.drop_column(
        "boxing_contracts",
        "docusign_status",
    )
    op.drop_column(
        "boxing_contracts",
        "docusign_envelope_id",
    )
