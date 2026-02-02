"""
Monster JSON Validation Service
Validates generated monster JSON against schema, data types, enums, and value limits.
Follows SOLID principles with modular validators.
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from app.core.config import ValidationRules
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a single validation error"""

    field: str
    error_type: (
        str  # "type_mismatch", "enum_invalid", "value_out_of_range", "missing_field"
    )
    message: str


class ValidationResult:
    """Container for validation results"""

    def __init__(self, is_valid: bool, errors: Optional[List[ValidationError]] = None):
        self.is_valid = is_valid
        self.errors = errors or []

    def add_error(self, field: str, error_type: str, message: str):
        """Add an error to the result"""
        self.errors.append(ValidationError(field, error_type, message))

    def get_error_summary(self) -> str:
        """Generate human-readable error summary"""
        if self.is_valid:
            return "Validation passed"

        summary = f"Validation failed with {len(self.errors)} error(s):\n"
        for error in self.errors:
            summary += f"  - [{error.field}] ({error.error_type}): {error.message}\n"
        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "errors": [
                {"field": e.field, "error_type": e.error_type, "message": e.message}
                for e in self.errors
            ],
        }


class TypeValidator:
    """Validates data types"""

    TYPE_MAPPING = {
        "string": str,
        "float": (int, float),  # Accept both int and float for numeric fields
        "int": int,
        "list": list,
        "dict": dict,
    }

    @staticmethod
    def validate_type(value: Any, expected_type: str) -> Tuple[bool, str]:
        """
        Validate a value against expected type
        Returns (is_valid, error_message)
        """
        if expected_type not in TypeValidator.TYPE_MAPPING:
            return False, f"Unknown type: {expected_type}"

        expected = TypeValidator.TYPE_MAPPING[expected_type]
        if not isinstance(value, expected):
            return False, f"Expected {expected_type}, got {type(value).__name__}"

        return True, ""


class EnumValidator:
    """Validates enum-like string values"""

    @staticmethod
    def validate_enum(
        value: str, allowed_values: set, field_name: str
    ) -> Tuple[bool, str]:
        """
        Validate value is in allowed set
        Returns (is_valid, error_message)
        """
        if not isinstance(value, str):
            return False, f"Expected string, got {type(value).__name__}"

        if value not in allowed_values:
            return False, f"Invalid value '{value}'. Allowed: {allowed_values}"

        return True, ""


class RangeValidator:
    """Validates numeric values within ranges"""

    @staticmethod
    def validate_range(
        value: Any, min_val: float, max_val: float, field_name: str
    ) -> Tuple[bool, str]:
        """
        Validate numeric value is within range
        Returns (is_valid, error_message)
        """
        if not isinstance(value, (int, float)):
            return False, f"Expected numeric, got {type(value).__name__}"

        if value < min_val or value > max_val:
            return False, f"Value {value} out of range [{min_val}, {max_val}]"

        return True, ""


