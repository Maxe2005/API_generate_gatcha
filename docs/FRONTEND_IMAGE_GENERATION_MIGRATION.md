# Migration Frontend - Génération d'Images Personnalisées

## 📋 Vue d'ensemble

La génération d'images personnalisées a été **refactorisée pour utiliser Celery et WebSocket**, suivant le même pattern que la génération de monstres. Cela permet une meilleure expérience utilisateur avec suivi en temps réel et requêtes non-bloquantes.

---

## 🔄 Comparaison: Ancien vs Nouveau Flux

### ❌ Ancien Flux (Synchrone)
```
Client                    Backend
  │                          │
  ├─ POST /images/generate ──→│
  │                          │ (Attente ~ 10-30s)
  │                          │ Génération d'image...
  │                          │
  │← MonsterImageResponse ────┤
  │                          │
```
**Problèmes:**
- Requête bloquante (timeout possible)
- Pas de feedback en temps réel
- Mauvaise UX pendant la génération

### ✅ Nouveau Flux (Asynchrone avec WebSocket)
```
Client                    Backend              Redis
  │                          │                   │
  ├─ POST /images/generate ──→│                   │
  │                          │ Crée batch_id    │
  │←─ {batch_id} (202) ──────┤                   │
  │                          │                   │
  │ Subscribe au WebSocket   │                   │
  ├─ WS /images/ws/{batch_id}→│                   │
  │  (connexion établie)     │                   │
  │                          ├─ Lance Celery ───→│
  │                          │ task              │
  │← Message "Génération..." ←init message───────┤
  │                          │                   │
  │                          │ (En arrière-plan) │
  │                          │ Génération...     │
  │                          │                   │
  │← Message "Génération terminée" ──────────────┤
  │  (WebSocket fermé)       │                   │
```
**Avantages:**
- Requête non-bloquante (HTTP 202 Accepted)
- Feedback en temps réel via WebSocket
- Meilleure UX et scalabilité
- Même pattern que la génération de monstres

---

## 🔌 Endpoints API

### 1. POST `/api/v1/images/generate`

**Demande HTTP:**
```http
POST /api/v1/images/generate HTTP/1.1
Content-Type: application/json

{
  "monster_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_name": "Dragon Mode Evolution",
  "custom_prompt": "A fierce dragon with glowing purple eyes and ice crystals"
}
```

**Réponse (HTTP 202 Accepted):**
```json
{
  "batch_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

**Champs requis:**
- `monster_id` (string, UUID): ID du monstre cible
- `image_name` (string): Nom/description de l'image
- `custom_prompt` (string): Prompt personnalisé pour la génération

---

### 2. WebSocket `/api/v1/images/ws/{batch_id}`

**Connexion:**
```javascript
const batchId = "f47ac10b-58cc-4372-a567-0e02b2c3d479";
const ws = new WebSocket(`ws://localhost:8000/api/v1/images/ws/${batchId}`);
```

**Messages reçus:**

#### Message de complétion
```json
"Génération terminée"
```

#### Message d'info
```json
{
  "info": "Message informatif sur la progression..."
}
```

#### Message d'erreur
```json
{
  "error": "Description de l'erreur"
}
```

---

## 💻 Guide d'Implémentation Frontend

### Étape 1: Requête HTTP pour initier la génération

```javascript
async function startCustomImageGeneration(monsterId, imageName, customPrompt) {
  try {
    const response = await fetch('/api/v1/images/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        monster_id: monsterId,
        image_name: imageName,
        custom_prompt: customPrompt,
      }),
    });

    if (response.status !== 202) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }

    const data = await response.json();
    return data.batch_id; // Retourner le batch_id
  } catch (error) {
    console.error('Erreur lors du démarrage de la génération:', error);
    throw error;
  }
}
```

### Étape 2: Connexion WebSocket et suivi

```javascript
function trackImageGeneration(batchId, onProgress, onComplete, onError) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/images/ws/${batchId}`);

  ws.onopen = () => {
    console.log(`Connecté au WebSocket pour batch_id: ${batchId}`);
    onProgress?.({ status: 'Initialisation de la génération...' });
  };

  ws.onmessage = (event) => {
    const message = event.data;
    console.log('Message reçu:', message);

    if (message === 'Génération terminée') {
      onComplete?.({ success: true });
      ws.close();
    } else {
      // Parser et afficher les messages
      try {
        const data = JSON.parse(message);
        if (data.error) {
          onError?.({ error: data.error });
        } else if (data.info) {
          onProgress?.({ info: data.info });
        } else if (data.monster) {
          // Image générée avec succès
          onProgress?.({ image: JSON.parse(data.monster) });
        }
      } catch (e) {
        // Message texte brut
        onProgress?.({ status: message });
      }
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket erreur:', error);
    onError?.({ error: 'Erreur de connexion WebSocket' });
  };

  ws.onclose = () => {
    console.log('WebSocket fermé');
  };

  return ws;
}
```

