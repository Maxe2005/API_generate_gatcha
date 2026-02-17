"""
Module: monster_modification_service

Description:
Service pour la modification des monstres structurés (à partir de PENDING_REVIEW).
Toutes les modifications de monstres doivent passer par ce service pour :
- Garantir la cohérence des données
- Valider les modifications
- Enregistrer l'historique
- Respecter les règles métier

Principes appliqués :
- Single Responsibility : Gère uniquement les modifications de monstres structurés
- DRY : Logique de validation et de mise à jour centralisée
- Modularité : Peut être facilement étendu et testé
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

from app.models.monster import Monster, Skill, MonsterState
from app.schemas.monster import MonsterUpdate, MonsterStructured 
from app.schemas.skill import SkillCreate, SkillUpdate, SkillStructured

from app.core.constants import MonsterStateEnum
from app.repositories.monster import MonsterRepository

logger = logging.getLogger(__name__)


class MonsterModificationError(Exception):
    """Exception levée lors d'une erreur de modification"""

    pass


class MonsterModificationService:
    """
    Service pour modifier les monstres structurés en base de données.

    Ce service est le point d'entrée unique pour toute modification de monstres
    à partir de l'état PENDING_REVIEW (quand les données sont structurées).

    Responsabilités :
    - Validation des modifications
    - Mise à jour des données (monstre + skills)
    - Gestion des contraintes métier
    - Historisation des changements
    """

    def __init__(self, db: Session):
        """
        Initialise le service avec une session de base de données.

        Args:
            db: Session SQLAlchemy
        """
        self.db = db
        self.monster_repo = MonsterRepository(db)

    def _check_monster_is_modifiable(self, monster_state: MonsterState) -> None:
        """
        Vérifie qu'un monstre peut être modifié.

        Un monstre ne peut être modifié que s'il est dans un état structuré
        (PENDING_REVIEW, APPROVED) et non transmis.

        Args:
            monster_state: État du monstre

        Raises:
            MonsterModificationError: Si le monstre n'est pas modifiable
        """
        allowed_states = [
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.APPROVED,
        ]

        if monster_state.state not in allowed_states:
            raise MonsterModificationError(
                f"Cannot modify monster in state {monster_state.state}. "
                f"Monster must be in {allowed_states}"
            )

        if not monster_state.monster:
            raise MonsterModificationError(
                "Monster is not structured yet. Cannot modify JSON data through this service."
            )

    def update_monster(
        self,
        monster_id: str,
        updates: MonsterUpdate,
        actor: str = "admin",
    ) -> MonsterStructured:
        """
        Met à jour les données d'un monstre structuré.

        Args:
            monster_id: UUID du monstre
            updates: Données à mettre à jour
            actor: Qui effectue la modification

        Returns:
            Monstre mis à jour avec ses skills

        Raises:
            MonsterModificationError: Si le monstre n'existe pas ou n'est pas modifiable
        """
        logger.info(f"Updating monster {monster_id} by {actor}")

        # Récupérer le monstre et son état
        monster_state = self.monster_repo.get_by_uuid(monster_id)
        if not monster_state:
            raise MonsterModificationError(f"Monster {monster_id} not found")

        # Vérifier que le monstre est modifiable
        self._check_monster_is_modifiable(monster_state)

        monster = monster_state.monster

        # Appliquer les modifications
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(monster, field):
                setattr(monster, field, value)

        # Mettre à jour le timestamp
        monster.updated_at = datetime.now(timezone.utc)
        monster_state.updated_at = datetime.now(timezone.utc)  # type: ignore

        # Persister
        self.db.commit()
        self.db.refresh(monster)
        self.db.refresh(monster_state)

        logger.info(f"Monster {monster_id} updated successfully")

        return MonsterStructured.model_validate(monster)

    def add_skill(
        self,
        monster_id: str,
        skill_data: SkillCreate,
        actor: str = "admin",
    ) -> SkillStructured:
        """
        Ajoute une nouvelle compétence à un monstre.

        Args:
            monster_id: UUID du monstre
            skill_data: Données de la compétence
            actor: Qui effectue l'ajout

        Returns:
            Compétence créée

        Raises:
            MonsterModificationError: Si le monstre n'existe pas ou n'est pas modifiable
        """
        logger.info(f"Adding skill to monster {monster_id} by {actor}")

        # Récupérer le monstre et son état
        monster_state = self.monster_repo.get_by_uuid(monster_id)
        if not monster_state:
            raise MonsterModificationError(f"Monster {monster_id} not found")

        # Vérifier que le monstre est modifiable
        self._check_monster_is_modifiable(monster_state)

        monster = monster_state.monster

        # Créer la nouvelle skill
        new_skill = Skill(
            monster_id=monster.id,
            name=skill_data.name,
            description=skill_data.description,
            damage=skill_data.damage,
            cooldown=skill_data.cooldown,
            lvl_max=skill_data.lvl_max,
            rank=skill_data.rank,
            ratio_stat=skill_data.ratio_stat,
            ratio_percent=skill_data.ratio_percent,
        )

        self.db.add(new_skill)
        monster_state.updated_at = datetime.now(timezone.utc)  # type: ignore
        self.db.commit()
        self.db.refresh(new_skill)

        logger.info(f"Skill '{skill_data.name}' added to monster {monster_id}")

        return SkillStructured.model_validate(new_skill)

    def update_skill(
        self,
        monster_id: str,
        skill_id: int,
        updates: SkillUpdate,
        actor: str = "admin",
    ) -> SkillStructured:
        """
        Met à jour une compétence d'un monstre.

        Args:
            monster_id: UUID du monstre
            skill_id: ID de la compétence
            updates: Données à mettre à jour
            actor: Qui effectue la modification

        Returns:
            Compétence mise à jour

        Raises:
            MonsterModificationError: Si le monstre ou la skill n'existe pas
        """
        logger.info(f"Updating skill {skill_id} of monster {monster_id} by {actor}")

        # Récupérer le monstre et son état
        monster_state = self.monster_repo.get_by_uuid(monster_id)
        if not monster_state:
            raise MonsterModificationError(f"Monster {monster_id} not found")

        # Vérifier que le monstre est modifiable
        self._check_monster_is_modifiable(monster_state)

        monster = monster_state.monster

        # Récupérer la skill
        skill = (
            self.db.query(Skill)
            .filter(Skill.id == skill_id, Skill.monster_id == monster.id)
            .first()
        )

        if not skill:
            raise MonsterModificationError(
                f"Skill {skill_id} not found for monster {monster_id}"
            )

        # Appliquer les modifications
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(skill, field):
                setattr(skill, field, value)

        # Mettre à jour les timestamps
        skill.updated_at = datetime.now(timezone.utc)  # type: ignore
        monster_state.updated_at = datetime.now(timezone.utc)  # type: ignore

        self.db.commit()
        self.db.refresh(skill)

        logger.info(f"Skill {skill_id} updated successfully")

        return SkillStructured.model_validate(skill)

    def delete_skill(
        self,
        monster_id: str,
        skill_id: int,
        actor: str = "admin",
    ) -> None:
        """
        Supprime une compétence d'un monstre.

        Args:
            monster_id: UUID du monstre
            skill_id: ID de la compétence
            actor: Qui effectue la suppression

        Raises:
            MonsterModificationError: Si le monstre ou la skill n'existe pas
        """
        logger.info(f"Deleting skill {skill_id} of monster {monster_id} by {actor}")

        # Récupérer le monstre et son état
        monster_state = self.monster_repo.get_by_uuid(monster_id)
        if not monster_state:
            raise MonsterModificationError(f"Monster {monster_id} not found")

        # Vérifier que le monstre est modifiable
        self._check_monster_is_modifiable(monster_state)

        monster = monster_state.monster

        # Récupérer la skill
        skill = (
            self.db.query(Skill)
            .filter(Skill.id == skill_id, Skill.monster_id == monster.id)
            .first()
        )

        if not skill:
            raise MonsterModificationError(
                f"Skill {skill_id} not found for monster {monster_id}"
            )

        # Vérifier qu'on ne supprime pas la dernière skill
        skill_count = (
            self.db.query(Skill).filter(Skill.monster_id == monster.id).count()
        )

        if skill_count <= 1:
            raise MonsterModificationError(
                "Cannot delete the last skill. Monster must have at least one skill."
            )

        # Supprimer la skill
        self.db.delete(skill)
        monster_state.updated_at = datetime.now(timezone.utc)  # type: ignore
        self.db.commit()

        logger.info(f"Skill {skill_id} deleted successfully")

    def get_monster_with_skills(self, monster_id: str) -> Optional[MonsterStructured]:
        """
        Récupère un monstre structuré avec toutes ses compétences.

        Args:
            monster_id: UUID du monstre

        Returns:
            Monstre structuré avec ses skills, ou None si non trouvé
        """
        monster_state = self.monster_repo.get_by_uuid(monster_id)
        if not monster_state or not monster_state.monster:
            return None

        return MonsterStructured.model_validate(monster_state.monster)

    def replace_all_skills(
        self,
        monster_id: str,
        skills_data: List[SkillCreate],
        actor: str = "admin",
    ) -> List[SkillStructured]:
        """
        Remplace toutes les compétences d'un monstre.

        Utile pour une mise à jour complète des skills.

        Args:
            monster_id: UUID du monstre
            skills_data: Liste des nouvelles compétences
            actor: Qui effectue le remplacement

        Returns:
            Liste des compétences créées

        Raises:
            MonsterModificationError: Si le monstre n'existe pas ou liste vide
        """
        logger.info(
            f"Replacing all skills of monster {monster_id} with {len(skills_data)} new skills by {actor}"
        )

        if not skills_data:
            raise MonsterModificationError(
                "Cannot replace skills with empty list. Monster must have at least one skill."
            )

        # Récupérer le monstre et son état
        monster_state = self.monster_repo.get_by_uuid(monster_id)
        if not monster_state:
            raise MonsterModificationError(f"Monster {monster_id} not found")

        # Vérifier que le monstre est modifiable
        self._check_monster_is_modifiable(monster_state)

        monster = monster_state.monster

        # Supprimer les skills existantes
        self.db.query(Skill).filter(Skill.monster_id == monster.id).delete()

        # Créer les nouvelles skills
        new_skills = []
        for skill_data in skills_data:
            skill = Skill(
                monster_id=monster.id,
                name=skill_data.name,
                description=skill_data.description,
                damage=skill_data.damage,
                cooldown=skill_data.cooldown,
                lvl_max=skill_data.lvl_max,
                rank=skill_data.rank,
                ratio_stat=skill_data.ratio_stat,
                ratio_percent=skill_data.ratio_percent,
            )
            self.db.add(skill)
            new_skills.append(skill)

        monster_state.updated_at = datetime.now(timezone.utc)  # type: ignore
        self.db.commit()

        # Refresh all new skills
        for skill in new_skills:
            self.db.refresh(skill)

        logger.info(f"All skills replaced for monster {monster_id}")

        return [SkillStructured.model_validate(skill) for skill in new_skills]

    def update_image_and_description(
        self,
        monster_db_id: int,
        image_url: str,
        description_visuelle: str,
    ) -> None:
        """
        Met à jour l'image_url et la description_visuelle d'un monstre.
        Utilisée lors de la sélection d'une image par défaut.

        Args:
            monster_db_id: ID de base de données du monstre
            image_url: Nouvelle URL de l'image
            description_visuelle: Nouvelle description visuelle

        Raises:
            MonsterModificationError: Si le monstre n'existe pas
        """
        # Récupérer le monstre directement par son ID de base de données
        monster = self.db.query(Monster).filter(Monster.id == monster_db_id).first()
        if not monster:
            raise MonsterModificationError(
                f"Monster with DB ID {monster_db_id} not found"
            )

        # Mettre à jour les champs
        monster.image_url = image_url  # type: ignore
        monster.description_visuelle = description_visuelle  # type: ignore
        monster.updated_at = datetime.now(timezone.utc)  # type: ignore

        self.db.commit()
        logger.info(
            f"Updated image_url and description_visuelle for monster ID {monster_db_id}"
        )
