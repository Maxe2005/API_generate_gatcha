"""
Example: Admin Panel Python Client for managing defective monsters

This script demonstrates how to interact with the validation admin endpoints
to review and correct defective monster JSONs.
"""

import requests
import json
from typing import List, Dict, Any
from datetime import datetime


class AdminClient:
    """Client for interacting with the admin API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_v1 = f"{base_url}/api/v1/admin"

    def list_defective_monsters(self) -> List[Dict[str, Any]]:
        """Get list of all defective monsters"""
        response = requests.get(f"{self.api_v1}/defective")
        response.raise_for_status()
        return response.json()

    def get_defective_monster(self, filename: str) -> Dict[str, Any]:
        """Get details of a specific defective monster"""
        if not filename.endswith(".json"):
            filename += ".json"
        response = requests.get(f"{self.api_v1}/defective/{filename}")
        response.raise_for_status()
        return response.json()

    def validate_monster(self, filename: str) -> Dict[str, Any]:
        """Validate a defective monster without approving"""
        if not filename.endswith(".json"):
            filename += ".json"
        response = requests.post(f"{self.api_v1}/defective/{filename}/validate")
        response.raise_for_status()
        return response.json()

    def approve_monster(
        self, filename: str, corrected_data: Dict[str, Any], notes: str = ""
    ) -> Dict[str, Any]:
        """Approve and correct a defective monster"""
        if not filename.endswith(".json"):
            filename += ".json"

        payload = {"corrected_data": corrected_data, "notes": notes}

        response = requests.post(
            f"{self.api_v1}/defective/{filename}/approve", json=payload
        )
        response.raise_for_status()
        return response.json()

    def reject_monster(self, filename: str, reason: str) -> Dict[str, Any]:
        """Reject and delete a defective monster"""
        if not filename.endswith(".json"):
            filename += ".json"

        payload = {"reason": reason}

        response = requests.post(
            f"{self.api_v1}/defective/{filename}/reject", json=payload
        )
        response.raise_for_status()
        return response.json()

    def update_monster(
        self, filename: str, corrected_data: Dict[str, Any], notes: str = ""
    ) -> Dict[str, Any]:
        """Update a defective monster (without approval)"""
        if not filename.endswith(".json"):
            filename += ".json"

        payload = {"corrected_data": corrected_data, "notes": notes}

        response = requests.put(
            f"{self.api_v1}/defective/{filename}/update", json=payload
        )
        response.raise_for_status()
        return response.json()

    def get_validation_rules(self) -> Dict[str, Any]:
        """Get all validation rules"""
        response = requests.get(f"{self.api_v1}/validation-rules")
        response.raise_for_status()
        return response.json()


def print_monster_summary(monster: Dict[str, Any]) -> None:
    """Pretty print a monster summary"""
    print(f"  Name: {monster.get('monster_name', 'Unknown')}")
    print(f"  Created: {monster.get('created_at', 'Unknown')}")
    print(f"  Status: {monster.get('status', 'Unknown')}")
    print(f"  Errors: {monster.get('error_count', 0)}")


def print_validation_errors(errors: List[Dict[str, Any]]) -> None:
    """Pretty print validation errors"""
    for error in errors:
        print(f"\n  ❌ [{error['field']}] ({error['error_type']})")
        print(f"     {error['message']}")


def print_validation_rules(rules: Dict[str, Any]) -> None:
    """Pretty print validation rules"""
    print("\n📋 VALIDATION RULES:")
    print(f"\n  Valid Stats: {', '.join(rules['valid_stats'])}")
    print(f"  Valid Elements: {', '.join(rules['valid_elements'])}")
    print(f"  Valid Ranks: {', '.join(rules['valid_ranks'])}")

    print("\n  📊 Stat Limits:")
    for stat, limits in rules["stat_limits"].items():
        print(f"    {stat}: [{limits['min']}, {limits['max']}]")

    print("\n  ⚔️ Skill Limits:")
    for skill, limits in rules["skill_limits"].items():
        print(f"    {skill}: [{limits['min']}, {limits['max']}]")

    print(f"\n  Max Level: {rules['lvl_max']}")
    print(f"  Max Description Length: {rules['max_card_description_length']}")


# Example workflows
def workflow_review_defectives():
    """Example: Review all defective monsters"""
    client = AdminClient()

    print("🔍 REVIEWING DEFECTIVE MONSTERS")
    print("=" * 50)

    defectives = client.list_defective_monsters()

    if not defectives:
        print("✅ No defective monsters!")
        return

    print(f"\nFound {len(defectives)} defective monster(s):\n")

    for i, monster in enumerate(defectives, 1):
        print(f"{i}. {monster['filename']}")
        print_monster_summary(monster)
        print()


def workflow_fix_monster(filename: str):
    """Example: Fix a specific monster"""
    client = AdminClient()

    print(f"🔧 FIXING MONSTER: {filename}")
    print("=" * 50)

    # Get details
    monster = client.get_defective_monster(filename)

    print(f"\nOriginal data for '{monster['monster_data']['nom']}':")
    print(json.dumps(monster["monster_data"], indent=2))

    print("\n❌ Validation errors:")
    print_validation_errors(monster["validation_errors"])

    # Get validation rules for reference
    rules = client.get_validation_rules()
    print_validation_rules(rules)

    # In a real admin UI, the user would edit the data here
    # For this example, we'll just make some basic corrections

    corrected_data = monster["monster_data"].copy()

    # Fix element if invalid
    if corrected_data.get("element") not in rules["valid_elements"]:
        print(f"\n⚠️  Invalid element '{corrected_data['element']}'")
        corrected_data["element"] = "FIRE"  # Default fix
        print(f"   Fixed to: FIRE")

    # Fix rank if invalid
    if corrected_data.get("rang") not in rules["valid_ranks"]:
        print(f"\n⚠️  Invalid rank '{corrected_data['rang']}'")
        corrected_data["rang"] = "COMMON"  # Default fix
        print(f"   Fixed to: COMMON")

    # Validate corrections
    print("\n🔍 Validating corrections...")
    validation = client.validate_monster(filename)

    if validation["is_valid"]:
        print("✅ Corrections look good!")

        # Approve
        print("\n✅ Approving monster...")
        result = client.approve_monster(
            filename, corrected_data, notes="Auto-fixed invalid enum values"
        )

        print(f"✅ Monster approved!")
        print(f"   New path: {result.get('new_path')}")
    else:
        print("❌ Corrections still have errors:")
        for error in validation["validation"]["errors"]:
            print(f"   - [{error['field']}] {error['message']}")


def workflow_reject_monster(filename: str, reason: str):
    """Example: Reject a monster"""
    client = AdminClient()

    print(f"🗑️  REJECTING MONSTER: {filename}")
    print("=" * 50)

    result = client.reject_monster(filename, reason)
    print(f"✅ Monster deleted: {result['message']}")
    print(f"   Reason: {reason}")


def workflow_batch_review():
    """Example: Batch review all defectives"""
    client = AdminClient()

    print("📦 BATCH REVIEWING DEFECTIVES")
    print("=" * 50)

    defectives = client.list_defective_monsters()

    print(f"\nFound {len(defectives)} defective monster(s)\n")

    approved = 0
    rejected = 0

    for monster in defectives:
        filename = monster["filename"]
        error_count = monster["error_count"]

        print(f"\nProcessing: {monster['monster_name']} ({error_count} errors)")

        # Simple heuristic: reject if too many errors
        if error_count > 5:
            print(f"  → Too many errors, rejecting...")
            try:
                client.reject_monster(
                    filename, f"Too many validation errors ({error_count})"
                )
                rejected += 1
            except Exception as e:
                print(f"  ✗ Error: {e}")
        else:
            print(f"  → Worth fixing, review manually")

    print(f"\n📊 Summary: {approved} approved, {rejected} rejected")


if __name__ == "__main__":
    print("🎮 GATCHA MONSTER ADMIN CLIENT")
    print("=" * 50)

    # Example 1: List defectives
    print("\n1️⃣  Listing defective monsters...")
    try:
        workflow_review_defectives()
    except requests.exceptions.ConnectionError:
        print(
            "❌ Cannot connect to API. Make sure it's running on http://localhost:8000"
        )

    # Example 2: Get validation rules
    print("\n2️⃣  Fetching validation rules...")
    try:
        client = AdminClient()
        rules = client.get_validation_rules()
        print_validation_rules(rules)
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 50)
    print("For real usage, adapt the workflow functions to your needs!")
