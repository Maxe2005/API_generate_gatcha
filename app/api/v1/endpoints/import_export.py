"""
Endpoints pour l'import/export des monstres.

Routes:
- POST /export : export zip des monstres (optionnel body {"uuids": [...]})
- POST /import : upload zip pour import
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import Field, BaseModel
from sqlalchemy.orm import Session
import logging

from app.models.base import get_db
from app.core.security import AuthContext, require_auth
from app.services.import_export_service import ImportExportService

logger = logging.getLogger(__name__)

router = APIRouter()


class ExportRequest(BaseModel):
    """Schéma d'entrée pour l'export des monstres"""

    uuids: Optional[list[str]] = Field(
        None, description="Liste des UUIDs des monstres à exporter (optionnel)"
    )


def get_import_export_service(db: Session = Depends(get_db)) -> ImportExportService:
    return ImportExportService(db)


@router.post("/monsters/export")
async def export_monsters(
    request: Optional[ExportRequest] = None,
    service: ImportExportService = Depends(get_import_export_service),
):
    """Export des monstres. Body optionnel: {"uuids": ["uuid1", ...]}"""
    try:
        uuids = request.uuids if request else None
        logger.info(f"Exporting monsters with UUIDs: {uuids}")
        data = service.export_monsters(uuids)
        logger.info(f"Exported data size: {len(data)} bytes")
        headers = {
            "Content-Disposition": "attachment; filename=monsters_export.zip",
            "Content-Length": str(len(data)),
        }
        return Response(content=data, media_type="application/zip", headers=headers)
    except Exception as e:
        logger.exception("Error exporting monsters")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monsters/import")
async def import_monsters(
    file: UploadFile = File(...),
    service: ImportExportService = Depends(get_import_export_service),
    auth: AuthContext = Depends(require_auth),
):
    """Import des monstres depuis un fichier zip uploadé."""
    try:
        content = await file.read()
        result = await service.import_monsters(content, auth_token=auth.token)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.exception("Error importing monsters")
        raise HTTPException(status_code=500, detail=str(e))
