from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.api.v1.endpoints import gatcha, nano_banana
from app.core.config import get_settings
import os

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Ensure static directory exists
os.makedirs("app/static/images", exist_ok=True)
os.makedirs("app/static/jsons", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(
    gatcha.router, prefix=f"{settings.API_V1_STR}/monsters", tags=["monsters"]
)
app.include_router(
    nano_banana.router,
    prefix=f"{settings.API_V1_STR}/nano-banana",
    tags=["nano-banana"],
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
