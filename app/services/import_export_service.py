"""
Service: import_export_service

Fournit l'export et l'import des monstres sous forme d'archive zip.

Fonctions principales:
- export_monsters(uuids: list[str] | None) -> bytes (zip archive)
- import_monsters(zip_bytes: bytes) -> dict (résumé)
"""

from typing import List, Optional, Dict, Any, Tuple
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
        return {
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
            MonsterJsonAttributes.SKILLS.value: self._serialize_skills(monster),
        }

    def _serialize_skills(self, monster) -> List[Dict[str, Any]]:
        skills: List[Dict[str, Any]] = []
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
        return skills

    def export_monsters(self, uuids: Optional[List[str]] = None) -> bytes:
        """
        Exporte les monstres donnés (par uuid). Si uuids is None -> exporte tous.
        Retourne les bytes d'une archive zip.
        """
        ids = self._get_ids_to_export(uuids)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for mid in ids:
                try:
                    self._write_monster_to_zip(mid, zf)
                except Exception as e:
                    logger.exception(f"Error exporting monster {mid}: {e}")

        buf.seek(0)
        return buf.getvalue()

    def _get_ids_to_export(self, uuids: Optional[List[str]]) -> List[str]:
        if uuids:
            return uuids
        metas = self.state_repo.list_all(limit=10, offset=0)
        return [m.monster_id for m in metas]

    def _write_monster_to_zip(self, mid: str, zf: zipfile.ZipFile) -> None:
        m = self.state_repo.get(mid)
        if not m:
            logger.warning(f"Monster state not found for {mid}, skipping")
            return

        monster_data = m.monster_data or self._reconstruct_monster_json(mid)
        zf.writestr(f"{mid}/monster.json", json.dumps(monster_data or {}, ensure_ascii=False))

        meta_dict = m.metadata.dict()
        meta_dict["update_events"] = self._serialize_update_events(mid)
        zf.writestr(f"{mid}/meta.json", json.dumps(meta_dict, default=str, ensure_ascii=False))

        images_list = []
        monster_struct = self.monster_repo.get_by_uuid(mid)
        if monster_struct:
            images_list = self._collect_images_and_write(mid, monster_struct, zf)

        zf.writestr(f"{mid}/images/images.json", json.dumps(images_list, ensure_ascii=False))

    def _serialize_update_events(self, mid: str) -> List[Dict[str, Any]]:
        events = self.update_repo.get_by_monster_id(mid)
        return [e.__dict__ for e in events] # type: ignore

    def _collect_images_and_write(self, mid: str, monster_struct, zf: zipfile.ZipFile) -> List[Dict[str, Any]]:
        images_list: List[Dict[str, Any]] = []
        imgs = self.image_repo.get_images_by_monster_id(monster_struct.id)  # type: ignore
        for im in imgs:
            id_v = int(im.id) if im.id else None # type: ignore
            raw_image_key = str(im.raw_image_key) if im.raw_image_key else None # type: ignore
            image_url = str(im.image_url) if im.image_url else None # type: ignore
            image_name = str(im.image_name) if im.image_name else None # type: ignore
            prompt = str(im.prompt) if im.prompt else None # type: ignore
            images_list.append(
                {
                    "id": id_v,
                    "image_name": image_name,
                    "image_url": image_url,
                    "prompt": prompt,
                    "is_default": bool(im.is_default),
                    "raw_image_key": raw_image_key,
                }
            )

            raw_key = None
            try:
                if raw_image_key:
                    raw_key = raw_image_key
                elif image_url:
                    name = PurePosixPath(image_url).name
                    stem = PurePosixPath(name).stem
                    raw_key = f"monsters/{stem}.png"
                else:
                    logger.warning(f"Could not derive raw key for image {im.id}")
                    continue

                obj = self.minio.client.get_object(self.settings.MINIO_BUCKET_RAW, raw_key)
                data = obj.read()
                obj.close()
                obj.release_conn()
                zf.writestr(f"{mid}/images/{PurePosixPath(raw_key).name}", data)
            except Exception as e:
                logger.warning(f"Could not fetch raw image {mid} {raw_key if raw_key else 'unknown'}: {e}")

        return images_list

    async def import_monsters(self, zip_bytes: bytes) -> Dict[str, Any]:
        """
        Importe les monstres depuis une archive zip (format attendu décrit dans l'API).
        Retourne un résumé sommaire.
        """
        summary: Dict[str, Any] = {"imported": [], "skipped": [], "errors": []}
        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf, mode="r") as zf:
            roots = set(p.split("/")[0] for p in zf.namelist() if p.strip())
            monsters_to_transmit: List = []
            for root in roots:
                try:
                    monster_data = self._read_json_from_zip(zf, root, "monster.json")
                    meta = self._read_json_from_zip(zf, root, "meta.json")

                    skip_root, meta_obj = self._save_state_from_meta(meta, monster_data, root, summary)

                    imgs = self._read_json_from_zip(zf, root, "images/images.json") or []

                    if skip_root:
                        continue

                    self._upload_images_from_zip(zf, root)

                    if meta_obj:
                        append_struct = self._prepare_structured_monster_for_transmit(meta_obj, monster_data)
                        if append_struct:
                            monsters_to_transmit.append(append_struct)

                except Exception as e:
                    logger.exception(f"Error importing root {root}: {e}")
                    summary["errors"].append({"root": root, "error": str(e)})

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

    def _read_json_from_zip(self, zf: zipfile.ZipFile, root: str, name: str) -> Optional[Any]:
        try:
            raw = zf.read(f"{root}/{name}")
            return json.loads(raw)
        except KeyError:
            return None

    def _save_state_from_meta(self, meta: Optional[Dict[str, Any]], monster_data: Optional[Dict[str, Any]], root: str, summary: Dict[str, Any]) -> Tuple[bool, Optional[Any]]:
        # returns (skip_root, meta_obj)
        skip_root = False
        meta_obj = None
        if meta and "monster_id" in meta:
            from app.schemas.metadata import MonsterMetadata

            meta_obj = MonsterMetadata(
                **{k: meta[k] for k in meta.keys() if k in MonsterMetadata.__fields__}
            )
            try:
                existing = self.state_repo.get(meta_obj.monster_id)
                if existing:
                    summary.setdefault("skipped", []).append({"root": root, "reason": "monster_exists"})
                    skip_root = True
                else:
                    self.state_repo.save(meta_obj, monster_data)
                    summary["imported"].append(root)
            except Exception as e:
                logger.warning(f"Error checking existing monster for {meta_obj.monster_id}: {e}")
                self.state_repo.save(meta_obj, monster_data)
                summary["imported"].append(root)
        else:
            summary.setdefault("skipped", []).append(root)

        return skip_root, meta_obj

    def _upload_images_from_zip(self, zf: zipfile.ZipFile, root: str) -> None:
        for name in zf.namelist():
            if not name.startswith(f"{root}/images/"):
                continue
            rel = name[len(f"{root}/images/") :]
            if rel in ("", "images.json"):
                continue
            try:
                data = zf.read(name)
                stem = PurePosixPath(rel).stem
                raw_key = f"monsters/{stem}.png"
                try:
                    if not self.minio.object_exists(self.settings.MINIO_BUCKET_RAW, raw_key):
                        self.minio.upload_image(self.settings.MINIO_BUCKET_RAW, raw_key, data, content_type="image/png")
                    else:
                        logger.info(f"Raw image already exists, skipping upload: {raw_key}")
                except Exception:
                    self.minio.upload_image(self.settings.MINIO_BUCKET_RAW, raw_key, data, content_type="image/png")

                try:
                    from app.utils.image_utils import optimize_for_web

                    webp_io = optimize_for_web(data)
                    webp_name = f"{stem}.webp"
                    try:
                        if not self.minio.object_exists(self.settings.MINIO_BUCKET_ASSETS, webp_name):
                            self.minio.upload_image(self.settings.MINIO_BUCKET_ASSETS, webp_name, webp_io.getvalue(), content_type="image/webp")
                        else:
                            logger.info(f"Webp already exists, skipping upload: {webp_name}")
                    except Exception:
                        self.minio.upload_image(self.settings.MINIO_BUCKET_ASSETS, webp_name, webp_io.getvalue(), content_type="image/webp")
                except Exception:
                    logger.warning(f"Could not create webp for {rel}")

            except Exception as e:
                logger.warning(f"Failed to import image {name}: {e}")

    def _prepare_structured_monster_for_transmit(self, meta_obj, monster_data: Optional[Dict[str, Any]]):
        from app.core.constants import MonsterStateEnum

        try:
            if meta_obj.state == MonsterStateEnum.TRANSMITTED:
                db_state = self.state_repo.get_db_object(meta_obj.monster_id)
                if db_state and (not db_state.monster) and monster_data:
                    try:
                        self.transition_repo.create_structured_monster_from_json(db_state, monster_data)
                    except Exception as e:
                        logger.warning(f"Could not create structured monster for {meta_obj.monster_id}: {e}")

                monster_struct = self.monster_repo.get_by_uuid(meta_obj.monster_id)
                return monster_struct
        except Exception as e:
            logger.warning(f"Error while preparing transmission for {meta_obj.monster_id}: {e}")

        return None
