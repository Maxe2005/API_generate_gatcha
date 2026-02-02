import os
import re
import json
import unicodedata
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


class FileManager:
    def __init__(
        self,
        output_dir: str = "app/static/jsons",
        defective_dir: str = "app/static/jsons_defective",
    ):
        self.output_dir = output_dir
        self.defective_dir = defective_dir
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.defective_dir, exist_ok=True)

    def sanitize_filename(self, name: str) -> str:
        """Converts name to lowercase, removes accents and spaces/special chars"""
        name = (
            unicodedata.normalize("NFKD", name)
            .encode("ASCII", "ignore")
            .decode("ASCII")
        )
        name = name.lower()
        # Keep only alphanumeric
        name = re.sub(r"[^a-z0-9]", "", name)
        return name

    def save_json(self, filename: str, data: Dict[str, Any]) -> str:
        """
        Saves dictionary to JSON file.
        Returns the absolute path to the saved file.
        """
        # Ensure extension
        if not filename.endswith(".json"):
            filename += ".json"

        file_path = os.path.join(self.output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return file_path

    def get_relative_path(self, filename: str) -> str:
        if not filename.endswith(".json"):
            filename += ".json"
        return f"/static/jsons/{filename}"

    # ===== Defective JSON Management (New) =====

    def save_defective_json(
        self,
        filename: str,
        data: Dict[str, Any],
        validation_errors: List[Dict[str, Any]],
    ) -> str:
        """
        Saves defective JSON to defective folder with metadata
        Returns the absolute path to the saved file
        """
        if not filename.endswith(".json"):
            filename += ".json"

        # Add timestamp to filename to avoid conflicts
        name_without_ext = filename[:-5]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name_without_ext}_{timestamp}.json"

        file_path = os.path.join(self.defective_dir, filename)

        # Wrap data with metadata
        defective_data = {
            "created_at": datetime.now().isoformat(),
            "status": "pending_review",
            "monster_data": data,
            "validation_errors": validation_errors,
            "notes": "",  # Admin can add notes here
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(defective_data, f, ensure_ascii=False, indent=4)

        return file_path

    def get_defective_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load a defective JSON file"""
        if not filename.endswith(".json"):
            filename += ".json"

        file_path = os.path.join(self.defective_dir, filename)

        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_defective_jsons(self) -> List[Dict[str, Any]]:
        """List all defective JSONs with metadata"""
        defective_list = []

        if not os.path.exists(self.defective_dir):
            return defective_list

        for filename in os.listdir(self.defective_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.defective_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        defective_list.append(
                            {
                                "filename": filename,
                                "created_at": data.get("created_at"),
                                "status": data.get("status"),
                                "error_count": len(data.get("validation_errors", [])),
                                "monster_name": data.get("monster_data", {}).get(
                                    "nom", "unknown"
                                ),
                            }
                        )
                except Exception as e:
                    # Log but continue listing other files
                    print(f"Error reading {filename}: {e}")

        return sorted(defective_list, key=lambda x: x["created_at"], reverse=True)

    def move_defective_to_valid(
        self, defective_filename: str, updated_data: Dict[str, Any]
    ) -> str:
        """
        Move a corrected defective JSON to valid folder
        Returns the path to the new file
        """
        if not defective_filename.endswith(".json"):
            defective_filename += ".json"

        defective_path = os.path.join(self.defective_dir, defective_filename)

        if not os.path.exists(defective_path):
            raise FileNotFoundError(f"Defective file not found: {defective_filename}")

        # Extract monster name for new filename
        monster_name = updated_data.get("nom", "monster")
        sanitized_name = self.sanitize_filename(monster_name)

        if not sanitized_name:
            sanitized_name = f"monster_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Save to valid folder
        new_path = self.save_json(sanitized_name, updated_data)

        # Delete defective file
        os.remove(defective_path)

        return new_path

    def delete_defective_json(self, filename: str) -> bool:
        """Delete a defective JSON file"""
        if not filename.endswith(".json"):
            filename += ".json"

        file_path = os.path.join(self.defective_dir, filename)

        if not os.path.exists(file_path):
            return False

        os.remove(file_path)
        return True

    def update_defective_json(
        self,
        filename: str,
        updated_data: Dict[str, Any],
        new_status: str = "pending_review",
        notes: str = "",
    ) -> Optional[str]:
        """
        Update a defective JSON with corrections
        Returns the path to the updated file
        """
        if not filename.endswith(".json"):
            filename += ".json"

        file_path = os.path.join(self.defective_dir, filename)

        if not os.path.exists(file_path):
            return None

        # Load existing metadata
        with open(file_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)

        # Update monster data and metadata
        existing_data["monster_data"] = updated_data
        existing_data["status"] = new_status
        existing_data["notes"] = notes
        existing_data["updated_at"] = datetime.now().isoformat()

        # Save updated file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)

        return file_path
