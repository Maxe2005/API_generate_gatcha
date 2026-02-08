# 🧪 Guide de Test - Système de Cycle de Vie

## Prérequis

```bash
# Installer les dépendances
pip install -r requirements.txt

# Créer le fichier .env (si nécessaire)
cp .env.example .env

# Variables importantes dans .env
INVOCATION_API_URL=http://localhost:8085
GEMINI_API_KEY=your_key_here
BANANA_API_KEY=your_key_here
```

## 1. Tests Manuels via Swagger

### Démarrer l'API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Accéder à Swagger
```
http://localhost:8000/docs
```

### Scénario de test complet

#### A. Vérifier le dashboard initial
```
GET /api/v1/admin/dashboard/stats
```
Vous devriez voir les statistiques des monstres existants.

#### B. Lister les monstres
```
GET /api/v1/admin/monsters?limit=10
```

#### C. Lister par état
```
GET /api/v1/admin/monsters?state=PENDING_REVIEW&limit=10
```

#### D. Voir les détails d'un monstre
```
GET /api/v1/admin/monsters/{monster_id}
```

#### E. Voir l'historique
```
GET /api/v1/admin/monsters/{monster_id}/history
```

#### F. Approuver un monstre (si en PENDING_REVIEW)
```
POST /api/v1/admin/monsters/{monster_id}/review
Body:
{
  "action": "approve",
  "notes": "Looks good!"
}
```

#### G. Transmettre un monstre approuvé
```
POST /api/v1/transmission/transmit/{monster_id}
```

#### H. Health check de l'API d'invocation
```
GET /api/v1/transmission/health-check
```

## 2. Tests avec cURL

### Dashboard Stats
```bash
curl -X GET http://localhost:8000/api/v1/admin/dashboard/stats
```

### Liste des monstres
```bash
curl -X GET "http://localhost:8000/api/v1/admin/monsters?limit=5"
```

### Liste des monstres en PENDING_REVIEW
```bash
curl -X GET "http://localhost:8000/api/v1/admin/monsters?state=PENDING_REVIEW&limit=5"
```

### Détails d'un monstre
```bash
curl -X GET http://localhost:8000/api/v1/admin/monsters/{MONSTER_ID}
```

### Approuver un monstre
```bash
curl -X POST http://localhost:8000/api/v1/admin/monsters/{MONSTER_ID}/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "notes": "Approved via cURL"
  }'
```

### Transmettre un monstre
```bash
curl -X POST http://localhost:8000/api/v1/transmission/transmit/{MONSTER_ID}
```

## 3. Tests Python

### Test basique d'import
```python
# test_imports.py
from app.schemas.monster import MonsterState, TransitionAction
from app.schemas.metadata import MonsterMetadata
from app.services.state_manager import MonsterStateManager
from app.repositories.monster_repository import MonsterRepository
from app.services.admin_service import AdminService

print("✅ All imports successful!")
```

### Test du StateManager
```python
# test_state_manager.py
from app.services.state_manager import MonsterStateManager
from app.schemas.monster import MonsterState

manager = MonsterStateManager()

# Test transition valide
assert manager.can_transition(MonsterState.GENERATED, MonsterState.PENDING_REVIEW)
print("✅ Valid transition check passed")

# Test transition invalide
assert not manager.can_transition(MonsterState.TRANSMITTED, MonsterState.PENDING_REVIEW)
print("✅ Invalid transition check passed")

# Test états finaux
assert manager.is_final_state(MonsterState.TRANSMITTED)
assert manager.is_final_state(MonsterState.REJECTED)
print("✅ Final state check passed")

print("✅ StateManager tests passed!")
```

### Test du Repository
```python
# test_repository.py
from app.repositories.monster_repository import MonsterRepository
from app.schemas.monster import MonsterState

repo = MonsterRepository()

# Compter par état
counts = repo.count_by_state()
print(f"Monsters by state: {counts}")

# Lister tous les monstres
monsters = repo.list_all(limit=5)
print(f"Found {len(monsters)} monsters")

# Lister par état
pending = repo.list_by_state(MonsterState.PENDING_REVIEW, limit=5)
print(f"Pending review: {len(pending)}")

print("✅ Repository tests passed!")
```

## 4. Migration des Données Existantes

```bash
# Backup des données actuelles (recommandé)
cp -r app/static/jsons app/static/jsons_backup
cp -r app/static/jsons_defective app/static/jsons_defective_backup

# Exécuter la migration
python3 scripts/migrate_existing_monsters.py

# Vérifier le résultat
ls -la app/static/metadata/
ls -la app/static/jsons/transmitted/
ls -la app/static/jsons/defective/
```

## 5. Test du Workflow Complet

