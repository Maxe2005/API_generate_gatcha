"""add_raw_image_key_to_monster_images

Revision ID: fce450bff814
Revises: 97343a9146db
Create Date: 2026-02-12 20:07:22.985815

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "fce450bff814"
down_revision = "97343a9146db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("monster_images")]
    if "raw_image_key" not in columns:
        op.add_column(
            "monster_images", sa.Column("raw_image_key", sa.String(), nullable=True)
        )


def downgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("monster_images")]
    if "raw_image_key" in columns:
        op.drop_column("monster_images", "raw_image_key")
