"""
Module: image_keys

Description:
Convention de nommage entre les deux buckets MinIO :
- bucket assets (public)  : <stem>.webp            (image optimisée web)
- bucket raw (privé)      : monsters/<stem>.png    (master haute résolution)

Ce module centralise la dérivation de la clé raw depuis une URL d'asset,
utilisée en secours quand la clé exacte n'a pas été persistée.
"""

from pathlib import PurePosixPath
from typing import Optional
from urllib.parse import unquote, urlparse

RAW_PREFIX = "monsters"


def derive_raw_key_from_asset_url(asset_url: Optional[str]) -> Optional[str]:
    """
    Dérive la clé de l'image raw (bucket privé) depuis l'URL publique de
    l'asset WebP, par convention de nommage partagée (même stem).

    Ex: http://localhost:9000/game-assets/dragon_abc.webp
        -> monsters/dragon_abc.png

    Returns:
        La clé raw, ou None si l'URL est vide/inexploitable.
    """
    if not asset_url:
        return None

    path = urlparse(asset_url).path
    name = PurePosixPath(unquote(path)).name
    if not name:
        return None

    stem = name.rsplit(".", 1)[0]
    if not stem:
        return None

    return f"{RAW_PREFIX}/{stem}.png"
