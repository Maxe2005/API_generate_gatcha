"""
Module: transmission_service

Description:
Service de transmission des monstres vers l'API d'invocation.

Author: Copilot
Date: 2026-02-08
"""

from typing import Optional, List
from datetime import datetime
import logging

from app.clients.invocation_api import InvocationApiClient, InvocationApiError
from app.repositories.monster_repository import MonsterRepository
from app.services.state_manager import MonsterStateManager
from app.schemas.monster import MonsterState

logger = logging.getLogger(__name__)


class TransmissionService:
    """Service de transmission des monstres vers l'API d'invocation"""

    def __init__(self, invocation_api_url: str = "http://localhost:8085"):
        self.invocation_client = InvocationApiClient(base_url=invocation_api_url)
        self.repository = MonsterRepository()
        self.state_manager = MonsterStateManager()

    async def transmit_monster(self, monster_id: str, force: bool = False) -> dict:
        """
        Transmet un monstre vers l'API d'invocation.

        Args:
            monster_id: ID du monstre à transmettre
            force: Si True, retransmet même si déjà transmis

        Returns:
            dict avec le résultat de la transmission

        Raises:
            ValueError: Si le monstre n'est pas dans l'état approprié
            InvocationApiError: Si la transmission échoue
        """
        # Récupérer le monstre
        monster = self.repository.get(monster_id)
        if not monster:
            raise ValueError(f"Monster {monster_id} not found")

        # Vérifier l'état
        if monster.metadata.state == MonsterState.TRANSMITTED and not force:
            return {
                "status": "already_transmitted",
                "monster_id": monster_id,
                "transmitted_at": monster.metadata.transmitted_at,
                "message": "Monster already transmitted. Use force=true to retransmit.",
            }

        if monster.metadata.state != MonsterState.APPROVED and not force:
            raise ValueError(
                f"Monster must be in APPROVED state, current: {monster.metadata.state}"
            )

        # Tenter la transmission
        try:
            response = await self.invocation_client.create_monster(monster.monster_data)

            # Mettre à jour les métadonnées
            monster.metadata.transmitted_at = datetime.utcnow()
            monster.metadata.transmission_attempts += 1
            monster.metadata.last_transmission_error = None
            monster.metadata.invocation_api_id = response.get("id")

            # Transition vers TRANSMITTED
            metadata = self.state_manager.transition(
                monster.metadata,
                MonsterState.TRANSMITTED,
                actor="system",
                note="Successfully transmitted to invocation API",
            )

            # Sauvegarder
            self.repository.save(metadata, monster.monster_data)
            self.repository.move_to_state(monster_id, MonsterState.TRANSMITTED)

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
            monster.metadata.transmission_attempts += 1
            monster.metadata.last_transmission_error = str(e)
            monster.metadata.updated_at = datetime.utcnow()

            self.repository.save(monster.metadata, monster.monster_data)

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
        approved_monsters = self.repository.list_by_state(
            MonsterState.APPROVED, limit=max_count or 1000
        )

        results = {
            "total": len(approved_monsters),
            "success": 0,
            "failed": 0,
            "details": [],
        }

        for metadata in approved_monsters:
            try:
                result = await self.transmit_monster(metadata.monster_id)
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
