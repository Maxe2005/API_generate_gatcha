"""
Module: models.monster.monster

Description:
Modèle SQLAlchemy pour la table monsters (données structurées).
Représente un monstre validé avec ses attributs structurés.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Enum as SQLEnum,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.constants import ElementEnum, RankEnum


class Monster(Base):
    """
    Table structurée des monstres validés.
    Créée lors de la transition vers PENDING_REVIEW.

    Relations:
    - 1-to-1 avec MonsterState : lié au cycle de vie du monstre
    - 1-to-many avec Skill : compétences du monstre
    - 1-to-many avec MonsterImage : images du monstre
    """

    __tablename__ = "monsters"

    # Identifiant
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    monster_uuid = Column(String, unique=True, index=True, nullable=False)  # UUID pour référence externe

    # Relation vers MonsterState (1-to-1)
    monster_state_id = Column(
        Integer,
        ForeignKey("monsters_state.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Informations de base
    nom = Column(String, nullable=False, index=True)
    element = Column(SQLEnum(ElementEnum), nullable=False, index=True)
    rang = Column(SQLEnum(RankEnum), nullable=False, index=True)

    # Stats
    hp = Column(Float, nullable=False)
    atk = Column(Float, nullable=False)
    def_ = Column(Float, nullable=False)  # defense
    vit = Column(Float, nullable=False)  # vitesse

    # Descriptions
    description_carte = Column(Text, nullable=False)
    description_visuelle = Column(Text, nullable=False)

    # Image
    image_url = Column(String, nullable=True)  # URL de l'image par défaut

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relations
    state = relationship("MonsterState", back_populates="monster")
    skills = relationship(
        "Skill",
        back_populates="monster",
        cascade="all, delete-orphan",
        order_by="Skill.id",
    )
    images = relationship(
        "MonsterImage",
        back_populates="monster",
        cascade="all, delete-orphan",
        order_by="MonsterImage.created_at",
    )

    def __repr__(self):
        return (
            f"<Monster(nom='{self.nom}', element='{self.element}', rang='{self.rang}')>"
        )
