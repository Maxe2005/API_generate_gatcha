from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Set, Dict, Tuple


class ValidationRules:
    """Centralized validation rules for monsters"""

    # Enum constraints
    VALID_STATS: Set[str] = {"ATK", "DEF", "HP", "VIT"}
    VALID_ELEMENTS: Set[str] = {"FIRE", "WATER", "WIND", "EARTH", "LIGHT", "DARKNESS"}
    VALID_RANKS: Set[str] = {"COMMON", "RARE", "EPIC", "LEGENDARY"}

    # Stat limits
    STAT_LIMITS: Dict[str, Tuple[float, float]] = {
        "hp": (50.0, 1000.0),
        "atk": (10.0, 200.0),
        "def": (10.0, 200.0),
        "vit": (10.0, 150.0),
    }

    # Skill limits
    SKILL_LIMITS: Dict[str, Tuple[float, float]] = {
        "damage": (0.0, 500.0),
        "percent": (0.1, 2.0),
        "cooldown": (0, 5),
    }

    # Individual stat boundaries
    MIN_HP: float = 50.0
    MAX_HP: float = 1000.0
    MIN_ATK: float = 10.0
    MAX_ATK: float = 200.0
    MIN_DEF: float = 10.0
    MAX_DEF: float = 200.0
    MIN_VIT: float = 10.0
    MAX_VIT: float = 150.0

    # Damage and skill boundaries
    MIN_DAMAGE: float = 0.0
    MAX_DAMAGE: float = 500.0
    MIN_PERCENT: float = 0.1
    MAX_PERCENT: float = 2.0
    MIN_COOLDOWN: int = 0
    MAX_COOLDOWN: int = 5

    # Other limits
    LVL_MAX: float = 5.0
    MAX_CARD_DESCRIPTION_LENGTH: int = 200


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Gatcha Monster Generator API"

    # External API Keys (Loaded from environment variables)
    GEMINI_API_KEY: str = ""
    BANANA_API_KEY: str = ""

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_BUCKET_RAW: str = "raw-assets"
    MINIO_BUCKET_ASSETS: str = "game-assets"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"

    # Defective JSONs folder
    DEFECTIVE_JSONS_DIR: str = "app/static/jsons_defective"

    # API Invocation
    INVOCATION_API_URL: str = "http://localhost:8085"
    INVOCATION_API_TIMEOUT: int = 30
    INVOCATION_API_MAX_RETRIES: int = 3
    INVOCATION_API_RETRY_DELAY: int = 2

    # Transmission automatique
    AUTO_TRANSMIT_ENABLED: bool = False
    AUTO_TRANSMIT_INTERVAL_SECONDS: int = 300

    # Chemins
    MONSTERS_BASE_PATH: str = "app/static"
    METADATA_DIR: str = "app/static/metadata"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


@lru_cache
def get_settings():
    return Settings()
