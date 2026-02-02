from .config import ValidationRules

# Import centralized validation rules
VALID_STATS = "|".join(ValidationRules.VALID_STATS)
VALID_ELEMENTS = "|".join(ValidationRules.VALID_ELEMENTS)
VALID_RANKS = "|".join(ValidationRules.VALID_RANKS)

# Global Balance Configuration
MIN_HP = ValidationRules.MIN_HP
MAX_HP = ValidationRules.MAX_HP
MIN_ATK = ValidationRules.MIN_ATK
MAX_ATK = ValidationRules.MAX_ATK
MIN_DEF = ValidationRules.MIN_DEF
MAX_DEF = ValidationRules.MAX_DEF
MIN_VIT = ValidationRules.MIN_VIT
MAX_VIT = ValidationRules.MAX_VIT

MIN_DAMAGE = ValidationRules.MIN_DAMAGE
MAX_DAMAGE = ValidationRules.MAX_DAMAGE
MIN_PERCENT = ValidationRules.MIN_PERCENT
MAX_PERCENT = ValidationRules.MAX_PERCENT
MIN_COOLDOWN = ValidationRules.MIN_COOLDOWN
MAX_COOLDOWN = ValidationRules.MAX_COOLDOWN
LVL_MAX = ValidationRules.LVL_MAX


class GatchaPrompts:
    SINGLE_PROFILE = (
        """
    Generate a creative monster profile for a gacha game based on this user prompt: "{user_prompt}".
    
    The number of skills must be between 4 and 6.
    At least one of the skills must be an ultimate skill with a higher rank.
    The ranks must be restricted to: """
        + VALID_RANKS
        + """.
    The ranks must be balanced with the stats.

    Output MUST be valid JSON with the following EXACT structure :
    {{
        "nom": "string (Creative Name)",
        "element": "string """
        + VALID_ELEMENTS
        + """",
        "rang": "string """
        + VALID_RANKS
        + """ - infer from prompt if possible)",
        "stats": {{
            "hp": float ("""
        + f"{MIN_HP}-{MAX_HP}"
        + """),
            "atk": float ("""
        + f"{MIN_ATK}-{MAX_ATK}"
        + """),
            "def": float ("""
        + f"{MIN_DEF}-{MAX_DEF}"
        + """),
            "vit": float ("""
        + f"{MIN_VIT}-{MAX_VIT}"
        + """)
        }},
        "description_carte": "string (Description visible to player, < 200 chars)",
        "description_visuelle": "string (Detailed visual description for art generator: style, colors, appearance, background)",
        "skills": [
            {{
                "name": "string (Skill Name)",
                "description": "string (Skill Description)",
                "damage": float ("""
        + f"{MIN_DAMAGE}-{MAX_DAMAGE}"
        + """),
                "ratio": {{
                    "stat": "string """
        + VALID_STATS
        + """",
                    "percent": float ("""
        + f"{MIN_PERCENT}-{MAX_PERCENT}"
        + """)
                }},
                "cooldown": float ("""
        + f"{MIN_COOLDOWN}-{MAX_COOLDOWN}"
        + """),
                "lvlMax": """
        + f"{LVL_MAX}"
        + """,
                "rank": "string (Same as monster rank usually)"
            }},
             {{
                "name": "string (Second Skill Name)",
                "description": "string",
                "damage": float ("""
        + f"{MIN_DAMAGE}-{MAX_DAMAGE}"
        + """),
                "ratio": {{
                    "stat": "string """
        + VALID_STATS
        + """",
                    "percent": float ("""
        + f"{MIN_PERCENT}-{MAX_PERCENT}"
        + """)
                }},
                "cooldown": float ("""
        + f"{MIN_COOLDOWN}-{MAX_COOLDOWN}"
        + """),
                "lvlMax": """
        + f"{LVL_MAX}"
        + """,
                "rank": "string"
            }}
        ]
    }}
    Do not include markdown code blocks. Just the JSON.
    """
    )

    BATCH_BRAINSTORM = (
        """
    Brainstorm {n} distinct monsters for a gacha game based on this theme: "{user_prompt}".
    
    The monsters must have balanced stats relative to each other.
    
    Output MUST be a valid JSON Array containing {n} objects.
    DO NOT include a "skills" field yet.
    
    Structure for each object:
    {{
        "nom": "string",
        "element": "string """
        + VALID_ELEMENTS
        + """",
        "rang": "string """
        + VALID_RANKS
        + """ - infer from concept)",
        "stats": {{
            "hp": float ("""
        + f"{MIN_HP}-{MAX_HP}"
        + """),
            "atk": float ("""
        + f"{MIN_ATK}-{MAX_ATK}"
        + """),
            "def": float ("""
        + f"{MIN_DEF}-{MAX_DEF}"
        + """),
            "vit": float ("""
        + f"{MIN_VIT}-{MAX_VIT}"
        + """)
        }},
        "description_carte": "string (<200 chars)",
        "description_visuelle": "string (Detailed visual description for art generator)"
    }}
    
    Do not include markdown code blocks. Just the JSON Array.
    """
    )

    BATCH_SKILLS = (
        """
    Here are monster profiles without skills:
    {monsters_json}
    
    Generate a list of balanced skills for each monster. 
    Return the SAME JSON list with the exact same order, but add the "skills" field to each monster.
    Each monster should have 4-6 skills. At least one skill must have a "rank" higher than the others.
    The ranks must be restricted to: """
        + VALID_RANKS
        + """.
    The ranks must be balanced with the stats.
    
    Skill Structure:
    {{
        "name": "string",
        "description": "string",
        "damage": float ("""
        + f"{MIN_DAMAGE}-{MAX_DAMAGE}"
        + """),
        "ratio": {{ "stat": "string """
        + VALID_STATS
        + """", "percent": float ("""
        + f"{MIN_PERCENT}-{MAX_PERCENT}"
        + """) }},
        "cooldown": float ("""
        + f"{MIN_COOLDOWN}-{MAX_COOLDOWN}"
        + """),
        "lvlMax": """
        + f"{LVL_MAX}"
        + """,
        "rank": "string"
    }}
    
    Output ONLY the valid JSON Array. Do not include markdown.
    """
    )

    # -- IMAGE GENERATION PROMPTS --

    # Default Style (Fantasy Art) - Optimized to avoid text/borders
    IMAGE_GENERATION = "Full body illustration of {prompt}, set in a detailed and coherent environment fitting the monster's theme. High-quality digital fantasy art, dynamic pose, cinematic lighting, sharp focus. The image must be a clean character illustration WITHOUT any text, writing, numbers, stats, UI elements, borders, card frames, or game interface overlays. Just the monster and the background scenery. Masterpiece, 4k resolution."

    # Alternative 1: Pixel Art Style
    IMAGE_GENERATION_PIXEL = "High quality pixel art sprite of {prompt}, full body. 16-bit retro game style, vibrant colors, clean and coherent background. No text, no UI, no borders, no stats overlays. Detailed pixel shading."

    # Alternative 2: Anime/Cel-Shaded Style
    IMAGE_GENERATION_ANIME = "Anime style character illustration of {prompt}. Cel-shaded, vibrant colors, clean lines, anime background. detailed character design. No text, no card borders, no stats, no interface elements. High quality, 4k."

    # Alternative 3: 3D Render/Realistic Style
    IMAGE_GENERATION_REALISTIC = "3D rendered character of {prompt}, Unreal Engine 5 style, realistic textures, volumetric lighting, photorealistic environment. No text, no game UI, no frames or borders. Cinematic shot."
