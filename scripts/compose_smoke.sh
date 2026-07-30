#!/usr/bin/env bash
# Compose smoke test for CI. Requires Docker. Uses synthetic secrets only.
set -euo pipefail

PROJECT="${COMPOSE_PROJECT_NAME:-exceler-ci}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
STATUS=0

mkdir -p secrets
printf 'ci-smoke-password\n' > secrets/db_password

cleanup() {
  STATUS=$?
  if [[ "$STATUS" -ne 0 ]]; then
    echo "---- compose diagnostics ----"
    docker compose -p "$PROJECT" ps || true
    docker compose -p "$PROJECT" logs --no-color exceler-app exceler-db || true
  fi
  docker compose -p "$PROJECT" down -v --remove-orphans || true
  exit "$STATUS"
}
trap cleanup EXIT

docker compose -p "$PROJECT" build
docker compose -p "$PROJECT" up -d

echo "Waiting for readiness..."
ready=0
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${EXCELER_HTTP_PORT:-8000}/health/ready" >/dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "Service did not become ready in time"
  exit 1
fi

curl -fsS "http://127.0.0.1:${EXCELER_HTTP_PORT:-8000}/health/live" | tee /tmp/exceler-live.json
curl -fsS "http://127.0.0.1:${EXCELER_HTTP_PORT:-8000}/health/ready" | tee /tmp/exceler-ready.json

docker compose -p "$PROJECT" exec -T exceler-app exceler db upgrade

CREATE_PAYLOAD='{"name":"ci-samples","root_location":"/sources/samples","read_only":true}'
curl -fsS -X POST "http://127.0.0.1:${EXCELER_HTTP_PORT:-8000}/api/v1/sources" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD" | tee /tmp/exceler-source.json

SOURCE_ID="$(python -c "import json; print(json.load(open('/tmp/exceler-source.json'))['id'])")"
curl -fsS -X POST "http://127.0.0.1:${EXCELER_HTTP_PORT:-8000}/api/v1/sources/${SOURCE_ID}/validate" \
  | tee /tmp/exceler-validate.json

echo "Compose smoke test passed."
