#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "Pulling latest changes..."
sudo git pull --ff-only

compose_files=(-f docker-compose.yml -f docker-compose.runtipi.yml)

echo "Stopping the dtp-tunes Compose stack..."
docker compose "${compose_files[@]}" down

echo "Checking required environment variables..."
docker compose "${compose_files[@]}" run --rm --build config-check

echo "Rebuilding and starting the dtp-tunes Compose stack..."
docker compose "${compose_files[@]}" up -d --build
