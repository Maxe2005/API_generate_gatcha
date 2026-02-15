"""
Module: models

Description:
Modèles de base de données SQLAlchemy pour PostgreSQL.
Architecture refactorisée :
- MonsterState : Table d'état et métadonnées
- Monster : Table structurée pour les monstres validés
- Skill : Table des compétences
"""

from app.models.monster import MonsterState, Monster, Skill, StateTransitionModel
from app.models.monster_image_model import MonsterImage
from app.models.base import Base, get_db, init_db, engine

__all__ = [
    "Base",
    "MonsterState",
    "Monster",
    "Skill",
    "StateTransitionModel",
    "MonsterImage",
    "get_db",
    "init_db",
    "engine",
]
