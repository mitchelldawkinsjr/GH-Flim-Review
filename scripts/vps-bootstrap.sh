#!/usr/bin/env bash
# One-time host prep for docker-compose.prod.yml (run on the VPS).
set -euo pipefail

NET="${DOCKER_NETWORK:-360ws-network}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/360ws/clients/docker-app}"
APP_DIR="${APP_DIR:-${DEPLOY_ROOT}/flim-review}"

if ! docker network inspect "$NET" >/dev/null 2>&1; then
  echo "Creating Docker network: $NET"
  docker network create "$NET"
else
  echo "Docker network exists: $NET"
fi

mkdir -p "$APP_DIR"
echo "Deploy directory ready: $APP_DIR"
echo ""
echo "Next: push to main (GitHub Actions deploys) or rsync + docker compose up manually."
