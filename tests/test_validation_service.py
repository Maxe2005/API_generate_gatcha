"""
Tests for Monster Validation Service
Demonstrates the validation system with various error scenarios
"""

import pytest
from app.services.validation_service import (
    MonsterValidationService,
    TypeValidator,
    EnumValidator,
    RangeValidator,
)
from app.core.config import ValidationRules


def make_valid_skills(count: int) -> list:
    """Build `count` minimally-valid skill dicts for tests unrelated to skills."""
    return [
        {
            "name": f"Skill {i}",
            "description": "Test skill",
            "damage": 100.0,
            "ratio": {"stat": "ATK", "percent": 1.0},
            "cooldown": 2,
            "lvlMax": 5.0,
            "rank": "RARE",
        }
        for i in range(count)
    ]


class TestTypeValidator:
    def test_valid_string(self):
        is_valid, msg = TypeValidator.validate_type("test", "string")
        assert is_valid is True
        assert msg == ""

    def test_invalid_string_type(self):
        is_valid, msg = TypeValidator.validate_type(123, "string")
        assert is_valid is False
        assert "Expected string" in msg

    def test_valid_float(self):
        is_valid, msg = TypeValidator.validate_type(10.5, "float")
        assert is_valid is True

    def test_float_accepts_int(self):
        is_valid, msg = TypeValidator.validate_type(10, "float")
        assert is_valid is True

    def test_invalid_float(self):
        is_valid, msg = TypeValidator.validate_type("string", "float")
        assert is_valid is False


class TestEnumValidator:
    def test_valid_enum(self):
        is_valid, msg = EnumValidator.validate_enum(
            "FIRE", ValidationRules.VALID_ELEMENTS, "element"
        )
        assert is_valid is True

    def test_invalid_enum(self):
        is_valid, msg = EnumValidator.validate_enum(
            "INVALID", ValidationRules.VALID_ELEMENTS, "element"
        )
        assert is_valid is False
        assert "Invalid value" in msg

    def test_enum_non_string(self):
        is_valid, msg = EnumValidator.validate_enum(
            123,
            ValidationRules.VALID_ELEMENTS,
            "element",  # type: ignore
        )
        assert is_valid is False


class TestRangeValidator:
    def test_valid_range(self):
        is_valid, msg = RangeValidator.validate_range(100.0, 50.0, 1000.0, "hp")
        assert is_valid is True

    def test_value_too_low(self):
        is_valid, msg = RangeValidator.validate_range(10.0, 50.0, 1000.0, "hp")
        assert is_valid is False
        assert "out of range" in msg

    def test_value_too_high(self):
        is_valid, msg = RangeValidator.validate_range(2000.0, 50.0, 1000.0, "hp")
        assert is_valid is False


