#!/usr/bin/env bash
# Update Hermes gateway to v0.16.0 (tag v2026.6.5 - The Surface Release) and restart

set -euo pipefail

HERMES_VERSION="v2026.6.5"

echo "==> Pulling Hermes Agent ${HERMES_VERSION}..."
docker compose pull

echo "==> Restarting gateway with new image..."
docker compose up -d --remove-orphans

echo "==> Waiting for gateway health check..."
for i in $(seq 1 12); do
  if docker compose exec gateway curl -sf http://localhost:8642/healthz > /dev/null 2>&1; then
    echo "==> Gateway is healthy."
    break
  fi
  echo "    Attempt ${i}/12 - not ready yet, waiting 5s..."
  sleep 5
done

echo "==> Gateway status:"
docker compose ps
