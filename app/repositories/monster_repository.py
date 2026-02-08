"""
Module: monster_repository

Description:
Gère la persistance des monstres et de leurs métadonnées.

Author: Copilot
Date: 2026-02-08
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.schemas.metadata import MonsterMetadata, MonsterWithMetadata
from app.schemas.monster import MonsterState

logger = logging.getLogger(__name__)


class MonsterRepository:
    """
    Gère la persistance des monstres et de leurs métadonnées.
    Actuellement utilise JSON, mais architecture prête pour une vraie DB.
    """

    def __init__(self, base_path: str = "app/static"):
        self.base_path = Path(base_path)
        self.metadata_dir = self.base_path / "metadata"
        self.images_dir = self.base_path / "images"

        # Dossiers par état
        self.jsons_dir = self.base_path / "jsons"
        self.state_dirs = {
            MonsterState.GENERATED: self.jsons_dir / "generated",
            MonsterState.DEFECTIVE: self.jsons_dir / "defective",
            MonsterState.CORRECTED: self.jsons_dir / "corrected",
            MonsterState.PENDING_REVIEW: self.jsons_dir / "pending_review",
            MonsterState.APPROVED: self.jsons_dir / "approved",
            MonsterState.TRANSMITTED: self.jsons_dir / "transmitted",
            MonsterState.REJECTED: self.jsons_dir / "rejected",
        }

        self._ensure_directories()

    def _ensure_directories(self):
        """Crée tous les dossiers nécessaires"""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        for state_dir in self.state_dirs.values():
            state_dir.mkdir(parents=True, exist_ok=True)

    def _get_metadata_path(self, monster_id: str) -> Path:
        """Retourne le chemin du fichier de métadonnées"""
        return self.metadata_dir / f"{monster_id}_metadata.json"

    def _get_monster_path(self, metadata: MonsterMetadata) -> Path:
        """Retourne le chemin du fichier JSON du monstre selon son état"""
        state_dir = self.state_dirs.get(metadata.state)
        return state_dir / metadata.filename

    def save(self, metadata: MonsterMetadata, monster_data: Dict[str, Any]) -> bool:
        """
        Sauvegarde un monstre et ses métadonnées.

        Args:
            metadata: Métadonnées du monstre
            monster_data: Données du monstre

        Returns:
            True si succès
        """
        try:
            # Sauvegarder les métadonnées
            metadata_path = self._get_metadata_path(metadata.monster_id)
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(
                    metadata.model_dump(mode="json"), f, indent=2, ensure_ascii=False
                )

            # Sauvegarder les données du monstre
            monster_path = self._get_monster_path(metadata)
            with open(monster_path, "w", encoding="utf-8") as f:
                json.dump(monster_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved monster {metadata.monster_id} to {monster_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save monster {metadata.monster_id}: {e}")
            return False

    def get(self, monster_id: str) -> Optional[MonsterWithMetadata]:
        """Récupère un monstre avec ses métadonnées"""
        try:
            # Charger les métadonnées
            metadata_path = self._get_metadata_path(monster_id)
            if not metadata_path.exists():
                return None

            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)
                metadata = MonsterMetadata(**metadata_dict)

            # Charger les données du monstre
            monster_path = self._get_monster_path(metadata)
            if not monster_path.exists():
                logger.warning(
                    f"Metadata exists but monster file not found: {monster_path}"
                )
                return None

            with open(monster_path, "r", encoding="utf-8") as f:
                monster_data = json.load(f)

            return MonsterWithMetadata(metadata=metadata, monster_data=monster_data)

        except Exception as e:
            logger.error(f"Failed to get monster {monster_id}: {e}")
            return None

    def list_by_state(
        self, state: MonsterState, limit: int = 50, offset: int = 0
    ) -> List[MonsterMetadata]:
        """Liste les monstres par état"""
        try:
            metadata_files = sorted(
                self.metadata_dir.glob("*_metadata.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            results = []
            for metadata_file in metadata_files[offset:]:
                if len(results) >= limit:
                    break

                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                    metadata = MonsterMetadata(**metadata_dict)

                    if metadata.state == state:
                        results.append(metadata)

            return results

        except Exception as e:
            logger.error(f"Failed to list monsters by state {state}: {e}")
            return []

    def list_all(self, limit: int = 50, offset: int = 0) -> List[MonsterMetadata]:
        """Liste tous les monstres"""
        try:
            metadata_files = sorted(
                self.metadata_dir.glob("*_metadata.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            results = []
            for metadata_file in metadata_files[offset : offset + limit]:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                    metadata = MonsterMetadata(**metadata_dict)
                    results.append(metadata)

            return results

        except Exception as e:
            logger.error(f"Failed to list all monsters: {e}")
            return []

    def move_to_state(self, monster_id: str, new_state: MonsterState) -> bool:
        """Déplace le fichier JSON d'un monstre vers le dossier de son nouvel état"""
        try:
            monster = self.get(monster_id)
            if not monster:
                return False

            old_path = self._get_monster_path(monster.metadata)

            # Mettre à jour l'état dans les métadonnées
            monster.metadata.state = new_state
            new_path = self._get_monster_path(monster.metadata)

            # Déplacer le fichier
            if old_path.exists():
                old_path.rename(new_path)
                logger.info(f"Moved monster file: {old_path} → {new_path}")

            return True

        except Exception as e:
            logger.error(
                f"Failed to move monster {monster_id} to state {new_state}: {e}"
            )
            return False

    def delete(self, monster_id: str) -> bool:
        """Supprime un monstre et ses métadonnées"""
        try:
            monster = self.get(monster_id)
            if not monster:
                return False

            # Supprimer le fichier JSON
            monster_path = self._get_monster_path(monster.metadata)
            if monster_path.exists():
                monster_path.unlink()

            # Supprimer les métadonnées
            metadata_path = self._get_metadata_path(monster_id)
            if metadata_path.exists():
                metadata_path.unlink()

            logger.info(f"Deleted monster {monster_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete monster {monster_id}: {e}")
            return False

    def count_by_state(self) -> Dict[str, int]:
        """Compte les monstres par état"""
        counts = {state.value: 0 for state in MonsterState}

        try:
            for metadata_file in self.metadata_dir.glob("*_metadata.json"):
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                    state = metadata_dict.get("state")
                    if state in counts:
                        counts[state] += 1
        except Exception as e:
            logger.error(f"Failed to count by state: {e}")

        return counts
