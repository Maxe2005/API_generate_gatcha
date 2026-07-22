"""
Module: fal_client

Description:
Client pour la génération d'images via fal.ai (API queue-based), provider
d'images par défaut du service (voir app/clients/image_provider_factory.py).
Expose la même interface (duck-typing) que ImageGenerationClient (Gemini)
pour permettre l'interchangeabilité des providers sans que les couches
services n'aient à connaître le provider effectivement utilisé.
"""

import asyncio
import base64
import logging
from typing import Any, Dict, Optional

import httpx

from app.clients.base import BaseClient
from app.clients.image_storage import store_generated_image
from app.clients.minio_client import MinioClientWrapper
from app.core.config import get_settings
from app.core.prompts import GatchaPrompts

logger = logging.getLogger(__name__)


class FalApiError(Exception):
    """Exception pour les erreurs de l'API fal.ai"""

    pass


class FalImageClient(BaseClient):
    """
    Client pour la génération d'images via fal.ai.

    Flux queue-based: POST {base_url}/{model} -> {request_id, status_url,
    response_url}, puis polling de status_url jusqu'à COMPLETED (boucle
    distincte de la boucle de retry réseau), puis GET response_url pour
    récupérer l'URL (temporaire, hébergée par fal.ai) de l'image générée,
    téléchargée puis stockée dans MinIO via le helper partagé
    `store_generated_image` (même contrat que ImageGenerationClient).
    """

    def __init__(self):
        settings = get_settings()
        super().__init__(base_url=settings.FAL_API_BASE_URL, api_key=settings.FAL_API_KEY)
        self.settings = settings
        self.timeout = settings.FAL_TIMEOUT
        self.max_retries = settings.FAL_MAX_RETRIES
        self.retry_delay = settings.FAL_RETRY_DELAY
        self.poll_interval = settings.FAL_POLL_INTERVAL_SECONDS
        self.max_poll_attempts = settings.FAL_MAX_POLL_ATTEMPTS
        self.minio_client = MinioClientWrapper()

    def _get_headers(self) -> Dict[str, str]:
        # fal.ai utilise le schéma "Key", pas "Bearer" (le défaut de BaseClient).
        return {
            "Content-Type": "application/json",
            "Authorization": f"Key {self.api_key}",
        }

    async def _submit(self, model_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Soumet une requête de génération à la file d'attente fal.ai, avec retry réseau."""
        url = f"{self.base_url}/{model_id}"
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload, headers=self.headers)
                    if response.status_code in (200, 201):
                        return response.json()
                    error_msg = f"fal.ai a retourné {response.status_code}: {response.text}"
                    last_error = FalApiError(error_msg)
                    logger.warning(f"Tentative {attempt}/{self.max_retries} échouée: {error_msg}")
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Tentative {attempt}/{self.max_retries} timeout: {e}")
            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Tentative {attempt}/{self.max_retries} erreur réseau: {e}")

            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay * attempt)

        raise FalApiError(
            f"Échec de soumission à fal.ai après {self.max_retries} tentatives: {last_error}"
        )

    async def _poll_until_complete(self, status_url: str) -> None:
        """
        Interroge le statut jusqu'à COMPLETED. Boucle distincte de la boucle de
        retry réseau de `_submit` : ici on attend une génération lente, on ne
        retente pas une erreur.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for _ in range(self.max_poll_attempts):
                response = await client.get(status_url, headers=self.headers)
                response.raise_for_status()
                status = response.json().get("status")

                if status == "COMPLETED":
                    return
                if status == "FAILED":
                    raise FalApiError(f"Génération fal.ai échouée: {response.text}")

                await asyncio.sleep(self.poll_interval)

        raise FalApiError(
            f"Délai d'attente dépassé après {self.max_poll_attempts} interrogations de statut fal.ai"
        )

    async def _fetch_result(self, response_url: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(response_url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def _download_bytes(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    @staticmethod
    def _to_data_uri(image_bytes: bytes, content_type: str = "image/png") -> str:
        # fal.ai accepte les data URI en entrée d'image — évite de dépendre
        # d'une URL MinIO potentiellement non accessible publiquement (ex.
        # localhost en dev) pour transmettre une image de référence.
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    async def _run_generation(self, model_id: str, payload: Dict[str, Any]) -> bytes:
        """Orchestre submit -> poll -> fetch -> download, retourne les bytes de l'image générée."""
        submission = await self._submit(model_id, payload)
        status_url = submission.get("status_url")
        response_url = submission.get("response_url")
        if not status_url or not response_url:
            raise FalApiError(f"Réponse de soumission fal.ai inattendue: {submission}")

        await self._poll_until_complete(status_url)
        result = await self._fetch_result(response_url)

        images = result.get("images") or []
        if not images or not images[0].get("url"):
            raise FalApiError(f"Aucune image dans la réponse fal.ai: {result}")

        return await self._download_bytes(images[0]["url"])

    async def generate_pixel_art(
        self,
        prompt: str,
        filename_base: str,
        model: str | None = None,
        reference_image_bytes: bytes | None = None,
    ) -> dict:
        """
        Génère une image via fal.ai et la stocke dans MinIO.
        Même contrat de retour que ImageGenerationClient.generate_pixel_art :
        {"image_url": ..., "raw_image_key": ...}.
        """
        full_prompt = GatchaPrompts.IMAGE_GENERATION.format(prompt=prompt)

        if reference_image_bytes is not None:
            model = model or self.settings.FAL_IMAGE_TO_IMAGE_MODEL
            payload = {
                "prompt": full_prompt,
                "image_url": self._to_data_uri(reference_image_bytes),
            }
        else:
            model = model or self.settings.FAL_TEXT_TO_IMAGE_MODEL
            payload = {"prompt": full_prompt, "image_size": "portrait_4_3"}

        raw_bytes = await self._run_generation(model, payload)
        return store_generated_image(raw_bytes, filename_base, self.minio_client)

    async def generate_custom_image(
        self,
        prompt: str,
        aspect_ratio: str,
        image_size: str,
        model: str | None = None,
        image_input: bytes | None = None,
    ) -> bytes:
        """
        Génère une image via fal.ai avec des paramètres personnalisés.
        Retourne les bytes bruts (PNG téléchargé), sans upload MinIO — miroir
        de ImageGenerationClient.generate_custom_image. `aspect_ratio` n'a
        pas d'équivalent direct côté fal (qui utilise des presets
        `image_size`) ; conservé pour la parité de signature.
        """
        if image_input is not None:
            model = model or self.settings.FAL_IMAGE_TO_IMAGE_MODEL
            payload = {"prompt": prompt, "image_url": self._to_data_uri(image_input)}
        else:
            model = model or self.settings.FAL_TEXT_TO_IMAGE_MODEL
            payload = {"prompt": prompt, "image_size": image_size}

        return await self._run_generation(model, payload)
