from enum import Enum

NB_SKILLS_MIN = 4
NB_SKILLS_MAX = 6

class MonsterJsonAttributes(Enum):
    NAME = "nom"
    ELEMENT = "element"
    RANK = "rang"
    STATS = "stats"
    DESCRIPTION_CARD = "description_carte"
    DESCRIPTION_VISUAL = "description_visuelle"
    SKILLS = "skills"
    IMAGE_URL = "ImageUrl"

class MonsterJsonStatsAttributes(Enum):
    HP = "hp"
    ATK = "atk"
    DEF = "def"
    VIT = "vit"

class MonsterJsonSkillAttributes(Enum):
    NAME = "name"
    DESCRIPTION = "description"
    DAMAGE = "damage"
    COOLDOWN = "cooldown"
    LVL_MAX = "lvlMax"
    RANK = "rank"
    RATIO = "ratio"

class MonsterJsonSkillRatioAttributes(Enum):
    STAT = "stat"
    PERCENT = "percent"

# Utilisation :
# MonsterJsonAttributes.NAME.value
