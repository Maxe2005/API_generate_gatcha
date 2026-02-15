"""
Module: repositories.monster

Description:
Repositories pour gérer la persistance des monstres.
Exports centralisés pour faciliter les imports.

Architecture:
- MonsterRepository : CRUD des monstres structurés
- SkillRepository : CRUD des compétences
- MonsterStateRepository : Gestion de l'état et métadonnées
- StructureRepository : Création de monstres structurés à partir de JSON
"""

from app.repositories.monster.repository import MonsterRepository
from app.repositories.monster.skill_repository import SkillRepository
from app.repositories.monster.state_repository import MonsterStateRepository
from app.repositories.monster.structure_repository import StructureRepository

__all__ = [
    "MonsterRepository",
    "SkillRepository",
    "MonsterStateRepository",
    "StructureRepository",
]
