"""
Module: models.monster.skill

Description:
Modèle SQLAlchemy pour la table skills (compétences des monstres).
Représente une compétence d'un monstre structuré.
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
from app.core.constants import RankEnum


class Skill(Base):
    """
    Table des compétences des monstres.
    Créée lors de la création du monstre structuré.

    Relations:
    - N-to-1 avec Monster : compétence d'un monstre
    """

    __tablename__ = "skills"

    # Identifiant
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Relation vers Monster
    monster_id = Column(Integer, ForeignKey("monsters.id"), nullable=False, index=True)

    # Informations de la compétence
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    damage = Column(Integer, nullable=False)
    cooldown = Column(Integer, nullable=False)
    lvl_max = Column(Integer, nullable=False)
    rank = Column(SQLEnum(RankEnum), nullable=False)

    # Ratio de la compétence
    ratio_stat = Column(String, nullable=False)  # ATK|DEF|HP|VIT
    ratio_percent = Column(Float, nullable=False)

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

    # Relation
    monster = relationship("Monster", back_populates="skills")

    def __repr__(self):
        return f"<Skill(name='{self.name}', damage={self.damage}, rank='{self.rank}')>"
