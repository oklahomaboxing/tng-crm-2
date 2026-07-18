"""add waiver submissions

Revision ID: 63c5555c46c4
Revises: 05a10fc92656
Create Date: 2026-07-18 13:41:33.069994
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "63c5555c46c4"
down_revision: Union[str, Sequence[str], None] = "05a10fc92656"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "waiver_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("participant_first_name", sa.String(), nullable=False),
        sa.Column("participant_last_name", sa.String(), nullable=False),
        sa.Column("participant_date_of_birth", sa.Date(), nullable=False),
        sa.Column("guardian_name", sa.String(), nullable=True),
        sa.Column("signer_relationship", sa.String(), nullable=False),
        sa.Column("emergency_contact_name", sa.String(), nullable=False),
        sa.Column("emergency_contact_phone", sa.String(), nullable=False),
        sa.Column("waiver_accepted", sa.Boolean(), nullable=False),
        sa.Column("medical_acknowledgment", sa.Boolean(), nullable=False),
        sa.Column("waiver_version", sa.String(), nullable=False),
        sa.Column("waiver_text_snapshot", sa.Text(), nullable=False),
        sa.Column("signature_name", sa.String(), nullable=False),
        sa.Column("signature_data", sa.Text(), nullable=True),
        sa.Column("photo_release", sa.Boolean(), nullable=False),
        sa.Column("sms_consent", sa.Boolean(), nullable=False),
        sa.Column("sms_consent_at", sa.DateTime(), nullable=True),
        sa.Column("sms_disclosure_version", sa.String(), nullable=True),
        sa.Column("email_consent", sa.Boolean(), nullable=False),
        sa.Column("email_consent_at", sa.DateTime(), nullable=True),
        sa.Column("email_disclosure_version", sa.String(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("submission_uuid", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_waiver_submissions_id"),
        "waiver_submissions",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_waiver_submissions_lead_id"),
        "waiver_submissions",
        ["lead_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_waiver_submissions_submission_uuid"),
        "waiver_submissions",
        ["submission_uuid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_waiver_submissions_submission_uuid"),
        table_name="waiver_submissions",
    )

    op.drop_index(
        op.f("ix_waiver_submissions_lead_id"),
        table_name="waiver_submissions",
    )

    op.drop_index(
        op.f("ix_waiver_submissions_id"),
        table_name="waiver_submissions",
    )

    op.drop_table("waiver_submissions")