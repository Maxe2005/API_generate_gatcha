#!/usr/bin/env python3
"""
Script de migration des données JSON vers PostgreSQL

Usage:
    python scripts/migrate_json_to_postgres.py

Description:
    Migre tous les monstres depuis le stockage JSON vers la base PostgreSQL.
    - Insère dans PostgreSQL avec l'état GENERATED
"""

import sys
import json
import logging
import uuid
from pathlib import Path
import os
from minio import Minio
from minio.error import S3Error

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import SessionLocal
from app.models.monster import MonsterState
from app.core.constants import MonsterStateEnum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_monsters(
    base_path: str = "app/static",
    dry_run: bool = False,
    minio_endpoint=None,
    minio_access_key=None,
    minio_secret_key=None,
    minio_bucket="game-assets",
    minio_public_url=None,
):
    """
    Migre tous les fichiers JSON du répertoire jsons vers PostgreSQL avec l'état GENERATED.

    Args:
        base_path: Chemin de base vers les fichiers statiques
        dry_run: Si True, n'insère pas réellement dans la DB
    """
    base_path_obj = Path(base_path)
    jsons_dir = base_path_obj / "jsons"

    # Préparer le client MinIO
    minio_client = None
    if minio_endpoint and minio_access_key and minio_secret_key:
        minio_client = Minio(
            minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=False,
        )

    db = SessionLocal()

    try:
        # Trouver tous les fichiers JSON
        json_files = sorted(jsons_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files")

        migrated = 0
        skipped = 0
        errors = 0

        for json_file in json_files:
            try:
                filename = json_file.name
                # Générer un ID unique basé sur le nom du fichier (sans l'extension)
                monster_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, filename))

                # Vérifier si déjà migré
                existing = (
                    db.query(MonsterState)
                    .filter(MonsterState.monster_id == monster_id)
                    .first()
                )

                if existing:
                    logger.info(
                        f"Skipping {filename} (already exists - ID: {monster_id})"
                    )
                    skipped += 1
                    continue

                # Charger les données du monstre
                with open(json_file, "r", encoding="utf-8") as f:
                    monster_data = json.load(f)

                # Recherche d'une image correspondante dans MinIO
                image_url = None
                if minio_client and minio_public_url:
                    prefix = filename.rsplit(".", 1)[0]
                    try:
                        found = False
                        for obj in minio_client.list_objects(
                            minio_bucket, prefix=prefix, recursive=True
                        ):
                            if obj.object_name and obj.object_name.startswith(prefix):
                                # Construit l'URL publique comme dans BananaClient
                                image_url = f"{minio_public_url}/{minio_bucket}/{obj.object_name}"
                                monster_data["ImageUrl"] = image_url
                                logger.info(
                                    f"Image trouvée pour {filename}: {obj.object_name}"
                                )
                                found = True
                                break
                        if not found:
                            logger.info(
                                f"Aucune image trouvée pour {filename} (préfixe: {prefix})"
                            )
                    except S3Error as e:
                        logger.error(f"Erreur MinIO pour {filename}: {e}")

                if dry_run:
                    logger.info(
                        f"[DRY RUN] Would migrate: {filename} (ID: {monster_id})"
                    )
                    migrated += 1
                    continue

                # Créer l'entrée dans la DB
                db_monster = MonsterState(
                    monster_id=monster_id,
                    state=MonsterStateEnum.GENERATED,
                    monster_data=monster_data,
                    generated_by="auto-migration",
                    generation_prompt=None,
                    is_valid=True,
                    validation_errors=None,
                    reviewed_by=None,
                    review_date=None,
                    review_notes=None,
                    transmitted_at=None,
                    transmission_attempts=0,
                    last_transmission_error=None,
                    invocation_api_id=None,
                )
                db.add(db_monster)
                db.commit()
                logger.info(f"Migrated: {filename} (ID: {monster_id})")
                migrated += 1

            except Exception as e:
                logger.error(f"Error migrating {json_file.name}: {e}")
                db.rollback()
                errors += 1

        logger.info("=" * 60)
        logger.info("Migration complete!")
        logger.info(f"  Migrated: {migrated}")
        logger.info(f"  Skipped:  {skipped}")
        logger.info(f"  Errors:   {errors}")
        logger.info("=" * 60)

    finally:
        db.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate monsters from JSON to PostgreSQL"
    )
    parser.add_argument(
        "--base-path",
        default="app/static",
        help="Base path to static files (default: app/static)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without actually inserting data",
    )
    parser.add_argument(
        "--minio-endpoint",
        default=os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
        help="MinIO endpoint (default: localhost:9000)",
    )
    parser.add_argument(
        "--minio-access-key",
        default=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        help="MinIO access key (default: minioadmin)",
    )
    parser.add_argument(
        "--minio-secret-key",
        default=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        help="MinIO secret key (default: minioadmin)",
    )
    parser.add_argument(
        "--minio-bucket",
        default=os.environ.get("MINIO_BUCKET", "game-assets"),
        help="MinIO bucket name (default: game-assets)",
    )
    parser.add_argument(
        "--minio-public-url",
        default=os.environ.get("MINIO_PUBLIC_URL", "http://localhost:9000"),
        help="MinIO public URL (default: http://localhost:9000)",
    )

    args = parser.parse_args()

    logger.info("Starting migration from JSON to PostgreSQL...")
    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be inserted")

    migrate_monsters(
        base_path=args.base_path,
        dry_run=args.dry_run,
        minio_endpoint=args.minio_endpoint,
        minio_access_key=args.minio_access_key,
        minio_secret_key=args.minio_secret_key,
        minio_bucket=args.minio_bucket,
        minio_public_url=args.minio_public_url,
    )


if __name__ == "__main__":
    main()
