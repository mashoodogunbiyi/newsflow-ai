#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

project_name="${NFA84_COMPOSE_PROJECT:-newsflow-nfa84-$$}"
frontend_port="${NFA84_FRONTEND_PORT:-43100}"
backend_port="${NFA84_BACKEND_PORT:-43101}"
postgres_port="${NFA84_POSTGRES_PORT:-43102}"
keep_environment="${NFA84_KEEP_ENVIRONMENT:-false}"
no_cache="${NFA84_NO_CACHE:-false}"

case "$project_name" in
  newsflow-nfa84-[A-Za-z0-9_-]*) ;;
  *)
    echo "NFA84_COMPOSE_PROJECT must start with newsflow-nfa84-." >&2
    exit 2
    ;;
esac

export APP_ENV=development
export BACKEND_PORT="$backend_port"
export FRONTEND_ORIGIN="http://localhost:$frontend_port"
export FRONTEND_PORT="$frontend_port"
export NEWS_SOURCE_MODE=fixture
export NEXT_PUBLIC_API_BASE_URL="http://localhost:$backend_port"
export POSTGRES_DB=newsflow_nfa84_test
export POSTGRES_PASSWORD=nfa84_test_password
export POSTGRES_PORT="$postgres_port"
export POSTGRES_USER=nfa84_test

compose() {
  docker compose --project-name "$project_name" --env-file /dev/null "$@"
}

cleanup() {
  if [ "$keep_environment" = "true" ]; then
    echo "Keeping isolated Compose project $project_name for inspection."
    return
  fi

  compose down --volumes --remove-orphans --rmi local >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

echo "Checking that required PostgreSQL settings fail closed..."
if env -u POSTGRES_DB -u POSTGRES_PASSWORD -u POSTGRES_USER \
  docker compose --project-name "$project_name" --env-file /dev/null config --quiet \
  >/dev/null 2>&1; then
  echo "Compose unexpectedly accepted missing PostgreSQL configuration." >&2
  exit 1
fi

echo "Validating the resolved Compose model without printing secrets..."
compose config --quiet

echo "Building the backend and frontend images..."
if [ "$no_cache" = "true" ]; then
  compose build --pull --no-cache
else
  compose build --pull
fi

echo "Starting the isolated application and waiting for health checks..."
compose up --detach --wait --wait-timeout 240

curl --fail --silent --show-error "http://127.0.0.1:$backend_port/health" >/dev/null
curl --fail --silent --show-error "http://127.0.0.1:$backend_port/ready" >/dev/null
curl --fail --silent --show-error "http://127.0.0.1:$frontend_port/login" >/dev/null

echo "Checking migrations and non-root application users..."
compose exec -T backend alembic current
test "$(compose exec -T backend id -u | tr -d '\r')" != "0"
test "$(compose exec -T frontend id -u | tr -d '\r')" != "0"

echo "Creating an isolated persistence marker..."
compose exec -T database sh -c \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE TABLE IF NOT EXISTS nfa84_packaging_probe (id integer PRIMARY KEY, value text NOT NULL); INSERT INTO nfa84_packaging_probe (id, value) VALUES (1, '\''persisted'\'') ON CONFLICT (id) DO UPDATE SET value = EXCLUDED.value;"' \
  >/dev/null

echo "Restarting PostgreSQL and verifying the marker survives..."
compose restart database
compose up --detach --wait --wait-timeout 240
test "$(compose exec -T database sh -c 'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT value FROM nfa84_packaging_probe WHERE id = 1;"' | tr -d '\r')" = "persisted"

echo "Restarting application containers and rechecking health..."
compose restart backend frontend
compose up --detach --wait --wait-timeout 240
curl --fail --silent --show-error "http://127.0.0.1:$backend_port/ready" >/dev/null
curl --fail --silent --show-error "http://127.0.0.1:$frontend_port/login" >/dev/null

echo "Testing a clean stop and start without deleting volumes..."
compose stop frontend backend database
compose start database
compose up --detach --wait --wait-timeout 240
test "$(compose exec -T database sh -c 'psql -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT value FROM nfa84_packaging_probe WHERE id = 1;"' | tr -d '\r')" = "persisted"
curl --fail --silent --show-error "http://127.0.0.1:$backend_port/ready" >/dev/null
curl --fail --silent --show-error "http://127.0.0.1:$frontend_port/login" >/dev/null

echo "Built image summary:"
compose images

echo "NFA-84 Docker packaging verification passed."
