"""
Controller: génération d'URLs présignées pour les images high-res

Ce module centralise la logique utilisée par l'endpoint `/images/signed-urls`.
"""

from typing import List
import logging

from app.core.config import get_settings
from app.clients.minio_client import MinioClientWrapper
from app.schemas.image import SignedUrlRequestItem, SignedUrlResponseItem

logger = logging.getLogger(__name__)


def generate_signed_urls(
    items: List[SignedUrlRequestItem],
) -> List[SignedUrlResponseItem]:
    """Génère une liste d'objets SignedUrlResponseItem pour les items fournis.

    - Valide la taille de la requête
    - Recherche la `raw_image_key` en base, sinon la dérive depuis l'URL fournie
    - Génère une URL présignée via MinIO
    """
    settings = get_settings()
    max_items = getattr(settings, "SIGNED_URLS_MAX_ITEMS", 50)
    expires = getattr(settings, "SIGNED_URLS_EXPIRES_SECONDS", 120)

    if not items:
        return []
    if len(items) > max_items:
        raise ValueError(f"Too many items: max {max_items}")

    minio = MinioClientWrapper()
    results: List[SignedUrlResponseItem] = []

    for it in items:
        signed_url = None
        error = None
        try:
            settings.MINIO_BUCKET_ASSETS
            url = it.url
            if settings.MINIO_BUCKET_ASSETS not in url:
                raise ValueError(f"URL does not contain expected bucket name: {url}")
            parsed = url.split(settings.MINIO_BUCKET_ASSETS)
            if len(parsed) != 2:
                raise ValueError(f"URL parsing failed for bucket name: {url}")
            raw_key = "monsters/" + parsed[1].lstrip("/").replace(".webp", ".png")
            signed_url = minio.presigned_get_object(raw_key, expires_seconds=expires)
        except Exception as e:
            logger.exception("Erreur génération signed url")
            error = str(e)

        results.append(
            SignedUrlResponseItem(
                id=it.id,
                input_url=it.url,
                signed_url=signed_url,
                expires_in=expires if signed_url else 0,
                error=error,
            )
        )

    return results
