#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${PREVIEW_IMAGE:-nginx:alpine}"

exec docker run --rm \
  --publish 8088:80 \
  --volume "${SCRIPT_DIR}:/usr/share/nginx/html:ro" \
  "${IMAGE}"
