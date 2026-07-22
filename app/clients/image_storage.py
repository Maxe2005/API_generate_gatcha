"""
Module: image_storage

Description:
Logique partagée de persistance d'une image générée (peu importe le provider
IA à l'origine des bytes) vers MinIO : upload du master PNG 4K dans le bucket
brut, optimisation WebP puis upload de l'asset public. Extrait de
`ImageGenerationClient` pour être réutilisé par tous les clients de
génération d'images (Gemini, fal.ai, ...) sans dupliquer cette logique.
"""

import io
import logging
import uuid

from PIL import Image

from app.clients.minio_client import MinioClientWrapper
from app.core.config import get_settings
from app.utils.image_utils import optimize_for_web

logger = logging.getLogger(__name__)


def store_generated_image(
    raw_bytes: bytes, filename_base: str, minio_client: MinioClientWrapper
) -> dict:
    """
    Convertit des bytes d'image bruts en PNG, les stocke en 4K dans le bucket
    RAW puis stocke une version WebP optimisée dans le bucket ASSETS.

    Args:
        raw_bytes: bytes d'image bruts renvoyés par le provider IA
        filename_base: nom de fichier de base (sans extension)
        minio_client: instance de MinioClientWrapper à utiliser pour l'upload

    Returns:
        dict avec les clés:
            - image_url: URL de l'image WebP optimisée (bucket ASSETS)
            - raw_image_key: clé objet du PNG 4K (bucket RAW, usage interne)
    """
    settings = get_settings()

    image = Image.open(io.BytesIO(raw_bytes))
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    unique_id = uuid.uuid4()
    filename_raw = f"{filename_base}_{unique_id}.png"
    filename_asset = f"{filename_base}_{unique_id}.webp"

    raw_image_key = f"monsters/{filename_raw}"

    minio_client.upload_image(
        bucket_name=settings.MINIO_BUCKET_RAW,
        filename=raw_image_key,
        image_data=img_bytes,
        content_type="image/png",
    )

    webp_io = optimize_for_web(img_bytes)
    webp_bytes = webp_io.getvalue()

    image_url = minio_client.upload_image(
        bucket_name=settings.MINIO_BUCKET_ASSETS,
        filename=filename_asset,
        image_data=webp_bytes,
        content_type="image/webp",
    )

    return {"image_url": image_url, "raw_image_key": raw_image_key}
