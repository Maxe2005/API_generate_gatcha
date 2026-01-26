import os
import re
import json
import unicodedata
from typing import Dict, Any


class FileManager:
    def __init__(self, output_dir: str = "app/static/jsons"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

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
