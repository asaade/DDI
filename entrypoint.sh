#!/usr/bin/env sh
set -e

until psql "$DATABASE_URL" -c '\q' 2>/dev/null; do
  sleep 1
done > /dev/null

echo "✅ Postgres disponible. Ejecutando migraciones..."
psql "$DATABASE_URL" -f /usr/src/app/migration.sql > /dev/null

echo "✅ Migraciones completadas. Iniciando servidor DDI..."
exec uvicorn ddi.main:app --host 0.0.0.0 --port 8000
