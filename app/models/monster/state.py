"""
Module: models.monster.state

Description:
Modèle SQLAlchemy pour la table monsters_state (état et métadonnées).
Gère le cycle de vie et les métadonnées des monstres.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    JSON,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.constants import MonsterStateEnum


class MonsterState(Base):
    """
    Table d'état et métadonnées des monstres (anciennement "monsters").
    Gère le cycle de vie et les transitions d'état.

    - Pour les états GENERATED, DEFECTIVE, CORRECTED : monster_data contient le JSON complet
    - À partir de PENDING_REVIEW : monster_data devient NULL, les données sont dans Monster/Skill

    Relations:
    - 1-to-1 avec Monster : lien vers les données structurées
    - 1-to-many avec StateTransitionModel : historique des transitions
    """

    __tablename__ = "monsters_state"

    # Identifiants
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    monster_id = Column(String, unique=True, index=True, nullable=False)  # UUID

    # État et lifecycle
    state = Column(
        SQLEnum(MonsterStateEnum),
        default=MonsterStateEnum.GENERATED,
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Données du monstre (stockées en JSON pour GENERATED, DEFECTIVE, CORRECTED)
    # NULL à partir de PENDING_REVIEW (données dans Monster/Skill)
    monster_data = Column(JSON, nullable=True)

    # Métadonnées de génération
    generated_by = Column(String, default="gemini", nullable=False)
    generation_prompt = Column(Text, nullable=True)

    # Validation
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_errors = Column(JSON, nullable=True)

    # Review admin
    reviewed_by = Column(String, nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Transmission
    transmitted_at = Column(DateTime(timezone=True), nullable=True)
    transmission_attempts = Column(Integer, default=0, nullable=False)
    last_transmission_error = Column(Text, nullable=True)
    invocation_api_id = Column(String, nullable=True)

    # Relation vers le monstre structuré (à partir de PENDING_REVIEW)
    monster = relationship(
        "Monster",
        back_populates="state",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Relation vers l'historique des transitions
    history = relationship(
        "StateTransitionModel",
        back_populates="monster_state",
        cascade="all, delete-orphan",
        order_by="StateTransitionModel.timestamp",
    )

    def __repr__(self):
        name = (
            self.monster.nom
            if self.monster
            else self.monster_data.get("nom", "N/A")
            if self.monster_data is not None
            else "N/A"
        )
        return f"<MonsterState(monster_id='{self.monster_id}', state='{self.state}', nom='{name}')>"
