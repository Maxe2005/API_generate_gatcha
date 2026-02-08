"""
Script de configuration de la structure de dossiers

Ce script crée tous les dossiers nécessaires pour le système
de gestion du cycle de vie des monstres.
"""

from pathlib import Path


def setup_directories():
    """Crée la structure de dossiers pour le système"""
    base = Path("app/static")

    dirs = [
        base / "metadata",
        base / "jsons" / "generated",
        base / "jsons" / "defective",
        base / "jsons" / "corrected",
        base / "jsons" / "pending_review",
        base / "jsons" / "approved",
        base / "jsons" / "transmitted",
        base / "jsons" / "rejected",
        Path("logs"),
    ]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {dir_path}")

    print(f"\n✅ All directories created successfully!")


if __name__ == "__main__":
    setup_directories()