# Full integration tests
class TestMonsterValidation:
    @pytest.fixture
    def validator(self):
        return MonsterValidationService()

    @pytest.fixture
    def valid_monster(self):
        return {
            "name": "Dragon",
            "element": "FIRE",
            "rank": "RARE",
            "stats": {
                "hp": 500.0,
                "atk": 100.0,
                "def": 80.0,
                "vit": 50.0,
            },
            "description_carte": "A mighty fire dragon.",
            "description_visuelle": "A large dragon breathing flames.",
            "skills": make_valid_skills(4),
        }

    def test_valid_monster(self, validator, valid_monster):
        result = validator.validate(valid_monster)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_missing_field(self, validator, valid_monster):
        del valid_monster["element"]
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any(e.error_type == "missing_field" for e in result.errors)

    def test_invalid_type(self, validator, valid_monster):
        valid_monster["stats"]["hp"] = "invalid"
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any(e.error_type == "type_mismatch" for e in result.errors)

    def test_invalid_enum_element(self, validator, valid_monster):
        valid_monster["element"] = "INVALID"
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any(e.field == "element" for e in result.errors)

    def test_value_out_of_range_hp(self, validator, valid_monster):
        valid_monster["stats"]["hp"] = 2000.0  # Max is 1000
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any(e.field == "stats.hp" for e in result.errors)

    def test_skill_damage_out_of_range(self, validator, valid_monster):
        valid_monster["skills"][0]["damage"] = 600.0  # Max is 500
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any("damage" in e.field for e in result.errors)

    def test_description_too_long(self, validator, valid_monster):
        valid_monster["description_carte"] = "x" * 300  # Max is 200
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any(e.field == "description_carte" for e in result.errors)

    def test_multiple_errors(self, validator, valid_monster):
        valid_monster["element"] = "INVALID"
        valid_monster["stats"]["hp"] = 10.0  # Too low
        valid_monster["rank"] = "SUPER_RARE"
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert len(result.errors) >= 3

    def test_error_summary(self, validator, valid_monster):
        valid_monster["element"] = "INVALID"
        result = validator.validate(valid_monster)
        summary = result.get_error_summary()
        assert "Validation failed" in summary
        assert "element" in summary

    def test_validation_result_to_dict(self, validator, valid_monster):
        valid_monster["element"] = "INVALID"
        result = validator.validate(valid_monster)
        result_dict = result.to_dict()
        assert "is_valid" in result_dict
        assert "error_count" in result_dict
        assert "errors" in result_dict
        assert result_dict["error_count"] > 0

    def test_too_few_skills_is_invalid(self, validator, valid_monster):
        # NB_SKILLS_MIN=4 (app/core/json_monster_config.py) : les prompts
        # demandent 4 à 6 compétences, mais rien ne l'imposait avant ce test.
        valid_monster["skills"] = make_valid_skills(3)
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any(e.field == "skills" for e in result.errors)

    def test_too_many_skills_is_invalid(self, validator, valid_monster):
        valid_monster["skills"] = make_valid_skills(7)  # NB_SKILLS_MAX=6
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any(e.field == "skills" for e in result.errors)

    def test_skill_count_within_bounds_is_valid(self, validator, valid_monster):
        for count in (4, 5, 6):
            valid_monster["skills"] = make_valid_skills(count)
            result = validator.validate(valid_monster)
            assert result.is_valid is True, f"Failed for {count} skills: {result.errors}"

    def test_skill_lvl_max_out_of_range(self, validator, valid_monster):
        # LVL_MAX=20 (app/core/constants.py) : le contenu réel utilise 5,
        # occasionnellement 10 — 87 est clairement une valeur aberrante.
        valid_monster["skills"][0]["lvlMax"] = 87.0
        result = validator.validate(valid_monster)
        assert result.is_valid is False
        assert any("lvlMax" in e.field for e in result.errors)

    def test_skill_lvl_max_within_range_is_valid(self, validator, valid_monster):
        valid_monster["skills"][0]["lvlMax"] = 20.0
        result = validator.validate(valid_monster)
        assert result.is_valid is True


# Example usage demonstrations
class TestValidationExamples:
    def test_all_stats_constraints(self):
        """Demonstrate all stat constraints"""
        validator = MonsterValidationService()

        test_cases = [
            # (stat_name, value, should_be_valid)
            ("hp", 50.0, True),  # Min
            ("hp", 1000.0, True),  # Max
            ("hp", 49.0, False),  # Below min
            ("hp", 1001.0, False),  # Above max
            ("atk", 10.0, True),  # Min
            ("atk", 200.0, True),  # Max
            ("def", 10.0, True),
            ("vit", 150.0, True),  # Max
            ("vit", 151.0, False),  # Above max
        ]

        for stat_name, value, should_be_valid in test_cases:
            monster = {
                "name": "Test",
                "element": "FIRE",
                "rank": "COMMON",
                "stats": {
                    "hp": 100.0 if stat_name != "hp" else value,
                    "atk": 100.0 if stat_name != "atk" else value,
                    "def": 100.0 if stat_name != "def" else value,
                    "vit": 100.0 if stat_name != "vit" else value,
                },
                "description_carte": "Test",
                "description_visuelle": "Test",
                "skills": make_valid_skills(4),
            }

            result = validator.validate(monster)
            assert result.is_valid == should_be_valid, f"Failed for {stat_name}={value}"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_validation_service.py -v
    print("Tests for Monster Validation Service")
    print("Run with: pytest tests/test_validation_service.py -v")
