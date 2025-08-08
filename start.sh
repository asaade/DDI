#!/usr/bin/env sh
set -e

docker-compose down -v  # --rmi all # Detiene, elimina todo y borra imágenes
docker-compose build    # --no-cache  # Reconstruye desde cero, sin caché
docker-compose up -d    # Lanza los servicios
echo "Proceso iniciado..."
# (sleep 5s && curl -X POST "http://localhost:8000/api/v1/items/generate" -H "Content-Type: application/json" --data-binary @request_item.json)