class MonsterStructureValidator:
    """Validates the overall monster JSON structure"""

    REQUIRED_TOP_LEVEL_FIELDS = {
        "nom": "string",
        "element": "string",
        "rang": "string",
        "stats": "dict",
        "description_carte": "string",
        "description_visuelle": "string",
        "skills": "list",
    }

    REQUIRED_STATS_FIELDS = {
        "hp": "float",
        "atk": "float",
        "def": "float",
        "vit": "float",
    }

    REQUIRED_SKILL_FIELDS = {
        "name": "string",
        "description": "string",
        "damage": "float",
        "ratio": "dict",
        "cooldown": "float",
        "lvlMax": "float",
        "rank": "string",
    }

    REQUIRED_SKILL_RATIO_FIELDS = {
        "stat": "string",
        "percent": "float",
    }

    @staticmethod
    def validate_structure(monster_data: Dict[str, Any]) -> ValidationResult:
        """Validate overall structure and required fields"""
        result = ValidationResult(True)

        # Check top-level fields
        for (
            field,
            expected_type,
        ) in MonsterStructureValidator.REQUIRED_TOP_LEVEL_FIELDS.items():
            if field not in monster_data:
                result.add_error(
                    field, "missing_field", f"Required field '{field}' is missing"
                )
                continue

            is_valid, error_msg = TypeValidator.validate_type(
                monster_data[field], expected_type
            )
            if not is_valid:
                result.add_error(field, "type_mismatch", error_msg)

        # Check stats structure
        if "stats" in monster_data and isinstance(monster_data["stats"], dict):
            stats = monster_data["stats"]
            for (
                field,
                expected_type,
            ) in MonsterStructureValidator.REQUIRED_STATS_FIELDS.items():
                if field not in stats:
                    result.add_error(
                        f"stats.{field}",
                        "missing_field",
                        f"Required field '{field}' is missing in stats",
                    )
                    continue

                is_valid, error_msg = TypeValidator.validate_type(
                    stats[field], expected_type
                )
                if not is_valid:
                    result.add_error(f"stats.{field}", "type_mismatch", error_msg)

        # Check skills structure
        if "skills" in monster_data and isinstance(monster_data["skills"], list):
            for idx, skill in enumerate(monster_data["skills"]):
                if not isinstance(skill, dict):
                    result.add_error(
                        f"skills[{idx}]",
                        "type_mismatch",
                        f"Skill must be a dict, got {type(skill).__name__}",
                    )
                    continue

                for (
                    field,
                    expected_type,
                ) in MonsterStructureValidator.REQUIRED_SKILL_FIELDS.items():
                    if field not in skill:
                        result.add_error(
                            f"skills[{idx}].{field}",
                            "missing_field",
                            f"Required field '{field}' is missing",
                        )
                        continue

                    is_valid, error_msg = TypeValidator.validate_type(
                        skill[field], expected_type
                    )
                    if not is_valid:
                        result.add_error(
                            f"skills[{idx}].{field}", "type_mismatch", error_msg
                        )

                # Check ratio structure
                if "ratio" in skill and isinstance(skill["ratio"], dict):
                    ratio = skill["ratio"]
                    for (
                        field,
                        expected_type,
                    ) in MonsterStructureValidator.REQUIRED_SKILL_RATIO_FIELDS.items():
                        if field not in ratio:
                            result.add_error(
                                f"skills[{idx}].ratio.{field}",
                                "missing_field",
                                f"Required field '{field}' is missing",
                            )
                            continue

                        is_valid, error_msg = TypeValidator.validate_type(
                            ratio[field], expected_type
                        )
                        if not is_valid:
                            result.add_error(
                                f"skills[{idx}].ratio.{field}",
                                "type_mismatch",
                                error_msg,
                            )

        result.is_valid = len(result.errors) == 0
        return result


class MonsterEnumValidator:
    """Validates enum constraints"""

    @staticmethod
    def validate_enums(monster_data: Dict[str, Any]) -> ValidationResult:
        """Validate all enum fields"""
        result = ValidationResult(True)

        # Validate element
        if "element" in monster_data:
            is_valid, error_msg = EnumValidator.validate_enum(
                monster_data["element"], ValidationRules.VALID_ELEMENTS, "element"
            )
            if not is_valid:
                result.add_error("element", "enum_invalid", error_msg)

        # Validate rank
        if "rang" in monster_data:
            is_valid, error_msg = EnumValidator.validate_enum(
                monster_data["rang"], ValidationRules.VALID_RANKS, "rang"
            )
            if not is_valid:
                result.add_error("rang", "enum_invalid", error_msg)

        # Validate skill stats
        if "skills" in monster_data and isinstance(monster_data["skills"], list):
            for idx, skill in enumerate(monster_data["skills"]):
                if isinstance(skill, dict):
                    # Validate skill rank
                    if "rank" in skill:
                        is_valid, error_msg = EnumValidator.validate_enum(
                            skill["rank"],
                            ValidationRules.VALID_RANKS,
                            f"skills[{idx}].rank",
                        )
                        if not is_valid:
                            result.add_error(
                                f"skills[{idx}].rank", "enum_invalid", error_msg
                            )

                    # Validate ratio stat
                    if "ratio" in skill and isinstance(skill["ratio"], dict):
                        if "stat" in skill["ratio"]:
                            is_valid, error_msg = EnumValidator.validate_enum(
                                skill["ratio"]["stat"],
                                ValidationRules.VALID_STATS,
                                f"skills[{idx}].ratio.stat",
                            )
                            if not is_valid:
                                result.add_error(
                                    f"skills[{idx}].ratio.stat",
                                    "enum_invalid",
                                    error_msg,
                                )

        result.is_valid = len(result.errors) == 0
        return result


