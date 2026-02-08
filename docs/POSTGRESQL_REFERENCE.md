# PostgreSQL - Référence Rapide

## 🔗 Connexions

### Via pgAdmin (Interface Web)
```
URL: http://localhost:5050
Email: admin@gatcha.local
Password: admin

Configuration du serveur:
  Host: postgres
  Port: 5432
  Database: gatcha_db
  Username: gatcha_user
  Password: gatcha_password
```

### Via CLI (psql)
```bash
# Depuis le host
docker exec -it gatcha_postgres psql -U gatcha_user -d gatcha_db

# Ou avec make
make db-shell
```

## 📊 Requêtes Utiles

### Statistiques Générales

```sql
-- Nombre total de monstres
SELECT COUNT(*) FROM monsters;

-- Nombre par état
SELECT state, COUNT(*) as count
FROM monsters
GROUP BY state
ORDER BY count DESC;

-- Monstres récents
SELECT monster_id, 
       monster_data->>'nom' as nom,
       monster_data->>'element' as element,
       state, created_at
FROM monsters
ORDER BY created_at DESC
LIMIT 10;

-- Taux de validation
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as valid,
  ROUND(100.0 * SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM monsters;
```

### Recherches

```sql
-- Chercher par nom
SELECT monster_id, monster_data->>'nom' as nom, state
FROM monsters
WHERE monster_data->>'nom' ILIKE '%dragon%';

-- Chercher par élément
SELECT monster_id, monster_data->>'nom' as nom
FROM monsters
WHERE monster_data->>'element' = 'FIRE';

-- Chercher par rang
SELECT monster_id, monster_data->>'nom' as nom, monster_data->>'rang' as rang
FROM monsters
WHERE monster_data->>'rang' = 'LEGENDARY'
ORDER BY created_at DESC;

-- Monstres générés par un prompt spécifique
SELECT monster_id, monster_data->>'nom' as nom, generation_prompt
FROM monsters
WHERE generation_prompt ILIKE '%cyberpunk%';
```

### Historique et Transitions

```sql
-- Historique complet d'un monstre
SELECT 
  m.monster_id,
  m.monster_data->>'nom' as nom,
  st.from_state,
  st.to_state,
  st.timestamp,
  st.actor,
  st.note
FROM monsters m
JOIN state_transitions st ON m.id = st.monster_db_id
WHERE m.monster_id = 'YOUR_MONSTER_ID_HERE'
ORDER BY st.timestamp;

-- Transitions récentes (tous monstres)
SELECT 
  m.monster_id,
  m.monster_data->>'nom' as nom,
  st.from_state,
  st.to_state,
  st.timestamp,
  st.actor
FROM state_transitions st
JOIN monsters m ON st.monster_db_id = m.id
ORDER BY st.timestamp DESC
LIMIT 20;

-- Nombre de transitions par monstre
SELECT 
  m.monster_id,
  m.monster_data->>'nom' as nom,
  COUNT(st.id) as nb_transitions
FROM monsters m
LEFT JOIN state_transitions st ON m.id = st.monster_db_id
GROUP BY m.monster_id, m.monster_data
ORDER BY nb_transitions DESC
LIMIT 10;
```

### Validation et Erreurs

```sql
-- Monstres avec erreurs de validation
SELECT 
  monster_id,
  monster_data->>'nom' as nom,
  state,
  validation_errors
FROM monsters
WHERE is_valid = false
ORDER BY updated_at DESC;

-- Types d'erreurs les plus fréquentes
SELECT 
  jsonb_array_elements(validation_errors::jsonb)->>'error_type' as error_type,
  COUNT(*) as count
FROM monsters
WHERE validation_errors IS NOT NULL
GROUP BY error_type
ORDER BY count DESC;
```

### Transmission

```sql
-- Monstres transmis
SELECT 
  monster_id,
  monster_data->>'nom' as nom,
  transmitted_at,
  invocation_api_id,
  transmission_attempts
FROM monsters
WHERE state = 'TRANSMITTED'
ORDER BY transmitted_at DESC;

-- Échecs de transmission
SELECT 
  monster_id,
  monster_data->>'nom' as nom,
  transmission_attempts,
  last_transmission_error
FROM monsters
WHERE transmission_attempts > 0 AND state != 'TRANSMITTED'
ORDER BY transmission_attempts DESC;

-- Taux de réussite transmission
SELECT 
  COUNT(*) FILTER (WHERE state = 'TRANSMITTED') as transmitted,
  COUNT(*) FILTER (WHERE transmission_attempts > 0 AND state != 'TRANSMITTED') as failed,
  ROUND(100.0 * COUNT(*) FILTER (WHERE state = 'TRANSMITTED') / 
    NULLIF(COUNT(*) FILTER (WHERE transmission_attempts > 0), 0), 2) as success_rate
FROM monsters;
```

### Analytics

