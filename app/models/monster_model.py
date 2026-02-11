"""
Module: monster_model

Description:
Modèles SQLAlchemy pour les monstres et leurs métadonnées
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
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.models.base import Base


class MonsterStateEnum(str, enum.Enum):
    """États possibles d'un monstre (pour SQLAlchemy)"""

    GENERATED = "GENERATED"
    DEFECTIVE = "DEFECTIVE"
    CORRECTED = "CORRECTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    TRANSMITTED = "TRANSMITTED"
    REJECTED = "REJECTED"


class Monster(Base):
    """
    Table principale des monstres avec leurs métadonnées et données.
    Combine les anciens fichiers JSON et metadata.
    """

    __tablename__ = "monsters"

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

    # Données du monstre (stockées en JSON)
    # Contient: nom, element, rang, stats, description_carte, description_visuelle, skills
    monster_data = Column(JSON, nullable=False)

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

    # Chemins et métadonnées additionnelles
    image_path = Column(String, nullable=True)

    # Relations
    history = relationship(
        "StateTransitionModel",
        back_populates="monster",
        cascade="all, delete-orphan",
        order_by="StateTransitionModel.timestamp",
    )

    def __repr__(self):
        return f"<Monster(monster_id='{self.monster_id}', state='{self.state}', nom='{self.monster_data.get('nom', 'N/A')}')>"


class StateTransitionModel(Base):
    """
    Table des transitions d'état pour l'historique.
    """

    __tablename__ = "state_transitions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    monster_db_id = Column(
        Integer, ForeignKey("monsters.id"), nullable=False, index=True
    )

    from_state = Column(SQLEnum(MonsterStateEnum), nullable=True)
    to_state = Column(SQLEnum(MonsterStateEnum), nullable=False)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor = Column(String, nullable=False)  # system|admin|user
    note = Column(Text, nullable=True)

    # Relation
    monster = relationship("Monster", back_populates="history")

    def __repr__(self):
        return f"<StateTransition(from='{self.from_state}', to='{self.to_state}', timestamp='{self.timestamp}')>"
