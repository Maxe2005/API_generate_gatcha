from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from app.api.v1.endpoints import (
    gatcha,
    nano_banana,
    admin,
    transmission,
    images,
    import_export,
)
from app.core.config import get_settings
from app.core.security import require_auth
from app.models.base import init_db
from scripts.seed_fixtures import seed_fixtures
import os
import logging
from logging.handlers import RotatingFileHandler

settings = get_settings()

# Setup logging with rotation
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            "logs/app.log",
            maxBytes=100000,  # ~100 KB (environ 1000 lignes)
            backupCount=5,  # Garde 5 fichiers archivés
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Startup
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    try:
        stats = seed_fixtures()
        if stats["created"]:
            logger.info(f"Fixtures seeded: {stats['created']} monsters created")
    except Exception as e:
        logger.error(f"Failed to seed fixtures: {e}")

    yield

    # Shutdown
    logger.info("Application shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Ensure static directories exist
os.makedirs("app/static/images", exist_ok=True)
os.makedirs(settings.METADATA_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(gatcha.router, prefix=f"{settings.API_V1_STR}/monsters", tags=["monsters"])
app.include_router(
    nano_banana.router,
    prefix=f"{settings.API_V1_STR}/nano-banana",
    tags=["nano-banana"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_STR}/admin",
    tags=["admin"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    import_export.router,
    prefix=f"{settings.API_V1_STR}/external",
    tags=["external"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    transmission.router,
    prefix=f"{settings.API_V1_STR}/transmission",
    tags=["transmission"],
    dependencies=[Depends(require_auth)],
)
app.include_router(
    images.router,
    prefix=f"{settings.API_V1_STR}/monsters",
    tags=["images"],
)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
