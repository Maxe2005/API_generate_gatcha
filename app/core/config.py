from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Set, Dict, Tuple


class ValidationRules:
    """Centralized validation rules for monsters"""

    # Enum constraints
    VALID_STATS: Set[str] = {"ATK", "DEF", "HP", "VIT"}
    VALID_ELEMENTS: Set[str] = {"FIRE", "WATER", "WIND", "EARTH", "LIGHT", "DARKNESS"}
    VALID_RANKS: Set[str] = {"COMMON", "RARE", "EPIC", "LEGENDARY"}

     # Individual stat boundaries
    MIN_HP: int = 50
    MAX_HP: int = 1000
    MIN_ATK: int = 10
    MAX_ATK: int = 200
    MIN_DEF: int = 10
    MAX_DEF: int = 200
    MIN_VIT: int = 10
    MAX_VIT: int = 150

    # Damage and skill boundaries
    MIN_DAMAGE: int = 0
    MAX_DAMAGE: int = 500
    MIN_PERCENT: float = 0.1
    MAX_PERCENT: float = 2.0
    MIN_COOLDOWN: int = 0
    MAX_COOLDOWN: int = 5

    # Stat limits
    STAT_LIMITS: Dict[str, Tuple[int, int]] = {
        "hp": (MIN_HP, MAX_HP),
        "atk": (MIN_ATK, MAX_ATK),
        "def": (MIN_DEF, MAX_DEF),
        "vit": (MIN_VIT, MAX_VIT),
    }

    # Skill limits
    SKILL_LIMITS: Dict[str, Tuple[int , int] | Tuple[float , float]] = {
        "damage": (MIN_DAMAGE, MAX_DAMAGE),
        "percent": (MIN_PERCENT, MAX_PERCENT),
        "cooldown": (MIN_COOLDOWN, MAX_COOLDOWN),
    }

    # Other limits
    LVL_MAX: int = 5
    MAX_CARD_DESCRIPTION_LENGTH: int = 200


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Gatcha Monster Generator API"

    # External API Keys (Loaded from environment variables)
    GEMINI_API_KEY: str = ""
    BANANA_API_KEY: str = ""

    # PostgreSQL
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "gatcha_user"
    POSTGRES_PASSWORD: str = "gatcha_password"
    POSTGRES_DB: str = "gatcha_db"

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
