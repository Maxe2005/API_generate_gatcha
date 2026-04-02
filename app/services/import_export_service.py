"""
Service: import_export_service

Fournit l'export et l'import des monstres sous forme d'archive zip.

Fonctions principales:
- export_monsters(uuids: list[str] | None) -> bytes (zip archive)
- import_monsters(zip_bytes: bytes) -> dict (résumé)
"""

from typing import List, Optional, Dict, Any
import io
import zipfile
import json
import logging
from pathlib import PurePosixPath

from sqlalchemy.orm import Session

from app.clients.minio_client import MinioClientWrapper
from app.core.config import get_settings
from app.repositories.monster.repository import MonsterRepository
from app.repositories.monster.state_repository import MonsterStateRepository
from app.repositories.monster.skill_repository import SkillRepository
from app.repositories.monster.update_event_repository import UpdateEventRepository
from app.repositories.monster.transition_repository import TransitionRepository
from app.repositories.monster_image_repository import MonsterImageRepository
from app.core.json_monster_config import (
    MonsterJsonAttributes,
    MonsterJsonSkillAttributes,
    MonsterJsonStatsAttributes,
)

logger = logging.getLogger(__name__)


class ImportExportService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.minio = MinioClientWrapper()
        self.monster_repo = MonsterRepository(db)
        self.state_repo = MonsterStateRepository(db)
        self.skill_repo = SkillRepository(db)
        self.update_repo = UpdateEventRepository(db)
        self.transition_repo = TransitionRepository(db)
        self.image_repo = MonsterImageRepository(db)

    def _reconstruct_monster_json(self, monster_uuid: str) -> Optional[Dict[str, Any]]:
        monster = self.monster_repo.get_by_uuid(monster_uuid)
        if not monster:
            return None

        skills = []
        for s in monster.skills:
            skills.append(
                {
                    MonsterJsonSkillAttributes.NAME.value: s.name,
                    MonsterJsonSkillAttributes.DESCRIPTION.value: s.description,
                    MonsterJsonSkillAttributes.DAMAGE.value: s.damage,
                    MonsterJsonSkillAttributes.COOLDOWN.value: s.cooldown,
                    MonsterJsonSkillAttributes.LVL_MAX.value: s.lvl_max,
                    MonsterJsonSkillAttributes.RANK.value: s.rank,
                    MonsterJsonSkillAttributes.RATIO.value: {
                        "stat": s.ratio_stat,
                        "percent": s.ratio_percent,
                    },
                }
            )

        monster_json = {
            MonsterJsonAttributes.NAME.value: monster.name,
            MonsterJsonAttributes.ELEMENT.value: monster.element.value
            if monster.element.value
            else None,
            MonsterJsonAttributes.RANK.value: monster.rank.value
            if monster.rank.value
            else None,
            MonsterJsonAttributes.STATS.value: {
                MonsterJsonStatsAttributes.HP.value: monster.hp,
                MonsterJsonStatsAttributes.ATK.value: monster.atk,
                MonsterJsonStatsAttributes.DEF.value: monster.def_,
                MonsterJsonStatsAttributes.VIT.value: monster.vit,
            },
            MonsterJsonAttributes.DESCRIPTION_CARD.value: monster.description_carte,
            MonsterJsonAttributes.DESCRIPTION_VISUAL.value: monster.description_visuelle,
            MonsterJsonAttributes.IMAGE_URL.value: monster.image_url,
            MonsterJsonAttributes.SKILLS.value: skills,
        }

        return monster_json

    def export_monsters(self, uuids: Optional[List[str]] = None) -> bytes:
        """
        Exporte les monstres donnés (par uuid). Si uuids is None -> exporte tous.
        Retourne les bytes d'une archive zip.
        """
        # Récupérer la liste des monsters à exporter
        ids_to_export: List[str] = []
        if uuids:
            ids_to_export = uuids
        else:
            metas = self.state_repo.list_all(limit=10, offset=0)
            ids_to_export = [m.monster_id for m in metas]

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for mid in ids_to_export:
                try:
                    m = self.state_repo.get(mid)
                    if not m:
                        logger.warning(f"Monster state not found for {mid}, skipping")
                        continue

                    # monster.json : préférer monster_data stocké sinon reconstruire
                    monster_data = m.monster_data
                    if monster_data is None:
                        monster_data = self._reconstruct_monster_json(mid)

                    zf.writestr(
                        f"{mid}/monster.json",
                        json.dumps(monster_data or {}, ensure_ascii=False),
                    )

                    # meta.json : sérialiser metadata + update events
                    meta_dict = m.metadata.dict()
                    # ajouter update events explicitement
                    events = self.update_repo.get_by_monster_id(mid)
                    meta_dict["update_events"] = [e.__dict__ for e in events]
                    zf.writestr(
                        f"{mid}/meta.json",
                        json.dumps(meta_dict, default=str, ensure_ascii=False),
                    )

                    # images
                    images_list = []
                    # si monstre structuré existe
                    monster_struct = self.monster_repo.get_by_uuid(mid)
                    if monster_struct:
                        imgs = self.image_repo.get_images_by_monster_id(
                            monster_struct.id # type: ignore
                        )
                        for im in imgs:
                            id = int(im.id) if im.id else None # type: ignore
                            raw_image_key = str(im.raw_image_key) if im.raw_image_key else None # type: ignore
                            image_url = str(im.image_url) if im.image_url else None # type: ignore
                            image_name = str(im.image_name) if im.image_name else None # type: ignore
                            prompt = str(im.prompt) if im.prompt else None # type: ignore
                            images_list.append(
                                {
                                    "id": id,
                                    "image_name": image_name,
                                    "image_url": image_url,
                                    "prompt": prompt,
                                    "is_default": bool(im.is_default),
                                    "raw_image_key": raw_image_key,
                                }
                            )
                            # try download raw image from minio
                            raw_key = None
                            try:
                                # derive raw key: often raw key is like "monsters/<stem>.png"
                                if raw_image_key:
                                    raw_key = raw_image_key
                                elif image_url:
                                    # fallback: derive from image_url
                                    name = PurePosixPath(image_url).name
                                    stem = PurePosixPath(name).stem
                                    raw_key = f"monsters/{stem}.png"
                                else:
                                    logger.warning(
                                        f"Could not derive raw key for image {im.id}"
                                    )
                                    continue

                                obj = self.minio.client.get_object(
                                    self.settings.MINIO_BUCKET_RAW, raw_key
                                )
                                data = obj.read()
                                obj.close()
                                obj.release_conn()
                                zf.writestr(
                                    f"{mid}/images/{PurePosixPath(raw_key).name}", data
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Could not fetch raw image {mid} {raw_key if raw_key else 'unknown'}: {e}"
                                )

                    zf.writestr(
                        f"{mid}/images/images.json",
                        json.dumps(images_list, ensure_ascii=False),
                    )

                except Exception as e:
                    logger.exception(f"Error exporting monster {mid}: {e}")

        buf.seek(0)
        return buf.getvalue()

    async def import_monsters(self, zip_bytes: bytes) -> Dict[str, Any]:
        """
        Importe les monstres depuis une archive zip (format attendu décrit dans l'API).
        Retourne un résumé sommaire.
        """
        summary: Dict[str, Any] = {"imported": [], "skipped": [], "errors": []}
        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf, mode="r") as zf:
            # parcourir les racines (un dossier par monster)
            roots = set(p.split("/")[0] for p in zf.namelist() if p.strip())
            monsters_to_transmit: List = []
            for root in roots:
                try:
                    # lire monster.json
                    try:
                        monster_raw = zf.read(f"{root}/monster.json")
                        monster_data = json.loads(monster_raw)
                    except KeyError:
                        monster_data = None

                    # lire meta.json
                    meta = None
                    try:
                        meta_raw = zf.read(f"{root}/meta.json")
                        meta = json.loads(meta_raw)
                    except KeyError:
                        meta = None

                    # Save state
                    skip_root = False
                    if meta and "monster_id" in meta:
                        # Build minimal MonsterMetadata-like dict
                        from app.schemas.metadata import MonsterMetadata

                        meta_obj = MonsterMetadata(
                            **{
                                k: meta[k]
                                for k in meta.keys()
                                if k in MonsterMetadata.__fields__
                            }
                        )
                        # Si le monstre structuré existe déjà en base, on le rejette proprement
                        try:
                            existing = self.monster_repo.get_by_uuid(meta_obj.monster_id)
                            if existing:
                                summary.setdefault("skipped", []).append(
                                    {"root": root, "reason": "monster_exists"}
                                )
                                skip_root = True
                            else:
                                self.state_repo.save(meta_obj, monster_data)
                                summary["imported"].append(root)
                        except Exception as e:
                            logger.warning(f"Error checking existing monster for {meta_obj.monster_id}: {e}")
                            # attempt to save state if check failed
                            self.state_repo.save(meta_obj, monster_data)
                            summary["imported"].append(root)

                        # Si le monstre est en TRANSMITTED, préparer la transmission en batch
                        from app.core.constants import MonsterStateEnum

                        try:
                            if meta_obj.state == MonsterStateEnum.TRANSMITTED:
                                # récupérer DB MonsterState
                                db_state = self.state_repo.get_db_object(meta_obj.monster_id)
                                if db_state and (not db_state.monster) and monster_data:
                                    # créer le monstre structuré à partir du JSON
                                    try:
                                        self.transition_repo.create_structured_monster_from_json(db_state, monster_data)
                                    except Exception as e:
                                        logger.warning(f"Could not create structured monster for {meta_obj.monster_id}: {e}")

                                # récupérer le structuré et l'ajouter à la liste
                                monster_struct = self.monster_repo.get_by_uuid(meta_obj.monster_id)
                                if monster_struct:
                                    monsters_to_transmit.append(monster_struct)
                        except Exception as e:
                            logger.warning(f"Error while preparing transmission for {meta_obj.monster_id}: {e}")
                    else:
                        summary["skipped"].append(root)

                    # images
                    try:
                        imgs_raw = zf.read(f"{root}/images/images.json")
                        imgs = json.loads(imgs_raw)
                    except KeyError:
                        imgs = []

                    # upload images present in zip (skip if monster was rejected)
                    if skip_root:
                        # skip image uploads for this root
                        continue

                    # upload images present in zip
                    for name in zf.namelist():
                        if not name.startswith(f"{root}/images/"):
                            continue
                        rel = name[len(f"{root}/images/") :]
                        if rel in ("", "images.json"):
                            continue
                        try:
                            data = zf.read(name)
                            # upload raw
                            stem = PurePosixPath(rel).stem
                            raw_key = f"monsters/{stem}.png"
                            # n'uploadez que si l'objet raw n'existe pas déjà
                            try:
                                if not self.minio.object_exists(self.settings.MINIO_BUCKET_RAW, raw_key):
                                    self.minio.upload_image(
                                        self.settings.MINIO_BUCKET_RAW,
                                        raw_key,
                                        data,
                                        content_type="image/png",
                                    )
                                else:
                                    logger.info(f"Raw image already exists, skipping upload: {raw_key}")
                            except Exception:
                                # si check échoue, fallback: tenter l'upload
                                self.minio.upload_image(
                                    self.settings.MINIO_BUCKET_RAW,
                                    raw_key,
                                    data,
                                    content_type="image/png",
                                )
                            # create webp and upload to assets
                            try:
                                from app.utils.image_utils import optimize_for_web

                                webp_io = optimize_for_web(data)
                                webp_name = f"{stem}.webp"
                                # n'uploadez que si webp n'existe pas déjà
                                try:
                                    if not self.minio.object_exists(self.settings.MINIO_BUCKET_ASSETS, webp_name):
                                        self.minio.upload_image(
                                            self.settings.MINIO_BUCKET_ASSETS,
                                            webp_name,
                                            webp_io.getvalue(),
                                            content_type="image/webp",
                                        )
                                    else:
                                        logger.info(f"Webp already exists, skipping upload: {webp_name}")
                                except Exception:
                                    # fallback: tenter l'upload
                                    self.minio.upload_image(
                                        self.settings.MINIO_BUCKET_ASSETS,
                                        webp_name,
                                        webp_io.getvalue(),
                                        content_type="image/webp",
                                    )
                            except Exception:
                                logger.warning(f"Could not create webp for {rel}")

                        except Exception as e:
                            logger.warning(f"Failed to import image {name}: {e}")

                except Exception as e:
                    logger.exception(f"Error importing root {root}: {e}")
                    summary["errors"].append({"root": root, "error": str(e)})

            # Après avoir traité tous les roots, transmettre en batch si besoin
            if monsters_to_transmit:
                try:
                    from app.clients.invocation_api import InvocationApiClient

                    client = InvocationApiClient(base_url=self.settings.INVOCATION_API_URL)
                    resp = await client.create_monsters_batch(monsters_to_transmit)
                    summary["batch_response"] = resp
                except Exception as e:
                    logger.exception(f"Failed to transmit batch after import: {e}")
                    summary.setdefault("errors", []).append({"batch_transmit": str(e)})

        return summary
