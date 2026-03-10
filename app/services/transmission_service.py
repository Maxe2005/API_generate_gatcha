"""
Module: transmission_service

Description:
Service de transmission des monstres vers l'API d'invocation.
"""

from typing import Optional
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.clients.invocation_api import InvocationApiClient, InvocationApiError
from app.repositories.monster import MonsterRepository
from app.repositories.monster.state_repository import MonsterStateRepository
from app.repositories.monster.transition_repository import TransitionRepository
from app.schemas.admin import MonsterListFilter
from app.services.state_manager import MonsterStateManager
from app.core.constants import MonsterStateEnum

logger = logging.getLogger(__name__)


class TransmissionService:
    """Service de transmission des monstres vers l'API d'invocation"""

    def __init__(
        self, db: Session, invocation_api_url: str = "http://host.docker.internal:8085"
    ):
        self.invocation_client = InvocationApiClient(base_url=invocation_api_url)
        self.repository = MonsterRepository(db)
        self.state_repository = MonsterStateRepository(db)
        self.structure_repository = TransitionRepository(db)
        self.state_manager = MonsterStateManager(
            self.state_repository, self.structure_repository
        )

    async def transmit_monster(
        self, monster_id: str, force: bool = False, admin_name: str = "system"
    ) -> dict:
        """
        Transmet un monstre vers l'API d'invocation.

        Args:
            monster_id: ID du monstre à transmettre
            force: Si True, retransmet même si déjà transmis
            admin_name: Nom de l'administrateur effectuant la transmission

        Returns:
            dict avec le résultat de la transmission

        Raises:
            ValueError: Si le monstre n'est pas dans l'état approprié
            InvocationApiError: Si la transmission échoue
        """
        # Récupérer le monstre
        monster = self.repository.get_by_uuid(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")

        monsterState = self.state_repository.get(monster_id)
        if not monsterState:
            raise ValueError(f"Monster state for {monster_id} not found")
        metadata = monsterState.metadata

        # Vérifier l'état
        if metadata.state == MonsterStateEnum.TRANSMITTED and not force:
            return {
                "status": "already_transmitted",
                "monster_id": monster_id,
                "transmitted_at": metadata.transmitted_at,
                "message": "Monster already transmitted. Use force=true to retransmit.",
            }

        if metadata.state != MonsterStateEnum.APPROVED and not force:
            raise ValueError(
                f"Monster must be in APPROVED state, current: {metadata.state}"
            )

        # Tenter la transmission
        try:
            response = await self.invocation_client.create_monster(monster)

            # Mettre à jour les métadonnées
            metadata.transmitted_at = datetime.now(timezone.utc)
            metadata.transmission_attempts += 1
            metadata.last_transmission_error = None
            metadata.invocation_api_id = response.get("id")

            # Transition vers TRANSMITTED
            metadata = self.state_manager.perform_transition(
                metadata,
                MonsterStateEnum.TRANSMITTED,
                actor=admin_name,
                note="Successfully transmitted to invocation API",
            )

            logger.info(f"Monster {monster_id} transmitted successfully")

            return {
                "status": "success",
                "monster_id": monster_id,
                "invocation_api_id": response.get("id"),
                "transmitted_at": metadata.transmitted_at,
                "message": "Monster transmitted successfully",
            }

        except InvocationApiError as e:
            # Enregistrer l'erreur
            metadata.transmission_attempts += 1
            metadata.last_transmission_error = str(e)
            metadata.updated_at = datetime.now(timezone.utc)

            self.state_repository.save(metadata)

            logger.error(f"Failed to transmit monster {monster_id}: {e}")

            raise

    async def transmit_all_approved(self, max_count: Optional[int] = None) -> dict:
        """
        Transmet tous les monstres approuvés.

        Args:
            max_count: Nombre maximum à transmettre (None = tous)

        Returns:
            dict avec les résultats de la transmission
        """
        filter: MonsterListFilter = MonsterListFilter(
            state=MonsterStateEnum.APPROVED, limit=max_count if max_count else 1000
        )
        approved_monsters = self.state_repository.list_filtred(filter)

        results = {
            "total": len(approved_monsters),
            "success": 0,
            "failed": 0,
            "details": [],
        }

        for metadata in approved_monsters:
            try:
                await self.transmit_monster(metadata.monster_id)
                results["success"] += 1
                results["details"].append(
                    {"monster_id": metadata.monster_id, "status": "success"}
                )
            except Exception as e:
                results["failed"] += 1
                results["details"].append(
                    {
                        "monster_id": metadata.monster_id,
                        "status": "failed",
                        "error": str(e),
                    }
                )

        logger.info(
            f"Batch transmission completed: "
            f"{results['success']} success, {results['failed']} failed"
        )

        return results

    async def health_check(self) -> dict:
        """Vérifie la disponibilité de l'API d'invocation"""
        is_healthy = await self.invocation_client.health_check()

        return {
            "invocation_api_healthy": is_healthy,
            "base_url": self.invocation_client.base_url,
        }