### Étape 3: Intégration complète

```javascript
async function generateCustomImage(monsterId, imageName, customPrompt) {
  // UI: Afficher loading/spinner
  showLoadingSpinner(true);

  try {
    // 1. Initier la génération
    const batchId = await startCustomImageGeneration(
      monsterId,
      imageName,
      customPrompt
    );
    console.log('Génération initiée avec batch_id:', batchId);

    // 2. Tracker en temps réel
    return new Promise((resolve, reject) => {
      trackImageGeneration(
        batchId,
        (progress) => {
          // Mise à jour du UI avec la progression
          if (progress.status) {
            updateProgressMessage(progress.status);
          }
          if (progress.info) {
            updateProgressMessage(progress.info);
          }
          if (progress.image) {
            updateImagePreview(progress.image);
          }
        },
        (result) => {
          // Génération terminée
          showLoadingSpinner(false);
          showSuccessMessage('Image générée avec succès!');
          resolve(result);
        },
        (error) => {
          // Erreur durant la génération
          showLoadingSpinner(false);
          showErrorMessage(`Erreur: ${error.error}`);
          reject(error);
        }
      );
    });
  } catch (error) {
    showLoadingSpinner(false);
    showErrorMessage(`Erreur: ${error.message}`);
    throw error;
  }
}
```

---

## 🔧 Détails Techniques

### Architecture Celery + WebSocket

```
Frontend          FastAPI          Celery           Redis
   │                 │                 │               │
   ├─ POST generate ─→│                                │
   │                 ├─ Crée batch_id →│               │
   │                 │                 │               │
   │                 ←─ 202 + batch_id ┤               │
   │                 │                                 │
   │ ─ WS connect ──→│                                 │
   │                 │ (PubSub subscribe)             │
   │                 │                 │ Génère image  │
   │                 │                 │               │
   │                 │                 ├─ Publie ─────→│
   │                 │                    réultats     │
   │                 │              ←─ Subscribe ─────┤
   │                 │                                 │
   │←─ Message ──────┤←─ Publie ─────────────────────┤
   │                 │                                 │
```

### Codes HTTP

| Code | Signification | Détails |
|------|---------------|---------|
| **202** | Accepted | Requête acceptée, génération lancée |
| **404** | Not Found | Monstre avec cet ID n'existe pas |
| **500** | Server Error | Erreur serveur (Celery, Banana API, etc.) |

### Format des Messages Redis

Les messages publiés sur Redis suivent ce format:

```json
// Message de complétion
"Génération terminée"

// Message d'info
{"info": "Description du message"}

// Message d'erreur
{"error": "Description de l'erreur"}

// Image générée
{"monster": "{...données image JSON...}"}
```

---

## 📊 État vs Ancien Comportement

| Aspect | Ancien | Nouveau |
|--------|--------|---------|
| **Requête** | Synchrone (bloquante) | Asynchrone (202 Accepted) |
| **Suivi** | Aucun | WebSocket en temps réel |
| **Timeout** | Potentiel (30s+) | Pas de timeout (async) |
| **Pattern** | Unique | Cohérent avec `/generate` monstres |
| **Scalabilité** | Limitée | Excellente |

---

## ✅ Checklist de Migration

- [ ] Remplacer l'appel POST synchrone par le nouveau pattern asynchrone
- [ ] Implémenter la connexion WebSocket après la requête HTTP
- [ ] Gérer les 3 types de messages (completion, info, error)
- [ ] Ajouter UI/UX pour le suivi en temps réel (spinner, barre de progression)
- [ ] Tester les cas d'erreur (monstre non trouvé, timeout Banana, etc.)
- [ ] Fermer proprement la connexion WebSocket après complétion
- [ ] Mettre en cache le `batch_id` si nécessaire pour debug
- [ ] Implémenter retry logic si la WebSocket se ferme prématurément

---

## 🐛 Troubleshooting

### Le WebSocket se ferme immédiatement
- Vérifier que le `batch_id` est correct
- Vérifier que Redis est accessible depuis le backend
- Vérifier les logs du worker Celery

### Pas de messages reçus
- Vérifier que la tâche Celery est bien lancée
- Vérifier les chaines `batch:{batch_id}` dans Redis
- Vérifier la configuration Redis dans `app/core/config.py`

### La génération échoue
- Vérifier le message d'erreur reçu via WebSocket
- Vérifier les logs Celery: `docker-compose logs celery`
- Vérifier quota Banana API

---

## 📚 Références Additionnelles

- Voir [gatcha.py](../app/api/v1/endpoints/gatcha.py) pour un exemple d'implémentation similaire
- Voir [tasks.py](../app/services/tasks.py) pour les détails des tâches Celery
- Voir [send_messages_utils.py](../app/utils/send_messages_utils.py) pour les utilitaires Redis
