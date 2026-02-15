"""
Script de migration des monstres existants

Ce script migre les monstres existants vers le nouveau système
de gestion du cycle de vie.
"""

import json
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.metadata import MonsterMetadata, StateTransition
from app.core.constants import MonsterStateEnum


def migrate_existing_monsters():
    """Migre les monstres existants vers le nouveau système"""

    print("🔄 Starting migration of existing monsters...\n")

    # Créer les dossiers nécessaires
    metadata_dir = Path("app/static/metadata")
    metadata_dir.mkdir(parents=True, exist_ok=True)

    # Monstres valides
    valid_jsons_dir = Path("app/static/jsons")
    if valid_jsons_dir.exists():
        valid_files = [f for f in valid_jsons_dir.glob("*.json") if f.is_file()]

        print(f"Found {len(valid_files)} valid monsters to migrate")

        for json_file in valid_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    monster_data = json.load(f)

                # Créer un ID unique
                monster_id = str(uuid.uuid4())

                # Créer les métadonnées
                metadata = MonsterMetadata(
                    monster_id=monster_id,
                    filename=json_file.name,
                    state=MonsterStateEnum.TRANSMITTED,
                    created_at=datetime.fromtimestamp(json_file.stat().st_ctime),
                    updated_at=datetime.fromtimestamp(json_file.stat().st_mtime),
                    generated_by="gemini",
                    is_valid=True,
                    transmitted_at=datetime.now(timezone.utc),
                    metadata={
                        "image_url": monster_data.get("image_url", ""),
                        "json_path": f"/static/jsons/transmitted/{json_file.name}",
                    },
                    history=[
                        StateTransition(
                            from_state=None,
                            to_state=MonsterStateEnum.TRANSMITTED,
                            timestamp=datetime.now(timezone.utc),
                            actor="system",
                            note="Migrated from existing system",
                        )
                    ],
                )

                # Sauvegarder les métadonnées
                metadata_path = metadata_dir / f"{monster_id}_metadata.json"
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(
                        metadata.model_dump(mode="json"),
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

                # Déplacer le fichier vers transmitted
                transmitted_dir = Path("app/static/jsons/transmitted")
                transmitted_dir.mkdir(parents=True, exist_ok=True)
                new_path = transmitted_dir / json_file.name

                if not new_path.exists():
                    json_file.rename(new_path)
                    print(f"  ✓ Migrated: {json_file.name} → transmitted/")
                else:
                    print(f"  ⚠ Skipped (already exists): {json_file.name}")

            except Exception as e:
                print(f"  ✗ Failed to migrate {json_file.name}: {e}")

    # Monstres défectueux
    defective_dir = Path("app/static/jsons_defective")
    if defective_dir.exists():
        defective_files = list(defective_dir.glob("*.json"))

        print(f"\nFound {len(defective_files)} defective monsters to migrate")

        for json_file in defective_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Extraire les données
                monster_data = data.get("monster_data", {})
                validation_errors = data.get("validation_errors", [])

                # Créer un ID unique
                monster_id = str(uuid.uuid4())

                # Créer les métadonnées
                metadata = MonsterMetadata(
                    monster_id=monster_id,
                    filename=json_file.name,
                    state=MonsterStateEnum.DEFECTIVE,
                    created_at=datetime.fromtimestamp(json_file.stat().st_ctime),
                    updated_at=datetime.fromtimestamp(json_file.stat().st_mtime),
                    generated_by="gemini",
                    is_valid=False,
                    validation_errors=validation_errors,
                    metadata={"json_path": f"/static/jsons/defective/{json_file.name}"},
                    history=[
                        StateTransition(
                            from_state=None,
                            to_state=MonsterStateEnum.DEFECTIVE,
                            timestamp=datetime.now(timezone.utc),
                            actor="system",
                            note="Migrated from existing system (defective)",
                        )
                    ],
                )

                # Sauvegarder les métadonnées
                metadata_path = metadata_dir / f"{monster_id}_metadata.json"
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(
                        metadata.model_dump(mode="json"),
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

                # Déplacer et nettoyer le fichier (garder uniquement monster_data)
                defective_new_dir = Path("app/static/jsons/defective")
                defective_new_dir.mkdir(parents=True, exist_ok=True)
                new_path = defective_new_dir / json_file.name

                with open(new_path, "w", encoding="utf-8") as f:
                    json.dump(monster_data, f, indent=2, ensure_ascii=False)

                json_file.unlink()  # Supprimer l'ancien

                print(f"  ✓ Migrated defective: {json_file.name} → defective/")

            except Exception as e:
                print(f"  ✗ Failed to migrate defective {json_file.name}: {e}")

    print("\n✅ Migration completed!")


if __name__ == "__main__":
    migrate_existing_monsters()
