"""
Module: invocation_api

Description:
Client pour communiquer avec l'API d'invocation.
"""

import httpx
import asyncio
from typing import Dict, Any, List
import logging
from enum import Enum

from app.clients.base import BaseClient
from app.models.monster.monster import Monster
from app.models.monster.skill import Skill

logger = logging.getLogger(__name__)


class InvocationApiError(Exception):
    """Exception pour les erreurs de l'API d'invocation"""

    pass


class InvocationApiClient(BaseClient):
    """
    Client pour communiquer avec l'API d'invocation.
    Suit le pattern des autres clients (Gemini, Banana).
    """

    def __init__(self, base_url: str = "http://localhost:8085", timeout: int = 30):
        super().__init__(api_key="", base_url=base_url)
        self.timeout = timeout
        self.max_retries = 3
        self.retry_delay = 2

    @staticmethod
    def _serialize_enum(value: Any) -> Any:
        """Retourne la valeur d'un Enum (ex: EARTH) au lieu de sa représentation Python."""
        if isinstance(value, Enum):
            return value.value
        return value

    def _map_monster_to_invocation_format(self, monster: Monster) -> Dict[str, Any]:
        """
        Convertit notre format de monstre vers le format de l'API d'invocation.
        Mapping: nom → name, rang → rank, def_ → def
        """
        monster_skills: List[Skill] = monster.skills
        skills = []
        for skill in monster_skills:
            skills.append(
                {
                    "name": skill.name,
                    "description": skill.description,
                    "damage": skill.damage,
                    "ratio": {
                        "stat": self._serialize_enum(skill.ratio_stat),
                        "percent": skill.ratio_percent,
                    },
                    "cooldown": skill.cooldown,
                    "lvlMax": skill.lvl_max,
                    "rank": self._serialize_enum(skill.rank),
                }
            )

        return {
            "name": monster.nom,
            "element": self._serialize_enum(monster.element),
            "rank": self._serialize_enum(monster.rang),
            "stats": {
                "hp": monster.hp,
                "atk": monster.atk,
                "def": monster.def_,
                "vit": monster.vit,
            },
            "visualDescription": monster.description_visuelle,
            "cardDescription": monster.description_carte,
            "imageUrl": monster.image_url,
            "skills": skills,
        }

    async def create_monster(self, monster: Monster) -> Dict[str, Any]:
        """
        Envoie un monstre à l'API d'invocation.

        Args:
            monster: Objet Monster dans notre format

        Returns:
            Réponse de l'API d'invocation

        Raises:
            InvocationApiError: En cas d'échec
        """
        # Convertir au format de l'API d'invocation
        payload = self._map_monster_to_invocation_format(monster)
        print(f"Payload for Invocation API: {payload}")

        endpoint = f"{self.base_url}/api/invocation/monsters/create"

        # Retry logic avec backoff exponentiel
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers={"accept": "*/*", "Content-Type": "application/json"},
                    )
                    print(f"Invocation API response: {response.json()}")

                    if response.status_code in [200, 201]:
                        logger.info(
                            f"Monster '{payload['name']}' transmitted successfully"
                        )
                        return response.json()
                    else:
                        error_msg = (
                            f"API returned {response.status_code}: {response.text}"
                        )
                        logger.warning(
                            f"Attempt {attempt}/{self.max_retries} failed: {error_msg}"
                        )

                        if attempt < self.max_retries:
                            await asyncio.sleep(self.retry_delay * attempt)
                        else:
                            raise InvocationApiError(error_msg)

            except httpx.TimeoutException as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} timeout: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                else:
                    raise InvocationApiError(
                        f"Timeout after {self.max_retries} attempts"
                    )

            except httpx.RequestError as e:
                logger.error(
                    f"Request error on attempt {attempt}/{self.max_retries}: {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)
                else:
                    raise InvocationApiError(f"Request failed: {str(e)}")

        raise InvocationApiError("Max retries exceeded")

    async def health_check(self) -> bool:
        """Vérifie si l'API d'invocation est accessible"""
        health_url = f"{self.base_url}/actuator/health"
        logger.info(f"Performing health check on Invocation API: {health_url}")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(health_url)
                logger.info(
                    f"Health check response: status={response.status_code}, body={response.text}"
                )
                return response.status_code == 200
        except httpx.RequestError as e:
            logger.error(f"Health check failed for {health_url}: {e}")
            return False
