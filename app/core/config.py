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

    # Modèle Gemini utilisé pour la génération de texte/stats (GeminiClient).
    # Distinct de GeminiModelEnum (app/core/constants.py), qui liste les modèles
    # *image*. "gemini-2.0-flash" (l'ancien défaut en dur) n'existe plus côté API
    # ("model ... is no longer available") — gemini-flash-latest est le modèle
    # texte courant vérifié fonctionnel avec ce projet au moment de l'écriture.
    GEMINI_TEXT_MODEL: str = "gemini-flash-latest"

    # PostgreSQL
    # Défauts alignés sur la stack racine (GatchaApi/docker-compose.yaml) :
    # port interne 5432 (5434 n'est que le port exposé côté hôte)
    POSTGRES_HOST: str = "postgres-generate-gatcha"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "gatcha_user"
    POSTGRES_PASSWORD: str = "gatcha_password"
    POSTGRES_DB: str = "gatcha_db"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "password123"
    MINIO_BUCKET_RAW: str = "raw-assets"
    MINIO_BUCKET_ASSETS: str = "game-assets"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"

    # API Invocation
    INVOCATION_API_URL: str = "http://api-invocations:8080"
    INVOCATION_API_TIMEOUT: int = 30
    INVOCATION_API_MAX_RETRIES: int = 3
    INVOCATION_API_RETRY_DELAY: int = 2

    # API Authentification (vérification du token porteur — mêmes credentials que
    # l'AuthInterceptor des services Java : POST /user/verify-token)
    AUTH_API_URL: str = "http://api-authentification:8080"
    AUTH_API_TIMEOUT: int = 5

    # Clé interne optionnelle pour les appels machine-à-machine (scripts, CI, health-checks)
    # qui ne portent pas de token utilisateur. Vide = mécanisme désactivé.
    INTERNAL_API_KEY: str = ""

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Chemins
    MONSTERS_BASE_PATH: str = "app/static"
    METADATA_DIR: str = "app/static/metadata"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


@lru_cache
def get_settings():
    return Settings()