class MonsterRangeValidator:
    """Validates numeric value ranges"""

    @staticmethod
    def validate_ranges(monster_data: Dict[str, Any]) -> ValidationResult:
        """Validate all numeric ranges"""
        result = ValidationResult(True)

        # Validate stats ranges
        if "stats" in monster_data and isinstance(monster_data["stats"], dict):
            stats = monster_data["stats"]
            for stat_name, (min_val, max_val) in ValidationRules.STAT_LIMITS.items():
                if stat_name in stats:
                    is_valid, error_msg = RangeValidator.validate_range(
                        stats[stat_name], min_val, max_val, f"stats.{stat_name}"
                    )
                    if not is_valid:
                        result.add_error(
                            f"stats.{stat_name}", "value_out_of_range", error_msg
                        )

        # Validate description_carte length
        if "description_carte" in monster_data:
            desc = monster_data["description_carte"]
            if len(desc) > ValidationRules.MAX_CARD_DESCRIPTION_LENGTH:
                result.add_error(
                    "description_carte",
                    "value_out_of_range",
                    f"Description too long ({len(desc)} chars). Max: {ValidationRules.MAX_CARD_DESCRIPTION_LENGTH}",
                )

        # Validate skill ranges
        if "skills" in monster_data and isinstance(monster_data["skills"], list):
            for idx, skill in enumerate(monster_data["skills"]):
                if isinstance(skill, dict):
                    # Validate damage
                    if "damage" in skill:
                        min_dmg, max_dmg = ValidationRules.SKILL_LIMITS["damage"]
                        is_valid, error_msg = RangeValidator.validate_range(
                            skill["damage"], min_dmg, max_dmg, f"skills[{idx}].damage"
                        )
                        if not is_valid:
                            result.add_error(
                                f"skills[{idx}].damage", "value_out_of_range", error_msg
                            )

                    # Validate cooldown
                    if "cooldown" in skill:
                        min_cool, max_cool = ValidationRules.SKILL_LIMITS["cooldown"]
                        is_valid, error_msg = RangeValidator.validate_range(
                            skill["cooldown"],
                            min_cool,
                            max_cool,
                            f"skills[{idx}].cooldown",
                        )
                        if not is_valid:
                            result.add_error(
                                f"skills[{idx}].cooldown",
                                "value_out_of_range",
                                error_msg,
                            )

                    # Validate lvlMax
                    if "lvlMax" in skill:
                        is_valid, error_msg = RangeValidator.validate_range(
                            skill["lvlMax"],
                            1.0,
                            ValidationRules.LVL_MAX,
                            f"skills[{idx}].lvlMax",
                        )
                        if not is_valid:
                            result.add_error(
                                f"skills[{idx}].lvlMax", "value_out_of_range", error_msg
                            )

                    # Validate ratio percent
                    if "ratio" in skill and isinstance(skill["ratio"], dict):
                        if "percent" in skill["ratio"]:
                            min_pct, max_pct = ValidationRules.SKILL_LIMITS["percent"]
                            is_valid, error_msg = RangeValidator.validate_range(
                                skill["ratio"]["percent"],
                                min_pct,
                                max_pct,
                                f"skills[{idx}].ratio.percent",
                            )
                            if not is_valid:
                                result.add_error(
                                    f"skills[{idx}].ratio.percent",
                                    "value_out_of_range",
                                    error_msg,
                                )

        result.is_valid = len(result.errors) == 0
        return result


class MonsterValidationService:
    """
    Main validation service - orchestrates all validators
    Implements the Facade pattern to provide a simple interface
    """

    def __init__(self):
        self.structure_validator = MonsterStructureValidator()
        self.enum_validator = MonsterEnumValidator()
        self.range_validator = MonsterRangeValidator()

    def validate(self, monster_data: Dict[str, Any]) -> ValidationResult:
        """
        Complete validation of monster JSON
        Returns ValidationResult with all errors found
        """
        # Run all validators
        structure_result = self.structure_validator.validate_structure(monster_data)
        enum_result = self.enum_validator.validate_enums(monster_data)
        range_result = self.range_validator.validate_ranges(monster_data)

        # Combine results
        combined_result = ValidationResult(True)
        combined_result.errors.extend(structure_result.errors)
        combined_result.errors.extend(enum_result.errors)
        combined_result.errors.extend(range_result.errors)
        combined_result.is_valid = len(combined_result.errors) == 0

        return combined_result
