#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${PREVIEW_IMAGE:-nginx:alpine}"
PREVIEW_PUBLISH="${PREVIEW_PUBLISH:-8088:80}"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-18080}"
DATA_DIR="${LUNCH_VOTE_DATA_DIR:-${TMPDIR:-/tmp}/zoak-lunch-vote-preview}"
NGINX_CONF="$(mktemp "${TMPDIR:-/tmp}/zoak-preview-nginx.XXXXXX.conf")"

preview_host_port() {
  local publish="$1"
  local parts
  IFS=':' read -r -a parts <<< "${publish}"
  if [[ "${#parts[@]}" -eq 2 ]]; then
    printf '%s' "${parts[0]}"
  elif [[ "${#parts[@]}" -eq 3 ]]; then
    printf '%s' "${parts[1]}"
  else
    printf '8088'
  fi
}

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
    wait "${API_PID}" 2>/dev/null || true
  fi
  rm -f "${NGINX_CONF}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -p "${DATA_DIR}"

export VOTE_DB_PATH="${VOTE_DB_PATH:-${DATA_DIR}/lunch-votes.sqlite}"
export VOTE_IP_HASH_SALT="${VOTE_IP_HASH_SALT:-local-preview-salt}"
export VOTE_TOKEN_HASH_SALT="${VOTE_TOKEN_HASH_SALT:-local-preview-token-salt}"
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

  add_header Content-Security-Policy "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; frame-src 'none'; form-action 'self'; script-src 'self' 'sha256-9XvVduAvBsrOLhurWicDrxtJ+k5ectmF67IFI9cQes4=' 'sha256-I6oMfprt2s1c1m4ZT+6K6Y/DcaxmCeNrz46GTWGVuyk=' 'sha256-IPYAYfI8bvG+DTOWVdYnNQgjhxpPwdNElqPiqQUU9Mw='; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: https://raw.githubusercontent.com https://github.com https://avatars.githubusercontent.com; connect-src 'self' https://api.github.com https://rdap.org https://dns.google https://trace.dns.google https://ipapi.co" always;
  add_header X-Content-Type-Options "nosniff" always;
  add_header X-Frame-Options "DENY" always;
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header Referrer-Policy "strict-origin-when-cross-origin" always;
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;

  location /api/ {
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_pass http://zoak-host.docker.internal:${API_PORT}/;
  }

  location / {
    try_files \$uri \$uri/ =404;
  }
}
NGINX

PREVIEW_PORT="$(preview_host_port "$PREVIEW_PUBLISH")"
echo "Preview: http://localhost:${PREVIEW_PORT}/lunch-vote/"
echo "API:     http://localhost:${PREVIEW_PORT}/api/lunch-vote/results"

docker run --rm \
  --add-host zoak-host.docker.internal:host-gateway \
  --publish "${PREVIEW_PUBLISH}" \
  --volume "${SCRIPT_DIR}:/usr/share/nginx/html:ro" \
  --volume "${NGINX_CONF}:/etc/nginx/conf.d/default.conf:ro" \
  "${IMAGE}"
