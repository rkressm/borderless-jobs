#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
env_file="$(python3 scripts/worktree_env.py)"

compose() {
    docker compose --env-file "$env_file" -f compose.yaml "$@"
}

case "${1:-}" in
    dev-up) compose --profile dev up -d --wait db ;;
    dev-down) compose --profile dev stop db ;;
    test-up) compose --profile test up -d --wait db-test ;;
    test-down) compose --profile test rm -s -f db-test ;;
    *)
        echo "Usage: $0 {dev-up|dev-down|test-up|test-down}" >&2
        exit 2
        ;;
esac
