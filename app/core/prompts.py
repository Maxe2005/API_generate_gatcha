import json

from app.core.constants import ElementEnum, EnumBase, RankEnum, StatEnum

from .config import ValidationRules

from .json_monster_config import (
    MonsterJsonAttributes,
    MonsterJsonSkillAttributes,
    MonsterJsonSkillRatioAttributes,
    NB_SKILLS_MAX,
    NB_SKILLS_MIN,
)


def get_enum_str(enum: type[EnumBase]) -> str:
    return "|".join(enum.values_list())


def get_stat_limits():
    return ValidationRules.STAT_LIMITS


def get_skill_limits():
    return ValidationRules.SKILL_LIMITS


def get_ratio_limits():
    return ValidationRules.RATIO_LIMITS


def monster_json_structure():
    # Structure JSON du monstre basée sur la config
    stats_limits = get_stat_limits()
    return {
        MonsterJsonAttributes.NAME.value: "string (Nom créatif)",
        MonsterJsonAttributes.ELEMENT.value: f"string ({get_enum_str(ElementEnum)})",
        MonsterJsonAttributes.RANK.value: f"string ({get_enum_str(RankEnum)})",
        MonsterJsonAttributes.STATS.value: {
            stat: f"int ({mini}-{maxi})" for stat, (mini, maxi) in stats_limits.items()
        },
        MonsterJsonAttributes.DESCRIPTION_CARD.value: f"string (Description visible joueur, <{ValidationRules.MAX_CARD_DESCRIPTION_LENGTH} chars)",
        MonsterJsonAttributes.DESCRIPTION_VISUAL.value: "string (Description visuelle détaillée pour générateur d'art)",
    }


def skill_json_structure(skill_number: int | None = None):
    # Structure JSON d'une skill basée sur la config
    skill_limits = get_skill_limits()
    ratio_limits = get_ratio_limits()
    return {
        MonsterJsonSkillAttributes.NAME.value: f"string (Nom de la compétence {skill_number if skill_number else ''})",
        MonsterJsonSkillAttributes.DESCRIPTION.value: f"string (Description de la compétence {skill_number if skill_number else ''})",
        MonsterJsonSkillAttributes.DAMAGE.value: f"int ({skill_limits[MonsterJsonSkillAttributes.DAMAGE.value][0]}-{skill_limits[MonsterJsonSkillAttributes.DAMAGE.value][1]})",
        MonsterJsonSkillAttributes.RATIO.value: {
            MonsterJsonSkillRatioAttributes.STAT.value: f"string ({get_enum_str(StatEnum)})",
            MonsterJsonSkillRatioAttributes.PERCENT.value: f"float ({ratio_limits[MonsterJsonSkillRatioAttributes.PERCENT.value][0]}-{ratio_limits[MonsterJsonSkillRatioAttributes.PERCENT.value][1]})",
        },
        MonsterJsonSkillAttributes.COOLDOWN.value: f"int ({skill_limits[MonsterJsonSkillAttributes.COOLDOWN.value][0]}-{skill_limits[MonsterJsonSkillAttributes.COOLDOWN.value][1]})",
        MonsterJsonSkillAttributes.LVL_MAX.value: f"int <= {ValidationRules.LVL_MAX}",
        MonsterJsonSkillAttributes.RANK.value: f"string ({get_enum_str(RankEnum)})",
    }


def monster_json_structure_str(with_skills: bool = True):
    if with_skills:
        # Ajouter la structure des skills à celle du monstre
        structure = monster_json_structure()
        structure[MonsterJsonAttributes.SKILLS.value] = [skill_json_structure(i + 1) for i in range(2)]
        return json.dumps(structure, indent=4, ensure_ascii=False)
    else:
        return json.dumps(monster_json_structure(), indent=4, ensure_ascii=False)


def skill_json_structure_str():
    return json.dumps(skill_json_structure(), indent=4, ensure_ascii=False)


