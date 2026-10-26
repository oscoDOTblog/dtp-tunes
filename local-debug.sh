#!/usr/bin/env bash
set -euo pipefail

readonly PROJECT_NAME="dtp-tunes-local"
readonly LOCAL_VOLUME="dtp-tunes-local-mongodb-data"
readonly MONGO_TARGET="mongodb://mongodb:27017/DTP_local (collections: tunes_*)"
readonly -a COMPOSE=(
  docker compose
  --project-name "${PROJECT_NAME}"
  --profile bundled-db
  --file docker-compose.yml
  --file docker-compose.local.yml
)

usage() {
  cat <<'EOF'
Usage: ./local-debug.sh <up|down|reset|config> [options]

  up [options]  Start the isolated local stack (options are passed to Compose).
  down          Stop the local stack and preserve its database.
  reset [--yes] Stop the stack and permanently remove only its local Mongo volume.
  config        Print the fully resolved local Compose configuration.
EOF
}

require_project_root() {
  if [[ ! -f docker-compose.yml || ! -f docker-compose.local.yml ]]; then
    echo "Run this script from the dtp-tunes project directory." >&2
    exit 1
  fi
}

print_target() {
  echo "Local debug MongoDB: ${MONGO_TARGET}"
  echo "Compose project: ${PROJECT_NAME}"
  echo "Mongo volume: ${LOCAL_VOLUME}"
}

require_project_root
command="${1:-}"
if [[ -z "${command}" ]]; then
  usage
  exit 2
fi
shift

case "${command}" in
  up)
    print_target
    "${COMPOSE[@]}" run --rm --build config-check
    "${COMPOSE[@]}" up --build "$@"
    ;;
  down)
    print_target
    "${COMPOSE[@]}" down "$@"
    ;;
  config)
    print_target
    "${COMPOSE[@]}" config "$@"
    ;;
  reset)
    assume_yes=false
    if [[ "${1:-}" == "--yes" ]]; then
      assume_yes=true
      shift
    fi
    if [[ $# -ne 0 ]]; then
      usage
      exit 2
    fi
    print_target
    if [[ "${assume_yes}" != true ]]; then
      read -r -p "Delete local MongoDB volume ${LOCAL_VOLUME}? [y/N] " answer
      if [[ ! "${answer}" =~ ^[Yy]$ ]]; then
        echo "Reset cancelled."
        exit 0
      fi
    fi
    "${COMPOSE[@]}" down
    if docker volume inspect "${LOCAL_VOLUME}" >/dev/null 2>&1; then
      docker volume rm "${LOCAL_VOLUME}"
      echo "Removed ${LOCAL_VOLUME}."
    else
      echo "Local MongoDB volume does not exist; nothing to remove."
    fi
    ;;
  *)
    usage
    exit 2
    ;;
esac
