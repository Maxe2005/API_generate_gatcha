# Guide d’utilisation des routes Gatcha pour le front-end

Ce guide explique comment utiliser les routes de génération de monstres (asynchrone) et le suivi en temps réel via WebSocket.

## 1. Génération d’un monstre

### Endpoint
`POST /api/v1/monsters/generate`

#### Payload
```json
{
  "prompt": "Décris ton monstre ici"
}
```

#### Réponse
```json
{
  "batch_id": "<uuid>"
}
```

## 2. Génération batch de monstres

### Endpoint
`POST /api/v1/monsters/generate-batch`

#### Payload
```json
{
  "n": 5,
  "prompt": "Décris le type de monstres à générer"
}
```

#### Réponse
```json
{
  "batch_id": "<uuid>"
}
```

## 3. Suivi en temps réel (WebSocket)

### Endpoint
`ws://<host>/api/v1/monsters/ws/{batch_id}`

- Connecte-toi au WebSocket avec le batch_id reçu.
- À chaque monstre généré, tu reçois un message JSON avec les infos du monstre.
- À la fin, tu reçois le message : `Génération terminée`.

### Exemple de flux côté front
```js
const ws = new WebSocket('ws://localhost:8000/api/v1/monsters/ws/<batch_id>');
ws.onmessage = (event) => {
  if (event.data === 'Génération terminée') {
    // Fin du batch
  } else {
    const monster = JSON.parse(event.data);
    // Affiche ou stocke le monstre
  }
};
```

## Résumé du workflow
1. POST pour lancer la génération (simple ou batch).
2. Récupère le batch_id.
3. Ouvre un WebSocket pour suivre l’avancement.
4. Notifie l'utilisateur à chaque monstre généré.
5. Ferme le WebSocket à la fin.
