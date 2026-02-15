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
from typing import Set, Dict, Tuple


# ========== ENUMS POUR SQLALCHEMY ET PYDANTIC ==========


class MonsterStateEnum(str, enum.Enum):
    """États possibles d'un monstre dans son cycle de vie"""

    GENERATED = "GENERATED"
    DEFECTIVE = "DEFECTIVE"
    CORRECTED = "CORRECTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    TRANSMITTED = "TRANSMITTED"
    REJECTED = "REJECTED"


class ElementEnum(str, enum.Enum):
    """Éléments possibles pour un monstre"""

    FIRE = "FIRE"
    WATER = "WATER"
    WIND = "WIND"
    EARTH = "EARTH"
    LIGHT = "LIGHT"
    DARKNESS = "DARKNESS"


class RankEnum(str, enum.Enum):
    """Rangs possibles pour un monstre ou une compétence"""

    COMMON = "COMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class StatEnum(str, enum.Enum):
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

    # Enums disponibles (ensembles)
    VALID_STATS: Set[str] = {"ATK", "DEF", "HP", "VIT"}
    VALID_ELEMENTS: Set[str] = {"FIRE", "WATER", "WIND", "EARTH", "LIGHT", "DARKNESS"}
    VALID_RANKS: Set[str] = {"COMMON", "RARE", "EPIC", "LEGENDARY"}
    VALID_STATES: Set[str] = {
        "GENERATED",
        "DEFECTIVE",
        "CORRECTED",
        "PENDING_REVIEW",
        "APPROVED",
        "TRANSMITTED",
        "REJECTED",
    }

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
    MIN_PERCENT: float = 0.1
    MAX_PERCENT: float = 2.0
    MIN_COOLDOWN: int = 0
    MAX_COOLDOWN: int = 5

    # Limites diverses
    LVL_MAX: int = 5
    MAX_CARD_DESCRIPTION_LENGTH: int = 200

    # Dictionnaires pour un accès facilité
    STAT_LIMITS: Dict[str, Tuple[float, float]] = {
        "hp": (MIN_HP, MAX_HP),
        "atk": (MIN_ATK, MAX_ATK),
        "def": (MIN_DEF, MAX_DEF),
        "vit": (MIN_VIT, MAX_VIT),
    }

    SKILL_LIMITS: Dict[str, Tuple[float, float]] = {
        "damage": (MIN_DAMAGE, MAX_DAMAGE),
        "percent": (MIN_PERCENT, MAX_PERCENT),
        "cooldown": (MIN_COOLDOWN, MAX_COOLDOWN),
    }

    @classmethod
    def get_enum_values(cls, enum_class) -> list:
        """Retourne les valeurs d'un enum"""
        return [item.value for item in enum_class]

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
