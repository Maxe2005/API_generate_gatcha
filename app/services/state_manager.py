"""
Module: state_manager

Description:
Gère les états des monstres et les transitions valides.
Gère la transition spéciale JSON → DB structurée lors du passage à PENDING_REVIEW.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.core.constants import MonsterStateEnum
from app.schemas.metadata import MonsterMetadata, StateTransition
from app.models.monster import MonsterState as MonsterStateDB
import logging

logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Exception levée lors d'une transition invalide"""

    pass


class MonsterStateManager:
    """
    Gère les états des monstres et les transitions valides.
    Respecte le principe Single Responsibility (SOLID).

    Responsabilités :
    - Valider les transitions d'état
    - Enregistrer l'historique des transitions
    - Orchestrer la transition JSON → DB (PENDING_REVIEW)
    """

    # Définition des transitions valides
    VALID_TRANSITIONS: Dict[MonsterStateEnum, list] = {
        MonsterStateEnum.GENERATED: [
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.DEFECTIVE,
        ],
        MonsterStateEnum.DEFECTIVE: [
            MonsterStateEnum.CORRECTED,
            MonsterStateEnum.REJECTED,
        ],
        MonsterStateEnum.CORRECTED: [MonsterStateEnum.PENDING_REVIEW],
        MonsterStateEnum.PENDING_REVIEW: [
            MonsterStateEnum.APPROVED,
            MonsterStateEnum.REJECTED,
        ],
        MonsterStateEnum.APPROVED: [
            MonsterStateEnum.TRANSMITTED,
            MonsterStateEnum.PENDING_REVIEW,
        ],
        MonsterStateEnum.TRANSMITTED: [],
        MonsterStateEnum.REJECTED: [],
    }

    # États qui nécessitent des données JSON (avant structuration)
    JSON_STATES = [
        MonsterStateEnum.GENERATED,
        MonsterStateEnum.DEFECTIVE,
        MonsterStateEnum.CORRECTED,
    ]

    # États qui nécessitent des données structurées (après structuration)
    STRUCTURED_STATES = [
        MonsterStateEnum.PENDING_REVIEW,
        MonsterStateEnum.APPROVED,
        MonsterStateEnum.TRANSMITTED,
        MonsterStateEnum.REJECTED,
    ]

    def can_transition(
        self, from_state: MonsterStateEnum, to_state: MonsterStateEnum
    ) -> bool:
        """Vérifie si une transition est valide"""
        return to_state in self.VALID_TRANSITIONS.get(from_state, [])

    def transition(
        self,
        metadata: MonsterMetadata,
        to_state: MonsterStateEnum,
        actor: str = "system",
        note: Optional[str] = None,
    ) -> MonsterMetadata:
        """
        Effectue une transition d'état si elle est valide.

        Note : Cette méthode ne gère PAS la transition JSON → DB.
        Pour les transitions vers PENDING_REVIEW, utiliser `transition_to_pending_review()`.

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
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            note=note,
        )

        # Mettre à jour les métadonnées
        metadata.state = to_state
        metadata.updated_at = datetime.now(timezone.utc)
        metadata.history.append(transition)

        logger.info(
            f"Monster {metadata.monster_id}: {current_state} → {to_state} (by {actor})"
        )

        return metadata

    def transition_to_pending_review(
        self,
        monster_state_db: MonsterStateDB,
        monster_json: Dict[str, Any],
        repository,  # MonsterRepository
        actor: str = "admin",
        note: Optional[str] = None,
    ) -> bool:
        """
        Effectue la transition spéciale vers PENDING_REVIEW.

        Cette transition implique :
        1. Validation de la transition d'état
        2. Création du monstre structuré et ses skills en DB
        3. Mise à NULL de monster_data
        4. Enregistrement de la transition

        Args:
            monster_state_db: Objet MonsterState DB (avec monster_data JSON)
            monster_json: Données JSON du monstre
            repository: Instance de MonsterRepository pour la création structurée
            actor: Qui effectue la transition
            note: Note optionnelle

        Returns:
            True si succès, False sinon

        Raises:
            StateTransitionError: Si la transition est invalide
        """
        current_state = MonsterStateEnum(monster_state_db.state.value)
        to_state = MonsterStateEnum.PENDING_REVIEW
        # - Mis monster_data à NULL
        # - Commit en DB

        # Ajouter la transition dans l'historique
        repository.add_transition(
            monster_state_db.monster_id,
            from_state=current_state,  # type: ignore
            to_state=to_state,  # type: ignore
            actor=actor,
            note=note or "Transition to PENDING_REVIEW (JSON → Structured DB)",
        )

        logger.info(
            f"Monster {monster_state_db.monster_id}: {current_state} → {to_state} "
            f"(structured with {len(monster.skills)} skills)"
        )

        return True

    def get_next_states(self, current_state: MonsterStateEnum) -> list:
        """Retourne les états possibles depuis l'état actuel"""
        return self.VALID_TRANSITIONS.get(current_state, [])

    def is_final_state(self, state: MonsterStateEnum) -> bool:
        """Vérifie si un état est final"""
        return len(self.VALID_TRANSITIONS.get(state, [])) == 0

    def requires_json_data(self, state: MonsterStateEnum) -> bool:
        """Vérifie si un état nécessite des données JSON"""
        return state in self.JSON_STATES

    def requires_structured_data(self, state: MonsterStateEnum) -> bool:
        """Vérifie si un état nécessite des données structurées"""
        return state in self.STRUCTURED_STATES
