"""
Widen token columns from varchar(255) to text.

JWT tokens used for email verification and password reset can exceed 255 chars.

Revision ID: 012
Revises: 011
Create Date: 2026-02-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "email_verification_token",
        type_=sa.Text(),
        existing_type=sa.String(255),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "password_reset_token",
        type_=sa.Text(),
        existing_type=sa.String(255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "email_verification_token",
        type_=sa.String(255),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "password_reset_token",
        type_=sa.String(255),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
