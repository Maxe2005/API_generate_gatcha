"""Drop monsters filename and metadata_extra columns

Revision ID: b4a6d7c8e901
Revises: None
Create Date: 2026-02-11 12:00:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b4a6d7c8e901"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("monsters", "metadata_extra")
    op.drop_column("monsters", "filename")


def downgrade() -> None:
    op.add_column(
        "monsters",
        sa.Column("filename", sa.String(), nullable=False),
    )
    op.add_column(
        "monsters",
        sa.Column(
            "metadata_extra", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
    )
    op.alter_column("monsters", "metadata_extra", server_default=None)
