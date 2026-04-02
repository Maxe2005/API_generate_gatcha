"""
Endpoints pour l'import/export des monstres.

Routes:
- POST /export : export zip des monstres (optionnel body {"uuids": [...]})
- POST /import : upload zip pour import
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import logging

from app.models.base import get_db
from app.services.import_export_service import ImportExportService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_import_export_service(db: Session = Depends(get_db)) -> ImportExportService:
    return ImportExportService(db)


@router.post("/monsters/export")
async def export_monsters(
    request: dict = None,
    service: ImportExportService = Depends(get_import_export_service),
):
    """Export des monstres. Body optionnel: {"uuids": ["uuid1", ...]}"""
    try:
        uuids = None
        if request and isinstance(request, dict):
            uuids = request.get("uuids")

        data = service.export_monsters(uuids)
        buf = io.BytesIO(data)
        headers = {"Content-Disposition": "attachment; filename=monsters_export.zip"}
        return StreamingResponse(buf, media_type="application/zip", headers=headers)
    except Exception as e:
        logger.exception("Error exporting monsters")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monsters/import")
async def import_monsters(
    file: UploadFile = File(...),
    service: ImportExportService = Depends(get_import_export_service),
):
    """Import des monstres depuis un fichier zip uploadé."""
    try:
        content = await file.read()
        result = await service.import_monsters(content)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.exception("Error importing monsters")
        raise HTTPException(status_code=500, detail=str(e))
