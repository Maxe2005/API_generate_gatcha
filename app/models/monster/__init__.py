"""
Module: models.monster

Description:
Modèles SQLAlchemy pour les monstres et leurs métadonnées.
Exports centralisés pour faciliter les imports.

Architecture:
- MonsterState : État et métadonnées (anciennement "monsters")
- Monster : Données structurées pour monstres validés
- Skill : Compétences des monstres
- StateTransitionModel : Historique des transitions d'état
"""

from app.models.monster.monster import Monster
from app.models.monster.skill import Skill
from app.models.monster.state import MonsterState
from app.models.monster.transition import StateTransitionModel

__all__ = [
    "Monster",
    "Skill",
    "MonsterState",
    "StateTransitionModel",
]
