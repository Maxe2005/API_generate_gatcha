"""
Module: base

Description:
Configuration de base pour SQLAlchemy et la connexion à PostgreSQL
"""

from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from alembic import command
from alembic.config import Config as AlembicConfig

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Construction de l'URL de connexion PostgreSQL
DATABASE_URL = (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

# Création du moteur SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Vérifie les connexions avant de les utiliser
    echo=False,  # Mettre à True pour voir les requêtes SQL
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Générateur de session de base de données pour les dépendances FastAPI.

    Usage:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Racine du projet (contient alembic.ini et le dossier alembic/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def init_db() -> None:
    """
    Initialise la base de données en appliquant les migrations Alembic
    jusqu'à `head`. Alembic est le seul propriétaire du schéma : il n'y a
    plus de `Base.metadata.create_all()` en parallèle, pour éviter que deux
    chemins d'installation produisent deux schémas différents (c'est ce qui
    avait cassé monster_update_events, corrigé par la migration
    c4f8b21d9a63).

    Idempotent : `alembic upgrade head` ne fait rien si la base est déjà à
    jour. Bascule ponctuelle : si une base a été créée par l'ancien
    `create_all()` (tables présentes mais pas de table `alembic_version`),
    on ne rejoue pas les migrations depuis la baseline — ça échouerait sur
    des relations déjà existantes — on `stamp` head à la place (les modèles
    et les révisions Alembic sont supposés en phase, cf. CLAUDE.md).

    Appelé au démarrage de l'application et par `scripts/seed_fixtures.py`.
    """
    try:
        # Import tous les modèles pour s'assurer qu'ils sont enregistrés
        from app.models import monster  # noqa: F401

        alembic_cfg = AlembicConfig(str(_PROJECT_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(_PROJECT_ROOT / "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        # Ne pas laisser alembic/env.py reconfigurer le logging global du
        # process (voir le commentaire dans env.py) : cet appel est fait à
        # chaud par une application qui a déjà configuré son propre logging.
        alembic_cfg.attributes["configure_logger"] = False

        existing_tables = set(inspect(engine).get_table_names())
        if existing_tables and "alembic_version" not in existing_tables:
            logger.warning(
                "Base créée par un ancien create_all() (aucune table "
                "alembic_version, tables déjà présentes) : stamp 'head' "
                "au lieu de rejouer les migrations depuis la baseline."
            )
            command.stamp(alembic_cfg, "head")
        else:
            command.upgrade(alembic_cfg, "head")
        logger.info("Database migrated to head successfully")
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")
        raise
