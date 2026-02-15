"""add_monster_images_table

Revision ID: 97343a9146db
Revises: b4a6d7c8e901
Create Date: 2026-02-12 19:39:41.552226

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "97343a9146db"
down_revision = "b4a6d7c8e901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    if "monster_images" not in tables:
        op.create_table(
            "monster_images",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("monster_id", sa.Integer(), nullable=False),
            sa.Column("image_name", sa.String(), nullable=False),
            sa.Column("image_url", sa.String(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column(
                "is_default", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["monster_id"], ["monsters.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_monster_images_id"), "monster_images", ["id"], unique=False
        )
        op.create_index(
            op.f("ix_monster_images_monster_id"),
            "monster_images",
            ["monster_id"],
            unique=False,
        )


def downgrade() -> None:
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    if "monster_images" in tables:
        op.drop_index(op.f("ix_monster_images_monster_id"), table_name="monster_images")
        op.drop_index(op.f("ix_monster_images_id"), table_name="monster_images")
        op.drop_table("monster_images")