```sql
-- Distribution par élément
SELECT 
  monster_data->>'element' as element,
  COUNT(*) as count
FROM monsters
GROUP BY monster_data->>'element'
ORDER BY count DESC;

-- Distribution par rang
SELECT 
  monster_data->>'rang' as rang,
  COUNT(*) as count
FROM monsters
GROUP BY monster_data->>'rang'
ORDER BY count DESC;

-- Monstres créés par jour (7 derniers jours)
SELECT 
  DATE(created_at) as day,
  COUNT(*) as monsters_created
FROM monsters
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY day DESC;

-- Temps moyen entre états
SELECT 
  AVG(EXTRACT(EPOCH FROM (transmitted_at - created_at))/3600) as hours_to_transmit
FROM monsters
WHERE transmitted_at IS NOT NULL;
```

### Review

```sql
-- Monstres en attente de review
SELECT 
  monster_id,
  monster_data->>'nom' as nom,
  state,
  created_at,
  EXTRACT(EPOCH FROM (NOW() - created_at))/3600 as hours_waiting
FROM monsters
WHERE state = 'PENDING_REVIEW'
ORDER BY created_at;

-- Reviews par admin
SELECT 
  reviewed_by,
  COUNT(*) as nb_reviews,
  COUNT(*) FILTER (WHERE state = 'APPROVED') as approved,
  COUNT(*) FILTER (WHERE state = 'REJECTED') as rejected
FROM monsters
WHERE reviewed_by IS NOT NULL
GROUP BY reviewed_by;
```

## 🛠️ Maintenance

### Informations sur la base

```sql
-- Taille de la base
SELECT pg_size_pretty(pg_database_size('gatcha_db'));

-- Taille de chaque table
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Nombre d'enregistrements par table
SELECT 
  'monsters' as table_name, 
  COUNT(*) as row_count 
FROM monsters
UNION ALL
SELECT 
  'state_transitions' as table_name, 
  COUNT(*) as row_count 
FROM state_transitions;
```

### Index et Performance

```sql
-- Lister les index
SELECT 
  tablename, 
  indexname, 
  indexdef 
FROM pg_indexes 
WHERE schemaname = 'public';

-- Statistiques des requêtes lentes (si pg_stat_statements activé)
-- SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

### Vacuum et Analyze

```sql
-- Nettoyer et optimiser
VACUUM ANALYZE monsters;
VACUUM ANALYZE state_transitions;
```

## 📦 Backup & Restore

```bash
# Backup
make db-backup
# ou
docker exec gatcha_postgres pg_dump -U gatcha_user gatcha_db > backup.sql

# Restore
make db-restore FILE=backup.sql
# ou
docker exec -i gatcha_postgres psql -U gatcha_user gatcha_db < backup.sql

# Backup avec compression
docker exec gatcha_postgres pg_dump -U gatcha_user gatcha_db | gzip > backup.sql.gz

# Restore depuis backup compressé
gunzip -c backup.sql.gz | docker exec -i gatcha_postgres psql -U gatcha_user gatcha_db
```

## 🔧 Commandes psql Utiles

```sql
\dt              -- Lister les tables
\d monsters      -- Décrire la structure de la table monsters
\d+ monsters     -- Description détaillée avec taille
\di              -- Lister les index
\l               -- Lister les bases de données
\du              -- Lister les utilisateurs
\x               -- Toggle mode étendu (meilleur pour lire les JSONs)
\q               -- Quitter
\timing          -- Afficher le temps d'exécution des requêtes
\e               -- Ouvrir l'éditeur pour écrire une requête longue
```

## 💡 Astuces

### JSON dans PostgreSQL

```sql
-- Accéder à un champ JSON (retourne JSON)
SELECT monster_data->'nom' FROM monsters LIMIT 1;

-- Accéder à un champ JSON (retourne TEXT)
SELECT monster_data->>'nom' FROM monsters LIMIT 1;

-- Accéder à un champ imbriqué
SELECT monster_data->'stats'->>'hp' FROM monsters LIMIT 1;

-- Chercher dans un array JSON
SELECT * FROM monsters 
WHERE monster_data @> '{"element": "FIRE"}';

-- Compter les skills
SELECT 
  monster_id,
  monster_data->>'nom' as nom,
  jsonb_array_length(monster_data->'skills') as nb_skills
FROM monsters;
```

### Mode Transaction Manuel

```sql
BEGIN;
  UPDATE monsters SET state = 'APPROVED' WHERE monster_id = 'abc123';
  INSERT INTO state_transitions (...) VALUES (...);
COMMIT;
-- ou ROLLBACK; si erreur
```

## 🚨 Troubleshooting

```sql
-- Connexions actives
SELECT * FROM pg_stat_activity WHERE datname = 'gatcha_db';

-- Tuer une connexion bloquante
SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
WHERE datname = 'gatcha_db' AND pid <> pg_backend_pid();

-- Locks actifs
SELECT * FROM pg_locks WHERE NOT granted;
```
