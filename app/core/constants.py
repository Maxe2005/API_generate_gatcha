"""
Module: constants

Description:
Constantes centralisées pour l'application.
Regroupe tous les enums et les valeurs de validation pour éviter les duplications.

Principes appliqués :
- DRY : Une seule source de vérité
- Modularité : Facile à étendre sans modification du code existant
- Type safety : Utilise des enums SQLAlchemy/Pydantic pour la typage
"""

import enum
from typing import Dict, Set, Tuple

from app.core.json_monster_config import MonsterJsonSkillAttributes, MonsterJsonSkillRatioAttributes, MonsterJsonStatsAttributes


# ========== ENUMS POUR SQLALCHEMY ET PYDANTIC ==========

class EnumBase(str, enum.Enum):
    """Base pour tous les enums de l'application, avec une méthode utilitaire"""

    @classmethod
    def values_set(cls) -> Set[str]:
        """Retourne un set de toutes les valeurs de l'enum"""
        return {item.value for item in cls}
    
    @classmethod
    def values_list(cls) -> list:
        """Retourne une liste de toutes les valeurs de l'enum"""
        return [item.value for item in cls]
    
    
class MonsterStateEnum(EnumBase):
    """États possibles d'un monstre dans son cycle de vie"""

    GENERATED = "GENERATED"
    DEFECTIVE = "DEFECTIVE"
    CORRECTED = "CORRECTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    TRANSMITTED = "TRANSMITTED"
    REJECTED = "REJECTED"


class TransitionActionEnum(EnumBase):
    """Actions possibles pour les transitions"""

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CORRECT = "CORRECT"
    TRANSMIT = "TRANSMIT"


class ElementEnum(EnumBase):
    """Éléments possibles pour un monstre"""

    FIRE = "FIRE"
    WATER = "WATER"
    WIND = "WIND"
    EARTH = "EARTH"
    LIGHT = "LIGHT"
    DARKNESS = "DARKNESS"


class RankEnum(EnumBase):
    """Rangs possibles pour un monstre ou une compétence"""

    COMMON = "COMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class StatEnum(EnumBase):
    """Stats possibles pour les ratios de compétences"""

    ATK = "ATK"
    DEF = "DEF"
    HP = "HP"
    VIT = "VIT"


# ========== CONSTANTES DE VALIDATION ==========


class ValidationConstants:
    """
    Constantes centralisées pour la validation des données.
    Évite les duplications et assure la cohérence entre les différents modules.
    """

    # Enums disponibles (listes)
    VALID_STATS: Set[str] = StatEnum.values_set()
    VALID_ELEMENTS: Set[str] = ElementEnum.values_set()
    VALID_RANKS: Set[str] = RankEnum.values_set()
    VALID_STATES: Set[str] = MonsterStateEnum.values_set()

    # Limites de stats individuelles
    MIN_HP: int = 50
    MAX_HP: int = 1000
    MIN_ATK: int = 10
    MAX_ATK: int = 200
    MIN_DEF: int = 10
    MAX_DEF: int = 200
    MIN_VIT: int = 10
    MAX_VIT: int = 150

    # Limites de dégâts et compétences
    MIN_DAMAGE: int = 0
    MAX_DAMAGE: int = 500
    MIN_COOLDOWN: int = 0
    MAX_COOLDOWN: int = 10

    # Limites de ratios
    MIN_PERCENT: float = 0.1
    MAX_PERCENT: float = 2.0

    # Limites diverses
    LVL_MAX: int = 100
    MAX_CARD_DESCRIPTION_LENGTH: int = 200

    # Dictionnaires pour un accès facilité
    STAT_LIMITS: Dict[str, Tuple[int, int]] = {
        MonsterJsonStatsAttributes.HP.value: (MIN_HP, MAX_HP),
        MonsterJsonStatsAttributes.ATK.value: (MIN_ATK, MAX_ATK),
        MonsterJsonStatsAttributes.DEF.value: (MIN_DEF, MAX_DEF),
        MonsterJsonStatsAttributes.VIT.value: (MIN_VIT, MAX_VIT),
    }

    SKILL_LIMITS: Dict[str, Tuple[int, int]] = {
        MonsterJsonSkillAttributes.DAMAGE.value: (MIN_DAMAGE, MAX_DAMAGE),
        MonsterJsonSkillAttributes.COOLDOWN.value: (MIN_COOLDOWN, MAX_COOLDOWN),
    }

    RATIO_LIMITS: Dict[str, Tuple[float, float]] = {
        MonsterJsonSkillRatioAttributes.PERCENT.value: (MIN_PERCENT, MAX_PERCENT),
    }

    @classmethod
    def validate_element(cls, element: str) -> bool:
        """Valide un élément"""
        return element in cls.VALID_ELEMENTS

    @classmethod
    def validate_rank(cls, rank: str) -> bool:
        """Valide un rang"""
        return rank in cls.VALID_RANKS

    @classmethod
    def validate_stat(cls, stat: str) -> bool:
        """Valide une stat"""
        return stat in cls.VALID_STATS

    @classmethod
    def validate_state(cls, state: str) -> bool:
        """Valide un état"""
        return state in cls.VALID_STATES


# ========== MESSAGES ET CONSTANTES D'APPLICATION ==========

# Messages d'erreur
ERROR_MONSTER_NOT_FOUND = "Monster not found"
ERROR_INVALID_TRANSITION = "Invalid state transition"
ERROR_TRANSMISSION_FAILED = "Failed to transmit monster to invocation API"
ERROR_VALIDATION_FAILED = "Monster validation failed"

# Messages de succès
SUCCESS_MONSTER_GENERATED = "Monster generated successfully"
SUCCESS_MONSTER_APPROVED = "Monster approved successfully"
SUCCESS_MONSTER_TRANSMITTED = "Monster transmitted successfully"

# Limites
MAX_BATCH_SIZE = 15
MAX_LIST_LIMIT = 200
DEFAULT_LIST_LIMIT = 50

# Timeouts (secondes)
DEFAULT_API_TIMEOUT = 30
HEALTH_CHECK_TIMEOUT = 5
