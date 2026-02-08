"""
Module: invocation_api

Description:
Client pour communiquer avec l'API d'invocation.

Author: Copilot
Date: 2026-02-08
"""

import httpx
import asyncio
from typing import Dict, Any, Optional
import logging

from app.clients.base import BaseClient

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

    def _map_monster_to_invocation_format(
        self, monster_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convertit notre format de monstre vers le format de l'API d'invocation.
        Mapping: nom → name, rang → rank, def_ → def
        """
        skills = []
        for skill in monster_data.get("skills", []):
            skills.append(
                {
                    "name": skill.get("name"),
                    "description": skill.get("description"),
                    "damage": skill.get("damage"),
                    "ratio": {
                        "stat": skill.get("ratio", {}).get("stat"),
                        "percent": skill.get("ratio", {}).get("percent"),
                    },
                    "cooldown": int(skill.get("cooldown", 0)),
                    "lvlMax": int(skill.get("lvlMax", 5)),
                    "rank": skill.get("rank"),
                }
            )

        return {
            "name": monster_data.get("nom"),
            "element": monster_data.get("element"),
            "rank": monster_data.get("rang"),
            "stats": {
                "hp": int(monster_data.get("stats", {}).get("hp", 0)),
                "atk": int(monster_data.get("stats", {}).get("atk", 0)),
                "def": int(
                    monster_data.get("stats", {}).get(
                        "def", monster_data.get("stats", {}).get("def_", 0)
                    )
                ),
                "vit": int(monster_data.get("stats", {}).get("vit", 0)),
            },
            "visualDescription": monster_data.get("description_visuelle", ""),
            "cardDescription": monster_data.get("description_carte", ""),
            "imageUrl": monster_data.get("image_url", ""),
            "skills": skills,
        }

    async def create_monster(self, monster_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envoie un monstre à l'API d'invocation.

        Args:
            monster_data: Données du monstre dans notre format

        Returns:
            Réponse de l'API d'invocation

        Raises:
            InvocationApiError: En cas d'échec
        """
        # Convertir au format de l'API d'invocation
        payload = self._map_monster_to_invocation_format(monster_data)

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
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
