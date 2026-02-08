#!/usr/bin/env python3
"""
Script de migration des données JSON vers PostgreSQL

Usage:
    python scripts/migrate_json_to_postgres.py

Description:
    Migre tous les monstres depuis le stockage JSON vers la base PostgreSQL.
    - Lit tous les fichiers JSON du répertoire app/static/jsons/
    - Insère dans PostgreSQL avec l'état GENERATED
"""

import sys
import json
import logging
import uuid
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import SessionLocal
from app.models.monster_model import Monster, MonsterStateEnum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_monsters(base_path: str = "app/static", dry_run: bool = False):
    """
    Migre tous les fichiers JSON du répertoire jsons vers PostgreSQL avec l'état GENERATED.

    Args:
        base_path: Chemin de base vers les fichiers statiques
        dry_run: Si True, n'insère pas réellement dans la DB
    """
    base_path_obj = Path(base_path)
    jsons_dir = base_path_obj / "jsons"

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
                    db.query(Monster).filter(Monster.monster_id == monster_id).first()
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

                if dry_run:
                    logger.info(
                        f"[DRY RUN] Would migrate: {filename} (ID: {monster_id})"
                    )
                    migrated += 1
                    continue

                # Créer l'entrée dans la DB
                db_monster = Monster(
                    monster_id=monster_id,
                    filename=filename,
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
                    metadata_extra={},
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

    args = parser.parse_args()

    logger.info("Starting migration from JSON to PostgreSQL...")
    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be inserted")

    migrate_monsters(base_path=args.base_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
