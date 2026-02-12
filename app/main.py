from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from app.api.v1.endpoints import gatcha, nano_banana, admin, transmission, images
from app.core.config import get_settings
from app.models.base import init_db
from app.clients.minio_client import MinioClientWrapper
import os
import logging

settings = get_settings()

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()],
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
        minio_client = MinioClientWrapper()
        uploaded = minio_client.ensure_default_images()
        if uploaded:
            logger.info(f"MinIO seeded with {uploaded} default images")
    except Exception as e:
        logger.error(f"Failed to seed MinIO with default images: {e}")

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
os.makedirs("app/static/jsons", exist_ok=True)
os.makedirs(settings.DEFECTIVE_JSONS_DIR, exist_ok=True)
os.makedirs(settings.METADATA_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(
    gatcha.router, prefix=f"{settings.API_V1_STR}/monsters", tags=["monsters"]
)
app.include_router(
    nano_banana.router,
    prefix=f"{settings.API_V1_STR}/nano-banana",
    tags=["nano-banana"],
)
app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_STR}/admin",
    tags=["admin"],
)
app.include_router(
    transmission.router,
    prefix=f"{settings.API_V1_STR}/transmission",
    tags=["transmission"],
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
