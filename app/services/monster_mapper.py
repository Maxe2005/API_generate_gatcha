"""
Module: monster_mapper

Description:
Fonctions utilitaires pour mapper les objets de données de monstre des schémas de sortie.
"""

from typing import Any, Dict
from app.core.constants import ElementEnum, RankEnum
from app.core.json_monster_config import MonsterJsonAttributes
from app.models.monster.monster import Monster
from app.models.monster.skill import Skill
from app.schemas.admin import MonsterSummary
from app.schemas.json_monster import MonsterBase, Skill as SkillBase
from app.schemas.metadata import MonsterMetadata, MonsterWithMetadata
from app.schemas.monster import MonsterStructured
from app.schemas.skill import SkillStructured


def map_monster_to_summary(metadata: MonsterMetadata, monster: Monster):
    """
    Mappe un monstre structuré (issu de la base relationnelle) et ses métadonnées vers un MonsterSummary.
    """
    return MonsterSummary(
        monster_id=monster.monster_uuid,  # type: ignore
        name=monster.nom,  # type: ignore
        element=monster.element,  # type: ignore
        rank=monster.rang,  # type: ignore
        state=metadata.state,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
        is_valid=metadata.is_valid,
        review_notes=metadata.review_notes,
    )


def map_monster_metadata_to_summary(metadata: MonsterMetadata, monster: MonsterWithMetadata):
    """
    Mappe un monstre issu du json brut et ses métadonnées vers un MonsterSummary.
    """
    if not monster.monster_data:
        return MonsterSummary(
            monster_id=metadata.monster_id,
            name="Unknown",
            element=ElementEnum.UNKNOWN,
            rank=RankEnum.UNKNOWN,
            state=metadata.state,
            created_at=metadata.created_at,
            updated_at=metadata.updated_at,
            is_valid=metadata.is_valid,
            review_notes=metadata.review_notes,
        )
    return MonsterSummary(
        monster_id=metadata.monster_id,
        name=monster.monster_data.get(MonsterJsonAttributes.NAME.value, "Unknown"),
        element=monster.monster_data.get(MonsterJsonAttributes.ELEMENT.value, ElementEnum.UNKNOWN.value),
        rank=monster.monster_data.get(MonsterJsonAttributes.RANK.value, RankEnum.UNKNOWN.value),
        state=metadata.state,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
        is_valid=metadata.is_valid,
        review_notes=metadata.review_notes,
    )


def map_global_structured_monster(monster: Monster) -> MonsterStructured:
    skills = [map_structured_skill(s) for s in monster.skills]  # type: ignore
    return MonsterStructured(
        monster_uuid=monster.monster_uuid,  # type: ignore
        nom=monster.nom,  # type: ignore
        element=monster.element,  # type: ignore
        rang=monster.rang,  # type: ignore
        description_carte=monster.description_carte,  # type: ignore
        description_visuelle=monster.description_visuelle,  # type: ignore*
        skills=skills,
    )

def map_structured_skill(skill_db: Skill) -> SkillStructured:
    return SkillStructured(
        skill_id=skill_db.id,  # type: ignore
        name=skill_db.name,  # type: ignore
        description=skill_db.description,  # type: ignore
        damage=skill_db.damage,  # type: ignore
        cooldown=skill_db.cooldown,  # type: ignore
        lvl_max=skill_db.lvl_max,  # type: ignore
        rank=skill_db.rank,  # type: ignore
        ratio_stat=skill_db.ratio_stat,  # type: ignore
        ratio_percent=skill_db.ratio_percent,  # type: ignore
    )

def map_monster_to_json(monster: Monster) -> MonsterBase :
    return MonsterBase(
        nom=monster.nom,  # type: ignore
        element=monster.element,  # type: ignore
        rang=monster.rang,  # type: ignore
        stats={
            "hp": monster.hp,  # type: ignore
            "atk": monster.atk,  # type: ignore
            "def": monster.def_,  # type: ignore
            "vit": monster.vit,  # type: ignore
        },
        description_carte=monster.description_carte,  # type: ignore
        description_visuelle=monster.description_visuelle,  # type: ignore
        skills=[
            SkillBase(
                name=s.name,  # type: ignore
                description=s.description,  # type: ignore
                damage=s.damage,  # type: ignore
                cooldown=s.cooldown,  # type: ignore
                lvlMax=s.lvl_max,  # type: ignore
                rank=s.rank,  # type: ignore
                ratio={
                    "stat": s.ratio_stat,  # type: ignore
                    "percent": s.ratio_percent,  # type: ignore
                },
            )
            for s in monster.skills  # type: ignore
        ],
        ImageUrl=monster.image_url,  # type: ignore
    )

def map_json_monster(monster_json: MonsterBase) -> Dict[str, Any]:
    return {
        "nom": monster_json.nom,
        "element": monster_json.element,
        "rang": monster_json.rang,
        "hp": monster_json.stats.hp,
        "atk": monster_json.stats.atk,
        "def": monster_json.stats.def_,
        "vit": monster_json.stats.vit,
        "description_carte": monster_json.description_carte,
        "description_visuelle": monster_json.description_visuelle,
        "skills": [
            {
                "name": s.name,
                "description": s.description,
                "damage": s.damage,
                "cooldown": s.cooldown,
                "lvl_max": s.lvlMax,
                "rank": s.rank,
                "ratio_stat": s.ratio.stat,
                "ratio_percent": s.ratio.percent,
            }
            for s in monster_json.skills
        ],
        "image_url": monster_json.ImageUrl,
    }
    
