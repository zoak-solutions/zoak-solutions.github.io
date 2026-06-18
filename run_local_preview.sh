#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${PREVIEW_IMAGE:-nginx:alpine}"
PREVIEW_PUBLISH="${PREVIEW_PUBLISH:-8088:80}"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-18080}"
DATA_DIR="${LUNCH_VOTE_DATA_DIR:-${TMPDIR:-/tmp}/zoak-lunch-vote-preview}"
NGINX_CONF="$(mktemp "${TMPDIR:-/tmp}/zoak-preview-nginx.XXXXXX.conf")"

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
    wait "${API_PID}" 2>/dev/null || true
  fi
  rm -f "${NGINX_CONF}"
}
trap cleanup EXIT INT TERM

mkdir -p "${DATA_DIR}"

export VOTE_DB_PATH="${VOTE_DB_PATH:-${DATA_DIR}/lunch-votes.sqlite}"
export VOTE_IP_HASH_SALT="${VOTE_IP_HASH_SALT:-local-preview-salt}"
export VOTE_DUPLICATE_WINDOW_SECONDS="${VOTE_DUPLICATE_WINDOW_SECONDS:-0}"
export VOTE_API_HOST="${API_HOST}"
export PORT="${API_PORT}"

python3 "${SCRIPT_DIR}/lunch-vote-api/server.py" &
API_PID="$!"

for _ in {1..50}; do
  if curl -fsS "http://${API_HOST}:${API_PORT}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

if ! curl -fsS "http://${API_HOST}:${API_PORT}/health" >/dev/null 2>&1; then
  echo "Lunch vote API did not start on ${API_HOST}:${API_PORT}" >&2
  exit 1
fi

cat > "${NGINX_CONF}" <<NGINX
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;

  location /api/ {
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_pass http://host.docker.internal:${API_PORT}/;
  }

  location / {
    try_files \$uri \$uri/ =404;
  }
}
NGINX

echo "Preview: http://localhost:8088/lunch-vote/"
echo "API:     http://localhost:8088/api/lunch-vote/results"

docker run --rm \
  --add-host host.docker.internal:host-gateway \
  --publish "${PREVIEW_PUBLISH}" \
  --volume "${SCRIPT_DIR}:/usr/share/nginx/html:ro" \
  --volume "${NGINX_CONF}:/etc/nginx/conf.d/default.conf:ro" \
  "${IMAGE}"