### Script de test end-to-end
```python
# test_workflow.py
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def test_workflow():
    async with httpx.AsyncClient() as client:
        # 1. Get dashboard stats
        print("1. Getting dashboard stats...")
        response = await client.get(f"{BASE_URL}/admin/dashboard/stats")
        stats = response.json()
        print(f"   Total monsters: {stats['total_monsters']}")
        print(f"   By state: {stats['by_state']}")
        
        # 2. List pending review monsters
        print("\n2. Listing pending review monsters...")
        response = await client.get(
            f"{BASE_URL}/admin/monsters",
            params={"state": "PENDING_REVIEW", "limit": 1}
        )
        monsters = response.json()
        
        if not monsters:
            print("   No monsters pending review")
            return
        
        monster_id = monsters[0]["monster_id"]
        print(f"   Found monster: {monster_id}")
        
        # 3. Get monster details
        print("\n3. Getting monster details...")
        response = await client.get(f"{BASE_URL}/admin/monsters/{monster_id}")
        detail = response.json()
        print(f"   Name: {detail['monster_data']['nom']}")
        print(f"   State: {detail['metadata']['state']}")
        
        # 4. Approve monster
        print("\n4. Approving monster...")
        response = await client.post(
            f"{BASE_URL}/admin/monsters/{monster_id}/review",
            json={
                "action": "approve",
                "notes": "Test approval"
            }
        )
        result = response.json()
        print(f"   New state: {result['new_state']}")
        
        # 5. Check transmission health
        print("\n5. Checking invocation API health...")
        response = await client.get(f"{BASE_URL}/transmission/health-check")
        health = response.json()
        print(f"   API healthy: {health['invocation_api_healthy']}")
        
        if health['invocation_api_healthy']:
            # 6. Transmit monster
            print("\n6. Transmitting monster...")
            response = await client.post(f"{BASE_URL}/transmission/transmit/{monster_id}")
            result = response.json()
            print(f"   Status: {result['status']}")
            print(f"   Invocation API ID: {result.get('invocation_api_id')}")
        else:
            print("\n⚠️  Invocation API not available, skipping transmission")
        
        print("\n✅ Workflow test completed!")

if __name__ == "__main__":
    asyncio.run(test_workflow())
```

Exécuter :
```bash
python3 test_workflow.py
```

## 6. Vérifications Post-Migration

### Vérifier la structure des fichiers
```bash
# Compter les métadonnées
echo "Metadata files:"
ls -1 app/static/metadata/*.json | wc -l

# Compter par dossier
for dir in generated defective corrected pending_review approved transmitted rejected; do
    count=$(ls -1 app/static/jsons/$dir/*.json 2>/dev/null | wc -l)
    echo "$dir: $count"
done
```

### Vérifier le contenu d'une métadonnée
```bash
# Prendre une métadonnée au hasard
file=$(ls app/static/metadata/*.json | head -1)
cat $file | python3 -m json.tool
```

## 7. Tests d'Erreurs

### Essayer une transition invalide
```bash
# Approuver un monstre déjà transmis (devrait échouer)
curl -X POST http://localhost:8000/api/v1/admin/monsters/{TRANSMITTED_MONSTER_ID}/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "notes": "This should fail"
  }'
```

### Transmettre un monstre non approuvé
```bash
# Devrait échouer
curl -X POST http://localhost:8000/api/v1/transmission/transmit/{PENDING_MONSTER_ID}
```

## 8. Surveillance des Logs

```bash
# Suivre les logs en temps réel
tail -f logs/app.log

# Chercher les erreurs
grep ERROR logs/app.log

# Chercher les transitions
grep "transition" logs/app.log
```

## 9. Checklist de Validation

- [ ] L'API démarre sans erreur
- [ ] Swagger est accessible
- [ ] Dashboard stats retourne des données
- [ ] Liste des monstres fonctionne
- [ ] Filtrage par état fonctionne
- [ ] Détails d'un monstre sont complets
- [ ] Historique des transitions est visible
- [ ] Approbation d'un monstre fonctionne
- [ ] Rejet d'un monstre fonctionne
- [ ] Correction d'un défaut fonctionne
- [ ] Health check invocation API répond
- [ ] Transmission d'un monstre fonctionne (si API disponible)
- [ ] Transmission batch fonctionne (si API disponible)
- [ ] Les logs sont écrits correctement
- [ ] Les métadonnées sont sauvegardées
- [ ] Les fichiers sont déplacés selon les états

## 10. Troubleshooting

### Erreur d'import
```bash
# Vérifier que pydantic est installé
pip list | grep pydantic

# Réinstaller si nécessaire
pip install -r requirements.txt
```

### API ne démarre pas
```bash
# Vérifier la syntaxe
python3 -m py_compile app/main.py

# Vérifier les imports
python3 -c "from app.main import app; print('OK')"
```

### Métadonnées introuvables
```bash
# Vérifier que le dossier existe
ls -la app/static/metadata/

# Recréer si nécessaire
python3 scripts/setup_directories.py
```

### Transmission échoue
```bash
# Vérifier l'URL de l'API d'invocation
echo $INVOCATION_API_URL

# Tester manuellement
curl http://localhost:8085/health
```

---

**Note** : Ces tests supposent que l'API est lancée en local. Adaptez les URLs si nécessaire.
