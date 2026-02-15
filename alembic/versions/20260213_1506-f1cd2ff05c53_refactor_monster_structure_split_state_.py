"""refactor_monster_structure_split_state_and_data

Revision ID: f1cd2ff05c53
Revises: fce450bff814
Create Date: 2026-02-13 15:06:13.763677

Description:
    Refactorisation majeure de l'architecture de données :
    1. Renomme 'monsters' en 'monsters_state' (table d'état et métadonnées)
    2. Crée une nouvelle table 'monsters' (données structurées pour monstres validés)
    3. Crée une nouvelle table 'skills' (compétences des monstres)
    4. monster_data devient nullable (NULL à partir de PENDING_REVIEW)
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f1cd2ff05c53"
down_revision = "fce450bff814"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade : Restructure les tables monsters
    """
    # 1. Renommer la table monsters en monsters_state
    op.rename_table("monsters", "monsters_state")

    # 2. Mettre à jour les contraintes et index avec les nouveaux noms
    # Renommer les séquences
    op.execute("ALTER SEQUENCE monsters_id_seq RENAME TO monsters_state_id_seq")

    # Renommer les index
    op.execute(
        "ALTER INDEX ix_monsters_monster_id RENAME TO ix_monsters_state_monster_id"
    )
    op.execute("ALTER INDEX ix_monsters_state RENAME TO ix_monsters_state_state")

    # 3. Modifier monster_data pour accepter NULL
    op.alter_column(
        "monsters_state",
        "monster_data",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=True,
    )

    # 4. Mettre à jour les foreign keys de state_transitions
    op.drop_constraint(
        "state_transitions_monster_db_id_fkey", "state_transitions", type_="foreignkey"
    )
    op.execute(
        "ALTER INDEX ix_state_transitions_monster_db_id RENAME TO ix_state_transitions_monster_state_db_id"
    )
    op.alter_column(
        "state_transitions", "monster_db_id", new_column_name="monster_state_db_id"
    )
    op.create_foreign_key(
        "state_transitions_monster_state_db_id_fkey",
        "state_transitions",
        "monsters_state",
        ["monster_state_db_id"],
        ["id"],
    )

    # 5. Mettre à jour les foreign keys de monster_images
    op.drop_constraint(
        "monster_images_monster_id_fkey", "monster_images", type_="foreignkey"
    )
    op.execute(
        "ALTER INDEX ix_monster_images_monster_id RENAME TO ix_monster_images_monster_state_id"
    )
    op.alter_column("monster_images", "monster_id", new_column_name="monster_state_id")
    op.create_foreign_key(
        "monster_images_monster_state_id_fkey",
        "monster_images",
        "monsters_state",
        ["monster_state_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 6. Créer les nouveaux enums pour la nouvelle table monsters
    element_enum = postgresql.ENUM("FIRE", "WATER", "WIND", "EARTH", name="elementenum")
    element_enum.create(op.get_bind(), checkfirst=True)

    rank_enum = postgresql.ENUM("COMMON", "RARE", "EPIC", "LEGENDARY", name="rankenum")
    rank_enum.create(op.get_bind(), checkfirst=True)

    # 7. Créer la nouvelle table monsters (structurée)
    op.create_table(
        "monsters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("monster_state_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column(
            "element",
            sa.Enum("FIRE", "WATER", "WIND", "EARTH", name="elementenum"),
            nullable=False,
        ),
        sa.Column(
            "rang",
            sa.Enum("COMMON", "RARE", "EPIC", "LEGENDARY", name="rankenum"),
            nullable=False,
        ),
        sa.Column("hp", sa.Float(), nullable=False),
        sa.Column("atk", sa.Float(), nullable=False),
        sa.Column("def_", sa.Float(), nullable=False),
        sa.Column("vit", sa.Float(), nullable=False),
        sa.Column("description_carte", sa.Text(), nullable=False),
        sa.Column("description_visuelle", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["monster_state_id"],
            ["monsters_state.id"],
        ),
        sa.UniqueConstraint("monster_state_id"),
    )
    op.create_index(op.f("ix_monsters_element"), "monsters", ["element"], unique=False)
    op.create_index(
        op.f("ix_monsters_monster_state_id"),
        "monsters",
        ["monster_state_id"],
        unique=True,
    )
    op.create_index(op.f("ix_monsters_nom"), "monsters", ["nom"], unique=False)
    op.create_index(op.f("ix_monsters_rang"), "monsters", ["rang"], unique=False)

    # 8. Créer la table skills
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("monster_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("damage", sa.Float(), nullable=False),
        sa.Column("cooldown", sa.Float(), nullable=False),
        sa.Column("lvl_max", sa.Float(), nullable=False),
        sa.Column(
            "rank",
            sa.Enum("COMMON", "RARE", "EPIC", "LEGENDARY", name="rankenum"),
            nullable=False,
        ),
        sa.Column("ratio_stat", sa.String(), nullable=False),
        sa.Column("ratio_percent", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["monster_id"],
            ["monsters.id"],
        ),
    )
    op.create_index(
        op.f("ix_skills_monster_id"), "skills", ["monster_id"], unique=False
    )


def downgrade() -> None:
    """
    Downgrade : Revenir à l'architecture précédente
    """
    # 1. Supprimer les nouvelles tables
    op.drop_index(op.f("ix_skills_monster_id"), table_name="skills")
    op.drop_table("skills")

    op.drop_index(op.f("ix_monsters_rang"), table_name="monsters")
    op.drop_index(op.f("ix_monsters_nom"), table_name="monsters")
    op.drop_index(op.f("ix_monsters_monster_state_id"), table_name="monsters")
    op.drop_index(op.f("ix_monsters_element"), table_name="monsters")
    op.drop_table("monsters")

    # 2. Supprimer les enums (si plus utilisés)
    # Note: On ne les supprime pas car monsterstateenum les utilise peut-être

    # 3. Rétablir les foreign keys de monster_images
    op.drop_constraint(
        "monster_images_monster_state_id_fkey", "monster_images", type_="foreignkey"
    )
    op.alter_column("monster_images", "monster_state_id", new_column_name="monster_id")
    op.execute(
        "ALTER INDEX ix_monster_images_monster_state_id RENAME TO ix_monster_images_monster_id"
    )
    op.create_foreign_key(
        "monster_images_monster_id_fkey",
        "monster_images",
        "monsters_state",  # Toujours monsters_state à ce stade
        ["monster_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 4. Rétablir les foreign keys de state_transitions
    op.drop_constraint(
        "state_transitions_monster_state_db_id_fkey",
        "state_transitions",
        type_="foreignkey",
    )
    op.alter_column(
        "state_transitions", "monster_state_db_id", new_column_name="monster_db_id"
    )
    op.execute(
        "ALTER INDEX ix_state_transitions_monster_state_db_id RENAME TO ix_state_transitions_monster_db_id"
    )
    op.create_foreign_key(
        "state_transitions_monster_db_id_fkey",
        "state_transitions",
        "monsters_state",  # Toujours monsters_state à ce stade
        ["monster_db_id"],
        ["id"],
    )

    # 5. Remettre monster_data en NOT NULL
    op.alter_column(
        "monsters_state",
        "monster_data",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=False,
    )

    # 6. Renommer les index
    op.execute("ALTER INDEX ix_monsters_state_state RENAME TO ix_monsters_state")
    op.execute(
        "ALTER INDEX ix_monsters_state_monster_id RENAME TO ix_monsters_monster_id"
    )

    # 7. Renommer la séquence
    op.execute("ALTER SEQUENCE monsters_state_id_seq RENAME TO monsters_id_seq")

    # 8. Renommer monsters_state en monsters
    op.rename_table("monsters_state", "monsters")
