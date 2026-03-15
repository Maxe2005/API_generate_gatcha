"""
Module: models.monster.update_event

Description:
Modèle SQLAlchemy pour la table monster_update_events.
Enregistre l'historique des mises à jour des données de monstres.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    JSON,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class UpdateEventModel(Base):
    """
    Table des événements de mise à jour des données de monstres.
    Enregistre chaque modification des données d'un monstre.

    Relations:
    - N-to-1 avec MonsterState : update d'un monstre
    """

    __tablename__ = "monster_update_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    monster_state_db_id = Column(
        Integer, ForeignKey("monsters_state.id"), nullable=False, index=True
    )

    # Timestamps et acteur
    occurred_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    actor_type = Column(String, nullable=False, default="admin")  # admin|system|user
    actor_name = Column(String, nullable=False)  # Nom de l'utilisateur/système
    actor_id = Column(String, nullable=True)  # ID optionnel (user_id, service_id, etc.)

    # Source et contexte
    source = Column(
        String, nullable=False
    )  # Ex: admin_update_endpoint, auto_repair, etc.
    reason = Column(Text, nullable=True)  # Notes/raison de l'update

    # Validation
    validation_before = Column(Boolean, nullable=False)  # État de validité avant update
    validation_after = Column(Boolean, nullable=False)  # État de validité après update
    skip_validation = Column(Boolean, nullable=False, default=False)

    # Stockage
    storage_mode_before = Column(
        String, nullable=False
    )  # json|structured - comment les données étaient stockées
    storage_mode_after = Column(
        String, nullable=False
    )  # json|structured - comment elles le sont après

    # Détails de changement
    changed_fields = Column(
        JSON, nullable=False, default=dict
    )  # Liste des champs modifiés, ex: ["stats.hp", "skills[1].cooldown"]
    diff_payload = Column(
        JSON, nullable=True
    )  # {field: {before: ..., after: ...}} pour champs modifiés

    # Métadonnées supplémentaires
    request_context = Column(
        JSON, nullable=True
    )  # Métadonnées: trace_id, correlation_id, etc.

    # Relation optionnelle vers MonsterState
    monster_state = relationship("MonsterState", foreign_keys=[monster_state_db_id])

    def __repr__(self):
        return f"<UpdateEvent(monster_state_db_id={self.monster_state_db_id}, occurred_at='{self.occurred_at}', actor='{self.actor_name}')>"