class GatchaPrompts:
    @staticmethod
    def SINGLE_PROFILE(user_prompt: str) -> str:
        return f'''
Generate a creative monster profile for a gacha game based on this user prompt: "{user_prompt}".

The number of skills must be between {NB_SKILLS_MIN} and {NB_SKILLS_MAX}.
At least one of the skills must be an ultimate skill with a higher rank.
The ranks must be restricted to: {get_enum_str(RankEnum)}.
The ranks must be balanced with the stats.

Output MUST be valid JSON with the following EXACT structure :
{monster_json_structure_str(with_skills=True)}
Do not include markdown code blocks. Just the JSON.
'''

    @staticmethod
    def BATCH_BRAINSTORM(n: int, user_prompt: str) -> str:
        return f'''
Brainstorm {n} distinct monsters for a gacha game based on this theme: "{user_prompt}".

The monsters must have balanced stats relative to each other.

Output MUST be a valid JSON Array containing {n} objects.
DO NOT include a "skills" field yet.

Structure for each object:
{monster_json_structure_str(with_skills=False)}

Do not include markdown code blocks. Just the JSON Array.
'''

    @staticmethod
    def BATCH_SKILLS(monsters_json: str) -> str:
        return f"""
Here are monster profiles without skills:
{monsters_json}

Generate a list of balanced skills for each monster.
Return the SAME JSON list with the exact same order, but add the "skills" field to each monster.
Each monster should have {NB_SKILLS_MIN}-{NB_SKILLS_MAX} skills. At least one skill must have a "rank" higher than the others.
The ranks must be restricted to: {get_enum_str(RankEnum)}.
The ranks must be balanced with the stats.

Skill Structure:
{skill_json_structure_str()}

Output ONLY the valid JSON Array. Do not include markdown.
"""

    # -- IMAGE GENERATION PROMPTS --

    # Default Style (Fantasy Art) - Optimized to avoid text/borders
    IMAGE_GENERATION = "Full body illustration of {prompt}, set in a detailed and coherent environment fitting the monster's theme. High-quality digital fantasy art, dynamic pose, cinematic lighting, sharp focus. The image must be a clean character illustration WITHOUT any text, writing, numbers, stats, UI elements, borders, card frames, or game interface overlays. Just the monster and the background scenery. Masterpiece, 4k resolution."

    # Alternative 1: Pixel Art Style
    IMAGE_GENERATION_PIXEL = "High quality pixel art sprite of {prompt}, full body. 16-bit retro game style, vibrant colors, clean and coherent background. No text, no UI, no borders, no stats overlays. Detailed pixel shading."

    # Alternative 2: Anime/Cel-Shaded Style
    IMAGE_GENERATION_ANIME = "Anime style character illustration of {prompt}. Cel-shaded, vibrant colors, clean lines, anime background. detailed character design. No text, no card borders, no stats, no interface elements. High quality, 4k."

    # Alternative 3: 3D Render/Realistic Style
    IMAGE_GENERATION_REALISTIC = "3D rendered character of {prompt}, Unreal Engine 5 style, realistic textures, volumetric lighting, photorealistic environment. No text, no game UI, no frames or borders. Cinematic shot."

if __name__ == "__main__":
    # Test rapide des prompts
    print("=== SINGLE_PROFILE ===")
    print(GatchaPrompts.SINGLE_PROFILE("Un dragon de feu majestueux"))
    print("\n=== BATCH_BRAINSTORM ===")
    print(GatchaPrompts.BATCH_BRAINSTORM(3, "Forêt enchantée"))
    print("\n=== BATCH_SKILLS ===")
    fake_monsters_json = '[{"nom": "Test", "element": "FIRE", "rang": "RARE", "stats": {"hp": 100, "atk": 50, "def": 30, "vit": 20}, "description_carte": "Un monstre test", "description_visuelle": "Rouge et féroce"}]'
    print(GatchaPrompts.BATCH_SKILLS(fake_monsters_json))
