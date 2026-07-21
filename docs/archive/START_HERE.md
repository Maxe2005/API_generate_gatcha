# 🎊 Migration PostgreSQL - Fichier de Démarrage

**Bienvenue!** Vous venez de migrer vers PostgreSQL avec pgAdmin. 🚀

## ⚡ Démarrage en 30 secondes

```bash
# Une seule commande pour tout!
./scripts/setup_postgres.sh

# Accéder à pgAdmin après
open http://localhost:5050
# Login: admin@gatcha.local / admin
```

---

## 📚 Documentation (Choisir votre niveau)

### 🏃‍♂️ Pressé? (5 minutes)
→ Lire [POSTGRESQL_QUICKSTART.md](POSTGRESQL_QUICKSTART.md)

### 🚴‍♂️ Temps limité? (20 minutes)
→ Lire [MIGRATION_POSTGRESQL.md](MIGRATION_POSTGRESQL.md)

### 🧑‍💻 Développeur? (30 minutes)
→ Lire [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) + [app/models/README.md](app/models/README.md)

### 🔍 Besoin de requêtes SQL?
→ Consulter [docs/POSTGRESQL_REFERENCE.md](docs/POSTGRESQL_REFERENCE.md)

### ✅ Vérification complète?
→ Lire [VERIFICATION_FINALE.md](VERIFICATION_FINALE.md)

---

## 🎯 Ce qui a changé

| Avant | Après |
|-------|-------|
| 📁 Fichiers JSON | 🗄️ PostgreSQL Database |
| ❌ Pas de visualisation | ✅ pgAdmin Web UI |
| 📂 Dossiers par état | 📊 Tables relationnelles |
| ⚠️ Pas de transactions | ✅ ACID Garanties |
| 🐢 Lent (fichiers) | ⚡ Rapide (SQL) |

---

## ✨ Services Disponibles

```
API:           http://localhost:8000/docs
pgAdmin:       http://localhost:5050
PostgreSQL:    localhost:5432
MinIO:         http://localhost:9001
```

**Credentials pgAdmin:**
- Email: `admin@gatcha.local`
- Password: `admin`

---

## 🛠️ Commandes Utiles

```bash
# Migration complète
./scripts/setup_postgres.sh

# Voir les stats
make db-stats

# Shell SQL
make db-shell

# Sauvegarder
make db-backup

# Ouvrir pgAdmin
make pgadmin

# Tous les commandes
make help
```

---

## 📂 Nouveau Dossier: app/models/

Les modèles SQLAlchemy suivants ont été créés:

- `base.py` - Configuration (engine, sessions, init_db)
- `monster_model.py` - Modèles Monster et StateTransition
- `README.md` - Documentation des modèles

---

## 🎓 Prochaines Étapes

1. ✅ Exécuter `./scripts/setup_postgres.sh`
2. ✅ Vérifier pgAdmin http://localhost:5050
3. ✅ Lire [POSTGRESQL_QUICKSTART.md](POSTGRESQL_QUICKSTART.md)
4. ✅ Tester les endpoints http://localhost:8000/docs

---

## 🚨 Problèm?

### PostgreSQL ne démarre pas?
```bash
docker-compose logs postgres
# Attendre "ready to accept connections"
```

### pgAdmin ne se connecte pas?
- Host: `postgres` (pas `localhost`)
- Port: `5432`
- Database: `gatcha_db`
- User: `gatcha_user`
- Password: `gatcha_password`

### Migration échoue?
```bash
python scripts/migrate_json_to_postgres.py --dry-run
```

---

## 📞 Aide Rapide

- 📖 [MIGRATION_POSTGRESQL.md](MIGRATION_POSTGRESQL.md) - Guide complet
- 🔍 [docs/POSTGRESQL_REFERENCE.md](docs/POSTGRESQL_REFERENCE.md) - Requêtes SQL
- ✅ [VERIFICATION_FINALE.md](VERIFICATION_FINALE.md) - Checklist

---

## 🎉 Bienvenue sur PostgreSQL!

You have successfully moved from JSON files to a professional PostgreSQL database with pgAdmin visualization.

**Let's go! 🚀**

```bash
./scripts/setup_postgres.sh
```
