#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$repo_root/.cache/uv}"

cleanup() {
    bash scripts/db.sh test-down
}
trap cleanup EXIT

bash scripts/db.sh test-down
bash scripts/db.sh test-up
run_migration() {
    uv run --locked --all-packages --group migration --offline python -m scripts.migrate test "$@"
}
assert_revision() {
    uv run --locked --all-packages --group migration --offline python -m scripts.check_migration_state "$1"
}
assert_revision base
run_migration upgrade head
assert_revision 0001
run_migration downgrade base
assert_revision base
run_migration upgrade head
assert_revision 0001
