# Changements API — Gestion du cycle de vie des monstres

Date: 2026-02-25

Ce document décrit les modifications récentes de l'API de gestion des monstres et explique la nouvelle utilisation des routes pour l'équipe frontend.

**Résumé rapide**

- Les routes de review et correct ne prennent plus de `corrected_data`.
- Ajout d'une route dédiée pour modifier les propriétés d'un monstre: `POST /monsters/{monster_id}/update`.
- Ajout d'une route dédiée pour rejeter un monstre: `POST /monsters/{monster_id}/reject`.
- `review` et `correct` renvoient une erreur si les données actuelles du monstre ne sont pas valides.
- La modification d'un monstre (`/update`) enregistre désormais une entrée dans l'historique (`history`).

**Principes métier importants**

- Seules certaines routes peuvent modifier l'état d'un monstre ; d'autres se contentent de marquer une transition.
- Un monstre peut être modifié (via `/update`) seulement s'il est dans l'un des états : `GENERATED`, `PENDING_REVIEW`, `DEFECTIVE`.
- Lors d'une modification, les données soumises sont validées par le backend. Si elles ne sont pas valides, la requête est refusée sauf si `skip_validation=true` est envoyé.
- Après une modification réussie, une entrée est ajoutée au champ `metadata.history` et persistée en base.

---

## Routes modifiées / supprimées

### POST /monsters/{monster_id}/review
- Payload: `ReviewRequest` (sans `corrected_data`)
- Comportement: accepte `action` (`APPROVE` ou `REJECT`) et `notes`.
- Condition: le monstre doit être en état `PENDING_REVIEW` ET ses données actuelles doivent être valides.
- Erreurs possibles:
  - 400 si l'état n'est pas `PENDING_REVIEW`.
  - 400 si les données actuelles ne sont pas valides (message: "Cannot review monster: current data is not valid...").

Exemple de requête:

```json
{
  "action": "APPROVE",
  "notes": "Bonne qualité",
  "admin_name": "alice"
}
```

Réponse attendue (succès): 200 JSON contenant `monster_id` et `new_state`.

### POST /monsters/{monster_id}/correct
- Payload: `CorrectionRequest` (sans `corrected_data`).
- Comportement: marque le monstre défectueux comme corrigé **si les données actuelles sont valides**.
- Condition: le monstre doit être en état `DEFECTIVE` et les données actuelles doivent être valides.
- Si les données actuelles sont invalides, renvoyer 400 et indiquer les erreurs de validation.

Exemple de requête:

```json
{
  "notes": "Vérifié et OK",
  "admin_name": "bob"
}
```

---

## Nouvelles routes

### POST /monsters/{monster_id}/update
- Payload: `UpdateMonsterRequest`
  - `monster_data` (objet) — les nouvelles données du monstre (obligatoire)
  - `skip_validation` (bool, default: false) — si `true`, autorise la mise à jour même si la validation échoue
  - `notes` (optionnel)
  - `admin_name` (via RequestContext) — nom de l'admin
- États autorisés: `GENERATED`, `PENDING_REVIEW`, `DEFECTIVE`.
- Validation: le backend valide `monster_data`. Si invalide et `skip_validation=false`, la requête est rejetée (400) et renvoie le détail des erreurs.
- Effets secondaires:
  - Met à jour `monster.monster_data` et `metadata.is_valid` / `metadata.validation_errors`.
  - Ajoute une entrée dans `metadata.history` décrivant la modification (timestamp, actor, note).
  - Persiste la transition en base via `save_transition`.

Exemples:

Requête (validation stricte):

```json
{
  "monster_data": { "nom": "Garcho", "lvl": 10, "stats": {...} },
  "skip_validation": false,
  "notes": "Correction de stats",
  "admin_name": "carol"
}
```

Requête (forcer malgré l'invalidité):

```json
{
  "monster_data": { "nom": "Garcho", "lvl": 999, "stats": {...} },
  "skip_validation": true,
  "notes": "Force update pour debug",
  "admin_name": "carol"
}
```

Réponses:
- 200: succès (JSON avec `state` et `is_valid`).
- 400: données invalides (quand `skip_validation=false`) — body contient erreurs de validation.

### POST /monsters/{monster_id}/reject
- Payload: `RejectMonsterRequest` (notes optionnelles, admin_name)
- États autorisés: `GENERATED`, `PENDING_REVIEW`, `DEFECTIVE`.
- Effet: transition immédiate vers `REJECTED`, avec enregistrement dans l'historique.

Exemple:

```json
{
  "notes": "Ne respecte pas les contraintes",
  "admin_name": "dave"
}
```

Réponses: 200 (succès) / 400 (état non autorisé) / 404 (monstre introuvable)

---

## Historique

- L'historique d'un monstre est accessible via `GET /monsters/{monster_id}/history`.
- Toute modification faite via `/update` ajoute une entrée `StateTransition` (même si l'état ne change pas). La transition enregistrée contient :
  - `from_state` et `to_state` (pour une mise à jour, les deux sont identiques),
  - `timestamp`,
  - `actor` (admin_name),
  - `note` (texte avec indication `valid` / `skip_validation`).

Frontend: affichez ces entrées dans le fil d'activité pour tracer les modifications.

---

## Notes d'intégration front

- Interface Review/Correct: retirer tout champ `corrected_data` des formulaires d'appel direct à `/review` et `/correct`.
- Avant d'appeler `/review` ou `/correct`, vérifier côté client si le backend accepte la review/correct (ex : appel de pré-validation via `GET /monsters/{id}` qui retourne `validation_report`).
- Proposer dans l'UI une étape « Modifier les données » (appelant `/update`) quand le `validation_report` indique des erreurs.
- Lors de l'appel à `/update`, afficher les erreurs de validation renvoyées par l'API et proposer de corriger ou bien d'utiliser l'option `forcer` (skip_validation) avec un avertissement clair.

---

## Exemples d'erreurs communes et codes HTTP

- 400 Bad Request : données invalides, état non autorisé, action invalide
- 404 Not Found : monstre introuvable
- 500 Internal Error : problème serveur

---

## Fichier(s) modifiés côté backend (référence)

- `app/schemas/admin.py` : schémas `UpdateMonsterRequest`, `RejectMonsterRequest`, suppression de `corrected_data` depuis `ReviewRequest` et `CorrectionRequest`.
- `app/services/admin_service.py` : nouvelles méthodes `update_monster_data`, `reject_monster`, modifications de `review_monster` et `correct_defective`.
- `app/api/v1/endpoints/admin.py` : nouvelles routes `/update` et `/reject`, modification des routes `/review` et `/correct`.

---

Si vous voulez, je peux aussi fournir des snippets TypeScript / Axios pour intégrer rapidement ces appels côté frontend.
