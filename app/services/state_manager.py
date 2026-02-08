"""
Module: state_manager

Description:
Gère les états des monstres et les transitions valides.

Author: Copilot
Date: 2026-02-08
"""

from typing import Optional, Dict
from datetime import datetime
from app.schemas.monster import MonsterState, TransitionAction
from app.schemas.metadata import MonsterMetadata, StateTransition
import logging

logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Exception levée lors d'une transition invalide"""

    pass


class MonsterStateManager:
    """
    Gère les états des monstres et les transitions valides.
    Respecte le principe Single Responsibility (SOLID).
    """

    # Définition des transitions valides
    VALID_TRANSITIONS: Dict[MonsterState, list] = {
        MonsterState.GENERATED: [MonsterState.PENDING_REVIEW],
        MonsterState.DEFECTIVE: [MonsterState.CORRECTED, MonsterState.REJECTED],
        MonsterState.CORRECTED: [MonsterState.PENDING_REVIEW],
        MonsterState.PENDING_REVIEW: [MonsterState.APPROVED, MonsterState.REJECTED],
        MonsterState.APPROVED: [MonsterState.TRANSMITTED, MonsterState.PENDING_REVIEW],
        MonsterState.TRANSMITTED: [],
        MonsterState.REJECTED: [],
    }

    def can_transition(self, from_state: MonsterState, to_state: MonsterState) -> bool:
        """Vérifie si une transition est valide"""
        return to_state in self.VALID_TRANSITIONS.get(from_state, [])

    def transition(
        self,
        metadata: MonsterMetadata,
        to_state: MonsterState,
        actor: str = "system",
        note: Optional[str] = None,
    ) -> MonsterMetadata:
        """
        Effectue une transition d'état si elle est valide.

        Args:
            metadata: Métadonnées du monstre
            to_state: État cible
            actor: Qui effectue la transition (system|admin|user)
            note: Note optionnelle

        Returns:
            Métadonnées mises à jour

        Raises:
            StateTransitionError: Si la transition est invalide
        """
        current_state = metadata.state

        if not self.can_transition(current_state, to_state):
            raise StateTransitionError(
                f"Invalid transition from {current_state} to {to_state}"
            )

        # Enregistrer la transition
        transition = StateTransition(
            from_state=current_state,
            to_state=to_state,
            timestamp=datetime.utcnow(),
            actor=actor,
            note=note,
        )

        # Mettre à jour les métadonnées
        metadata.state = to_state
        metadata.updated_at = datetime.utcnow()
        metadata.history.append(transition)

        logger.info(
            f"Monster {metadata.monster_id}: {current_state} → {to_state} (by {actor})"
        )

        return metadata

    def get_next_states(self, current_state: MonsterState) -> list:
        """Retourne les états possibles depuis l'état actuel"""
        return self.VALID_TRANSITIONS.get(current_state, [])

    def is_final_state(self, state: MonsterState) -> bool:
        """Vérifie si un état est final"""
        return len(self.VALID_TRANSITIONS.get(state, [])) == 0
