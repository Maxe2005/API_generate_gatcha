"""
Module: models.monster.transition

Description:
Modèle SQLAlchemy pour la table state_transitions.
Gère l'historique des transitions d'état des monstres.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    Enum as SQLEnum,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.constants import MonsterStateEnum


class StateTransitionModel(Base):
    """
    Table des transitions d'état pour l'historique.
    Enregistre chaque changement d'état d'un monstre.

    Relations:
    - N-to-1 avec MonsterState : transition d'un monstre
    """

    __tablename__ = "state_transitions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    monster_state_db_id = Column(
        Integer, ForeignKey("monsters_state.id"), nullable=False, index=True
    )

    from_state = Column(SQLEnum(MonsterStateEnum), nullable=True)
    to_state = Column(SQLEnum(MonsterStateEnum), nullable=False)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor = Column(String, nullable=False)  # system|admin|user
    note = Column(Text, nullable=True)

    # Relation
    monster_state = relationship("MonsterState", back_populates="history")

    def __repr__(self):
        return f"<StateTransition(from='{self.from_state}', to='{self.to_state}', timestamp='{self.timestamp}')>"
