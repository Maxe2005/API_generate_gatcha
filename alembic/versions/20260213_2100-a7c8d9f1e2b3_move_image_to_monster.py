"""move_image_path_from_state_to_monster

Revision ID: a7c8d9f1e2b3
Revises: f1cd2ff05c53
Create Date: 2026-02-13 21:00:00.000000

Description:
    Refactorisation de la gestion des images :
    1. Supprime image_path de monsters_state
    2. Ajoute image_url à monsters
    3. Renomme monster_state_id en monster_id dans monster_images
    4. Change la ForeignKey de monster_images vers monsters au lieu de monsters_state
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a7c8d9f1e2b3"
down_revision = "f1cd2ff05c53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade : Déplace la gestion des images de MonsterState vers Monster
    """
    # 1. Ajouter image_url à la table monsters
    op.add_column(
        "monsters",
        sa.Column("image_url", sa.String(), nullable=True),
    )

    # 2. Supprimer image_path de la table monsters_state
    op.drop_column("monsters_state", "image_path")

    # 3. Renommer monster_state_id en monster_id dans monster_images
    # D'abord, supprimer la contrainte de ForeignKey existante
    op.drop_constraint(
        "monster_images_monster_state_id_fkey", "monster_images", type_="foreignkey"
    )

    # Renommer l'index
    op.execute(
        "ALTER INDEX ix_monster_images_monster_state_id RENAME TO ix_monster_images_monster_id"
    )

    # Renommer la colonne
    op.alter_column("monster_images", "monster_state_id", new_column_name="monster_id")

    # 4. Créer la nouvelle ForeignKey vers monsters
    op.create_foreign_key(
        "monster_images_monster_id_fkey",
        "monster_images",
        "monsters",
        ["monster_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """
    Downgrade : Annule les changements de migration
    """
    # 1. Récréer la ForeignKey vers monsters_state
    op.drop_constraint(
        "monster_images_monster_id_fkey", "monster_images", type_="foreignkey"
    )

    op.create_foreign_key(
        "monster_images_monster_state_id_fkey",
        "monster_images",
        "monsters_state",
        ["monster_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2. Renommer la colonne monster_id en monster_state_id
    op.alter_column("monster_images", "monster_id", new_column_name="monster_state_id")

    # Renommer l'index
    op.execute(
        "ALTER INDEX ix_monster_images_monster_id RENAME TO ix_monster_images_monster_state_id"
    )

    # 3. Récréer image_path dans monsters_state
    op.add_column(
        "monsters_state",
        sa.Column("image_path", sa.String(), nullable=True),
    )

    # 4. Supprimer image_url de monsters
    op.drop_column("monsters", "image_url")
