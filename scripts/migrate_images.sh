#!/bin/bash

# Nom du service MinIO dans docker-compose
SERVICE_NAME="minio"
# Dossier local à copier
LOCAL_MINIO_DATA="minio_data"
# Dossier cible dans le volume Docker
DOCKER_TARGET="/data"

echo "Arrêt du service MinIO..."
docker-compose stop $SERVICE_NAME

# Récupère le nom du volume Docker associé à MinIO
VOLUME_NAME=$(docker volume ls --format '{{.Name}}' | grep minio_data)
if [ -z "$VOLUME_NAME" ]; then
  echo "Erreur : Volume Docker minio_data introuvable."
  exit 1
fi

echo "Volume Docker trouvé : $VOLUME_NAME"
echo "Copie des fichiers de $LOCAL_MINIO_DATA/ vers le volume Docker $VOLUME_NAME..."

# Utilise un conteneur temporaire pour copier les fichiers dans le volume
docker run --rm -v "$VOLUME_NAME:$DOCKER_TARGET" -v "$PWD/$LOCAL_MINIO_DATA":/from busybox sh -c "cp -r /from/. $DOCKER_TARGET/"

echo "Redémarrage du service MinIO..."
docker-compose start $SERVICE_NAME

echo "Transfert terminé."