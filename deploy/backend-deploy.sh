#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/bounty-pool/app}"
BACKEND_DIR="${BACKEND_DIR:-$APP_DIR/backend}"
SERVICE_NAME="${SERVICE_NAME:-bounty-pool}"
BRANCH="${BRANCH:-master}"
LOCAL_HEALTH_URL="${LOCAL_HEALTH_URL:-http://127.0.0.1:8000/health}"
PUBLIC_HEALTH_URL="${PUBLIC_HEALTH_URL:-https://api.talentsignal.cloud/health}"

echo "== Backend deploy started =="
echo "App dir: $APP_DIR"
echo "Branch: $BRANCH"

cd "$APP_DIR"

git config --global --add safe.directory "$APP_DIR" >/dev/null 2>&1 || true

echo "== Current version =="
git status --short --branch
git rev-parse HEAD

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "ERROR: tracked files have local changes. Refusing to deploy."
  git status --short
  exit 1
fi

echo "== Pull latest code =="
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"
git rev-parse HEAD

echo "== Restart service =="
cd "$BACKEND_DIR"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager

echo "== Verify local health =="
for attempt in 1 2 3 4 5; do
  if curl -fsS "$LOCAL_HEALTH_URL"; then
    echo
    break
  fi
  if [ "$attempt" = "5" ]; then
    echo "ERROR: local health check failed."
    sudo journalctl -u "$SERVICE_NAME" -n 120 --no-pager
    exit 1
  fi
  sleep 2
done

echo "== Verify public health =="
curl -fsS "$PUBLIC_HEALTH_URL"
echo

echo "Backend deploy completed."
