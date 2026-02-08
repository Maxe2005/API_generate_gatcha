# 🚀 Quick Start - Système de Cycle de Vie

## ⚡ Démarrage Rapide (3 minutes)

### 1. Installation (si pas déjà fait)
```bash
pip install -r requirements.txt
```

### 2. Lancer l'API
```bash
uvicorn app.main:app --reload
```

### 3. Ouvrir Swagger
```
http://localhost:8000/docs
```

## 📋 Endpoints Clés à Tester

### Dashboard (statistiques)
```
GET /api/v1/admin/dashboard/stats
```

### Lister tous les monstres
```
GET /api/v1/admin/monsters
```

### Lister par état
```
GET /api/v1/admin/monsters?state=PENDING_REVIEW
```

### Détails d'un monstre
```
GET /api/v1/admin/monsters/{monster_id}
```

### Approuver un monstre
```
POST /api/v1/admin/monsters/{monster_id}/review
Body: {"action": "approve", "notes": "OK"}
```

### Transmettre à l'API Invocation
```
POST /api/v1/transmission/transmit/{monster_id}
```

## 🔍 États Disponibles

- **GENERATED** : Monstre généré
- **DEFECTIVE** : Monstre avec erreurs de validation
- **CORRECTED** : Monstre corrigé
- **PENDING_REVIEW** : En attente de validation admin
- **APPROVED** : Approuvé par admin
- **TRANSMITTED** : Envoyé à l'API d'invocation
- **REJECTED** : Rejeté par admin

## 📁 Structure des Fichiers

```
app/static/
├── metadata/              # Métadonnées de tous les monstres
├── jsons/
│   ├── generated/         # État GENERATED
│   ├── defective/         # État DEFECTIVE
│   ├── corrected/         # État CORRECTED
│   ├── pending_review/    # État PENDING_REVIEW
│   ├── approved/          # État APPROVED
│   ├── transmitted/       # État TRANSMITTED
│   └── rejected/          # État REJECTED
```

## 🎯 Workflow Simple

1. **Générer** un monstre → GENERATED
2. **Validation auto** → PENDING_REVIEW (si valide) ou DEFECTIVE (si erreurs)
3. **Admin review** → APPROVED ou REJECTED
4. **Transmission** → TRANSMITTED

## 📚 Documentation Complète

- `IMPLEMENTATION_SUMMARY.md` - Résumé de l'implémentation
- `TESTING_GUIDE.md` - Guide de test détaillé
- `docs/` - Documentation technique complète

## ⚠️ Notes Importantes

- L'API d'invocation doit être accessible sur `http://localhost:8085` (configurable dans `.env`)
- Les logs sont dans `logs/app.log`
- Les monstres existants peuvent être migrés avec `python3 scripts/migrate_existing_monsters.py`

## 🆘 Problèmes Courants

**L'API ne démarre pas**
```bash
# Vérifier les dépendances
pip install -r requirements.txt
```

**Erreur 404 sur un monstre**
```bash
# Utiliser le monster_id, pas le filename
# Le monster_id est dans la réponse de la liste des monstres
```

**Transmission échoue**
```bash
# Vérifier que l'API d'invocation est lancée
curl http://localhost:8085/health
```

---

**Tout fonctionne ?** Consultez `TESTING_GUIDE.md` pour des tests plus approfondis !
