from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Import centralized validation rules from constants
from app.core.constants import ValidationConstants


# Alias for backward compatibility
class ValidationRules(ValidationConstants):
    """Backward-compatible alias for ValidationConstants"""

    pass


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
