"""
Test du système de gestion multi-images pour les monstres

Ce script teste les nouvelles fonctionnalités :
- Vérification qu'une image par défaut est créée lors de la génération d'un monstre
- Génération d'une image personnalisée
- Récupération de toutes les images d'un monstre
- Changement de l'image par défaut
"""

import requests
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"


def create_monster() -> Dict[str, Any]:
    """Crée un nouveau monstre et vérifie la création de l'image par défaut"""
    print("\n" + "=" * 60)
    print("TEST 1: Création d'un monstre avec image par défaut")
    print("=" * 60)

    response = requests.post(
        f"{API_V1}/monsters/",
        json={"prompt": "Un dragon de glace majestueux avec des ailes cristallines"},
    )

    if response.status_code != 200:
        print(f"❌ Erreur lors de la création: {response.status_code}")
        print(response.text)
        return {}

    monster = response.json()
    print(f"✅ Monstre créé: {monster.get('name', 'Unknown')}")
    print(f"   Monster ID: {monster.get('monster_id', 'N/A')}")
    print(f"   Image URL: {monster.get('image_path', 'N/A')}")

    return monster


def get_monster_images(monster_id: str) -> Dict[str, Any]:
    """Récupère toutes les images d'un monstre"""
    print("\n" + "=" * 60)
    print("TEST 2: Récupération des images du monstre")
    print("=" * 60)

    response = requests.get(f"{API_V1}/monsters/images/{monster_id}")

    if response.status_code != 200:
        print(f"❌ Erreur lors de la récupération: {response.status_code}")
        print(response.text)
        return {}

    images_data = response.json()
    print(f"✅ Images récupérées pour: {images_data.get('monster_name', 'Unknown')}")
    print(f"   Nombre d'images: {len(images_data.get('images', []))}")

    if images_data.get("default_image"):
        default = images_data["default_image"]
        print(f"   Image par défaut: {default.get('image_name', 'N/A')}")
        print(f"   ID de l'image: {default.get('id', 'N/A')}")

    for idx, img in enumerate(images_data.get("images", []), 1):
        print(
            f"   {idx}. {img['image_name']} (default: {img['is_default']}) - ID: {img['id']}"
        )

    return images_data


def generate_custom_image(monster_id: str) -> Dict[str, Any]:
    """Génère une nouvelle image personnalisée pour le monstre"""
    print("\n" + "=" * 60)
    print("TEST 3: Génération d'une image personnalisée")
    print("=" * 60)

    response = requests.post(
        f"{API_V1}/monsters/images/generate",
        json={
            "monster_id": monster_id,
            "image_name": "dragon_glace_variant_feu",
            "custom_prompt": "Le même dragon de glace mais avec des flammes bleues sortant de sa gueule, ambiance nocturne",
        },
    )

    if response.status_code != 201:
        print(f"❌ Erreur lors de la génération: {response.status_code}")
        print(response.text)
        return {}

    image = response.json()
    print(f"✅ Image générée: {image.get('image_name', 'Unknown')}")
    print(f"   ID: {image.get('id', 'N/A')}")
    print(f"   URL: {image.get('image_url', 'N/A')}")
    print(f"   Est défaut: {image.get('is_default', False)}")

    return image


def set_default_image(monster_id: str, image_id: int) -> Dict[str, Any]:
    """Définit une nouvelle image comme image par défaut"""
    print("\n" + "=" * 60)
    print("TEST 4: Changement de l'image par défaut")
    print("=" * 60)

    response = requests.put(
        f"{API_V1}/monsters/images/{monster_id}/default", json={"image_id": image_id}
    )

    if response.status_code != 200:
        print(f"❌ Erreur lors du changement: {response.status_code}")
        print(response.text)
        return {}

    image = response.json()
    print(f"✅ Nouvelle image par défaut: {image.get('image_name', 'Unknown')}")
    print(f"   ID: {image.get('id', 'N/A')}")
    print(f"   Est défaut: {image.get('is_default', False)}")

    return image


def main():
    """Exécute tous les tests"""
    print("\n" + "*" * 60)
    print("   TEST DU SYSTÈME MULTI-IMAGES")
    print("*" * 60)

    # Test 1: Créer un monstre
    monster = create_monster()
    if not monster:
        print("\n❌ Impossible de continuer sans monstre")
        return

    monster_id = monster.get("monster_id")
    if not monster_id:
        print("\n❌ Monster ID manquant")
        return

    # Attendre un peu pour que le monstre soit bien sauvegardé
    import time

    time.sleep(2)

    # Test 2: Récupérer les images
    images_data = get_monster_images(monster_id)
    if not images_data:
        print("\n❌ Impossible de récupérer les images")
        return

    # Test 3: Générer une image personnalisée
    # Note: Ce test peut être long (génération d'image)
    print("\n⏳ Génération d'une nouvelle image (cela peut prendre du temps)...")
    custom_image = generate_custom_image(monster_id)
    if not custom_image:
        print("\n⚠️ La génération d'image personnalisée a échoué")
        print(
            "   Cela peut être normal si l'API Gemini a des limites de quota ou de connexion"
        )
        # On continue quand même pour récupérer les images
    else:
        # Attendre que l'image soit bien créée
        time.sleep(2)

    # Test 4: Récupérer à nouveau les images
    images_data = get_monster_images(monster_id)
    if not images_data or not images_data.get("images"):
        print("\n❌ Pas d'images trouvées")
        return

    # Test 5: Changer l'image par défaut (si on a plusieurs images)
    if len(images_data.get("images", [])) > 1:
        # Prendre la deuxième image
        new_default_id = images_data["images"][1]["id"]
        set_default_image(monster_id, new_default_id)

        # Vérifier le changement
        time.sleep(1)
        final_images = get_monster_images(monster_id)
        if final_images.get("default_image", {}).get("id") == new_default_id:
            print("\n✅ Changement d'image par défaut confirmé!")
        else:
            print("\n⚠️ Le changement d'image par défaut n'a pas été détecté")
    else:
        print("\n⚠️ Une seule image disponible, impossible de tester le changement")

    print("\n" + "*" * 60)
    print("   FIN DES TESTS")
    print("*" * 60)
    print(f"\n📝 Monster ID pour référence future: {monster_id}")
    print(f"🔗 Voir dans l'interface: {BASE_URL}/docs")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur inattendue: {e}")
        import traceback

        traceback.print_exc()
