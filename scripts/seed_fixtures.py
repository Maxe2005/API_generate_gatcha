#!/usr/bin/env python3
"""
Seed des fixtures (Postgres + MinIO) — idempotent.

Pour chaque fixtures/monsters/<slug>.json :
- valide le JSON (structure/enums/ranges) ;
- si fixtures/images/<slug>.png existe : upload du master PNG dans
  raw-assets/monsters/<slug>.png et du WebP optimisé dans
  game-assets/<slug>.webp (sautés si les objets existent déjà), puis
  renseigne ImageUrl et RawImageKey dans le JSON ;
- insère un MonsterState en état GENERATED avec un monster_id
  déterministe (uuid5 du nom de fichier, compatible avec l'ancien script
  de migration) — sauté si le monstre existe déjà.

Options:
    --process       après le seed, valide et transitionne chaque monstre
                    (PENDING_REVIEW si valide+image, DEFECTIVE sinon)
    --pairs-only    ne seed que les monstres qui ont une image associée
    --dry-run       affiche le plan sans toucher ni à la DB ni à MinIO

Usage:
    python scripts/seed_fixtures.py [--process] [--pairs-only] [--dry-run]
"""

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

# Permettre les imports de l'application depuis scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.constants import MonsterStateEnum
from app.core.json_monster_config import MonsterJsonAttributes
from app.services.validation_service import MonsterValidationService
from app.utils.image_keys import RAW_PREFIX

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_fixtures")

FIXTURES_DIR = Path("fixtures")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")


def monster_id_for_slug(slug: str) -> str:
    """UUID déterministe, compatible avec l'ancien script de migration
    (uuid5 sur le nom de fichier JSON)."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{slug}.json"))


def find_image(images_dir: Path, slug: str) -> Path | None:
    for suffix in IMAGE_SUFFIXES:
        candidate = images_dir / f"{slug}{suffix}"
        if candidate.exists():
            return candidate
    return None


def collect_fixtures(fixtures_dir: Path) -> list[dict]:
    """Charge et valide les fixtures ; retourne une liste d'entrées prêtes à seeder."""
    monsters_dir = fixtures_dir / "monsters"
    images_dir = fixtures_dir / "images"
    validator = MonsterValidationService()

    entries = []
    for json_file in sorted(monsters_dir.glob("*.json")):
        slug = json_file.stem
        data = json.loads(json_file.read_text(encoding="utf-8"))
        result = validator.validate(data)
        entries.append(
            {
                "slug": slug,
                "monster_id": monster_id_for_slug(slug),
                "data": data,
                "image": find_image(images_dir, slug),
                "is_valid": result.is_valid,
                "errors": [f"{e.field}: {e.message}" for e in result.errors],
            }
        )
    return entries


def seed_image(minio_client, settings, entry: dict) -> None:
    """Upload raw + webp si absents, et renseigne ImageUrl/RawImageKey."""
    from app.utils.image_utils import optimize_for_web

    slug = entry["slug"]
    image_path: Path = entry["image"]
    raw_key = f"{RAW_PREFIX}/{slug}.png"
    asset_name = f"{slug}.webp"

    raw_bytes = image_path.read_bytes()

    if not minio_client.object_exists(settings.MINIO_BUCKET_RAW, raw_key):
        minio_client.upload_image(
            bucket_name=settings.MINIO_BUCKET_RAW,
            filename=raw_key,
            image_data=raw_bytes,
            content_type="image/png",
        )
        logger.info(f"  ↳ upload raw   {settings.MINIO_BUCKET_RAW}/{raw_key}")

    if not minio_client.object_exists(settings.MINIO_BUCKET_ASSETS, asset_name):
        webp_bytes = optimize_for_web(raw_bytes).getvalue()
        minio_client.upload_image(
            bucket_name=settings.MINIO_BUCKET_ASSETS,
            filename=asset_name,
            image_data=webp_bytes,
            content_type="image/webp",
        )
        logger.info(f"  ↳ upload asset {settings.MINIO_BUCKET_ASSETS}/{asset_name}")

    entry["data"][MonsterJsonAttributes.IMAGE_URL.value] = (
        f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET_ASSETS}/{asset_name}"
    )
    entry["data"][MonsterJsonAttributes.RAW_IMAGE_KEY.value] = raw_key


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed des fixtures Postgres + MinIO")
    parser.add_argument("--fixtures-dir", default=str(FIXTURES_DIR))
    parser.add_argument("--pairs-only", action="store_true",
                        help="Ne seed que les monstres ayant une image associée")
    parser.add_argument("--process", action="store_true",
                        help="Valide et transitionne les monstres seedés")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche le plan sans toucher à la DB ni à MinIO")
    args = parser.parse_args()

    fixtures_dir = Path(args.fixtures_dir)
    entries = collect_fixtures(fixtures_dir)
    if args.pairs_only:
        entries = [e for e in entries if e["image"]]

    with_image = sum(1 for e in entries if e["image"])
    invalid = [e for e in entries if not e["is_valid"]]
    logger.info(
        f"{len(entries)} fixtures ({with_image} avec image, {len(invalid)} invalides)"
    )
    for e in invalid:
        logger.warning(f"fixture invalide {e['slug']}: {'; '.join(e['errors'])}")

    if args.dry_run:
        for e in entries:
            image = e["image"].name if e["image"] else "—"
            logger.info(f"[dry-run] {e['slug']:45s} image={image:30s} id={e['monster_id']}")
        return 0

    # Imports différés : la connexion DB/MinIO n'est requise qu'ici
    from app.clients.minio_client import MinioClientWrapper
    from app.models.base import SessionLocal, init_db
    from app.models.monster import MonsterState

    settings = get_settings()
    init_db()
    minio_client = MinioClientWrapper()
    db = SessionLocal()

    created = skipped = processed = 0
    seeded_ids = []
    try:
        for entry in entries:
            slug, monster_id = entry["slug"], entry["monster_id"]

            if entry["image"]:
                seed_image(minio_client, settings, entry)

            existing = (
                db.query(MonsterState)
                .filter(MonsterState.monster_id == monster_id)
                .first()
            )
            if existing:
                logger.info(f"= {slug} déjà en base ({existing.state}), sauté")
                skipped += 1
                continue

            db.add(
                MonsterState(
                    monster_id=monster_id,
                    state=MonsterStateEnum.GENERATED,
                    monster_data=entry["data"],
                    generated_by="fixtures",
                    is_valid=entry["is_valid"],
                    validation_errors=(
                        [{"field": "", "error_type": "fixture", "message": m}
                         for m in entry["errors"]] or None
                    ),
                )
            )
            db.commit()
            logger.info(f"+ {slug} seedé (GENERATED, image={'oui' if entry['image'] else 'non'})")
            created += 1
            seeded_ids.append(monster_id)

        if args.process and seeded_ids:
            from app.services.admin_service import AdminService

            admin = AdminService(db)
            for monster_id in seeded_ids:
                outcome = admin.process_generated_monster(monster_id)
                logger.info(f"process {monster_id}: {outcome.get('action', outcome.get('status'))}")
                processed += 1
    finally:
        db.close()

    logger.info("=" * 60)
    logger.info(f"Seed terminé : {created} créés, {skipped} déjà présents"
                + (f", {processed} traités" if args.process else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
