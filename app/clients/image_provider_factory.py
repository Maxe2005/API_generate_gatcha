"""
Module: image_provider_factory

Description:
Point d'entrée unique pour construire un client de génération d'images
selon le provider choisi. fal.ai (`ImageProviderEnum.FAL`) est le provider
par défaut ; Gemini reste disponible comme alternative
(`ImageProviderEnum.GEMINI`).
"""

from app.clients.fal_client import FalImageClient
from app.clients.image_generation_client import ImageGenerationClient
from app.core.constants import ImageProviderEnum


def get_image_client(
    provider: ImageProviderEnum = ImageProviderEnum.FAL,
) -> ImageGenerationClient | FalImageClient:
    """Construit une instance du client de génération d'images pour le provider donné."""
    if provider == ImageProviderEnum.GEMINI:
        return ImageGenerationClient()
    return FalImageClient()
