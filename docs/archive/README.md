# Archive

Documents historiques : plans/checklists d'implémentations déjà terminées
(migration PostgreSQL, système de cycle de vie), audits datés dont les
constats (auth absente, StateManager partiel...) sont résolus depuis, ou
guides décrivant une architecture remplacée (stockage JSON pur, scripts
`setup_postgres.sh` supprimés).

Gardés pour l'historique, mais à ne pas utiliser comme documentation
courante — voir `docs/` (racine) pour ce qui est à jour, et `CLAUDE.md` à
la racine du service pour la vue d'ensemble actuelle.

`FRONTEND_API_GATCHA.md` est ici pour une raison différente : ses routes
sont toujours correctes, mais il ne mentionne pas l'authentification
Bearer/`X-Internal-Api-Key` devenue obligatoire sur `/monsters/generate*`
— un front qui le suit à la lettre se prend un 401. Archivé pour éviter
de le confondre avec de la doc à jour plutôt que pour son contenu propre.
