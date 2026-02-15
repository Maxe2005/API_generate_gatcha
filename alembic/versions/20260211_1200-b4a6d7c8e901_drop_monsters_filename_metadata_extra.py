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
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("monsters")]
    if "metadata_extra" in columns:
        op.drop_column("monsters", "metadata_extra")
    if "filename" in columns:
        op.drop_column("monsters", "filename")


def downgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("monsters")]
    if "filename" not in columns:
        op.add_column(
            "monsters",
            sa.Column("filename", sa.String(), nullable=False),
        )
    if "metadata_extra" not in columns:
        op.add_column(
            "monsters",
            sa.Column(
                "metadata_extra",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )
        op.alter_column("monsters", "metadata_extra", server_default=None)
