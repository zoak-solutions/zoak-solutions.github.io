#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${PREVIEW_IMAGE:-nginx:alpine}"

exec docker run --rm \
  --publish 127.0.0.1:8088:80 \
  --volume "${SCRIPT_DIR}:/usr/share/nginx/html:ro" \
  "${IMAGE}"
