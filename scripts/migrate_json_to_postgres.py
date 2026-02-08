#!/usr/bin/env python3
"""
Script de migration des données JSON vers PostgreSQL

Usage:
    python scripts/migrate_json_to_postgres.py

Description:
    Migre tous les monstres depuis le stockage JSON vers la base PostgreSQL.
    - Lit les fichiers metadata JSON
    - Lit les fichiers monster JSON correspondants
    - Insère dans PostgreSQL via SQLAlchemy
"""

import sys
import json
import logging
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.base import SessionLocal
from app.models.monster_model import Monster, StateTransitionModel, MonsterStateEnum
from app.schemas.monster import MonsterState
from app.schemas.metadata import MonsterMetadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_monster_json_path(metadata: MonsterMetadata, base_path: Path) -> Path:
    """Retrouve le chemin du fichier JSON du monstre selon son état"""
    state_dirs = {
        MonsterState.GENERATED: base_path / "jsons" / "generated",
        MonsterState.DEFECTIVE: base_path / "jsons" / "defective",
        MonsterState.CORRECTED: base_path / "jsons" / "corrected",
        MonsterState.PENDING_REVIEW: base_path / "jsons" / "pending_review",
        MonsterState.APPROVED: base_path / "jsons" / "approved",
        MonsterState.TRANSMITTED: base_path / "jsons" / "transmitted",
        MonsterState.REJECTED: base_path / "jsons" / "rejected",
    }

    # Chercher aussi dans les anciens dossiers
    possible_paths = [
        state_dirs.get(metadata.state, base_path / "jsons") / metadata.filename,
        base_path / "jsons" / metadata.filename,
        base_path / "jsons_defective" / metadata.filename,
    ]

    for path in possible_paths:
        if path.exists():
            return path

    raise FileNotFoundError(f"Monster JSON not found for {metadata.filename}")


def migrate_monsters(base_path: str = "app/static", dry_run: bool = False):
    """
    Migre les monstres depuis les fichiers JSON vers PostgreSQL.

    Args:
        base_path: Chemin de base vers les fichiers statiques
        dry_run: Si True, n'insère pas réellement dans la DB
    """
    base_path_obj = Path(base_path)
    metadata_dir = base_path_obj / "metadata"

    db = SessionLocal()

    try:
        metadata_files = list(metadata_dir.glob("*_metadata.json"))
        logger.info(f"Found {len(metadata_files)} metadata files")

        migrated = 0
        skipped = 0
        errors = 0

        for metadata_file in metadata_files:
            try:
                # Charger les métadonnées
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                    metadata = MonsterMetadata(**metadata_dict)

                # Vérifier si déjà migré
                existing = (
                    db.query(Monster)
                    .filter(Monster.monster_id == metadata.monster_id)
                    .first()
                )

                if existing:
                    logger.info(f"Skipping {metadata.monster_id} (already exists)")
                    skipped += 1
                    continue

                # Charger les données du monstre
                try:
                    monster_path = get_monster_json_path(metadata, base_path_obj)
                    with open(monster_path, "r", encoding="utf-8") as f:
                        monster_data = json.load(f)
                except FileNotFoundError as e:
                    logger.warning(f"Skipping {metadata.monster_id}: {e}")
                    skipped += 1
                    continue

                if dry_run:
                    logger.info(f"[DRY RUN] Would migrate: {metadata.monster_id}")
                    migrated += 1
                    continue

                # Créer l'entrée dans la DB
                db_monster = Monster(
                    monster_id=metadata.monster_id,
                    filename=metadata.filename,
                    state=MonsterStateEnum(metadata.state.value),
                    monster_data=monster_data,
                    generated_by=metadata.generated_by,
                    generation_prompt=metadata.generation_prompt,
                    is_valid=metadata.is_valid,
                    validation_errors=metadata.validation_errors,
                    reviewed_by=metadata.reviewed_by,
                    review_date=metadata.review_date,
                    review_notes=metadata.review_notes,
                    transmitted_at=metadata.transmitted_at,
                    transmission_attempts=metadata.transmission_attempts,
                    last_transmission_error=metadata.last_transmission_error,
                    invocation_api_id=metadata.invocation_api_id,
                    metadata_extra=metadata.metadata,
                    created_at=metadata.created_at,
                    updated_at=metadata.updated_at,
                )
                db.add(db_monster)

                # Ajouter l'historique des transitions
                for transition in metadata.history:
                    db_transition = StateTransitionModel(
                        monster=db_monster,
                        from_state=MonsterStateEnum(transition.from_state.value)
                        if transition.from_state
                        else None,
                        to_state=MonsterStateEnum(transition.to_state.value),
                        timestamp=transition.timestamp,
                        actor=transition.actor,
                        note=transition.note,
                    )
                    db.add(db_transition)

                db.commit()
                logger.info(f"Migrated: {metadata.monster_id} ({metadata.filename})")
                migrated += 1

            except Exception as e:
                logger.error(f"Error migrating {metadata_file.name}: {e}")
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
