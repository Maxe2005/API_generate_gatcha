"""SyncMonsterUpdateEventsWithModel

Supprime les colonnes source, storage_mode_before et storage_mode_after de
monster_update_events : elles ont été retirées du modèle SQLAlchemy
(commit 9bf1dca) sans migration corrective. Sur une base migrée par
Alembic, ces colonnes NOT NULL faisaient échouer toute insertion
d'événement de mise à jour.

Les DROP COLUMN utilisent IF EXISTS car les bases initialisées via
Base.metadata.create_all() n'ont jamais eu ces colonnes.

Revision ID: c4f8b21d9a63
Revises: 65adb29cc7c0
Create Date: 2026-07-19 15:50:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c4f8b21d9a63"
down_revision = "65adb29cc7c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE monster_update_events DROP COLUMN IF EXISTS source")
    op.execute(
        "ALTER TABLE monster_update_events DROP COLUMN IF EXISTS storage_mode_before"
    )
    op.execute(
        "ALTER TABLE monster_update_events DROP COLUMN IF EXISTS storage_mode_after"
    )


def downgrade() -> None:
    # Recréées nullable : les valeurs d'origine ne peuvent pas être restaurées
    op.add_column(
        "monster_update_events", sa.Column("source", sa.String(), nullable=True)
    )
    op.add_column(
        "monster_update_events",
        sa.Column("storage_mode_before", sa.String(), nullable=True),
    )
    op.add_column(
        "monster_update_events",
        sa.Column("storage_mode_after", sa.String(), nullable=True),
    )
