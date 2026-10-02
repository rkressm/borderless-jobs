#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
script_path="$repo_root/scripts/check-quality.sh"
cd "$repo_root"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$repo_root/.cache/uv}"

run_tool() {
    uv run --locked --all-packages --group migration --offline "$@"
}

case "${1:-all}" in
    format)
        run_tool ruff format --check apps packages scripts migrations tests
        ;;
    lint)
        run_tool ruff check apps packages scripts migrations tests
        ;;
    type)
        run_tool mypy
        ;;
    test)
        run_tool python -m pytest
        ;;
    coverage)
        run_tool coverage run -m pytest
        run_tool coverage report
        ;;
    imports)
        run_tool python scripts/check_imports.py
        ;;
    ci)
        run_tool python scripts/check_ci.py
        ;;
    all)
        "$script_path" format
        "$script_path" lint
        "$script_path" type
        "$script_path" imports
        "$script_path" ci
        "$script_path" test
        "$script_path" coverage
        ;;
    *)
        echo "Usage: $0 {format|lint|type|imports|ci|test|coverage|all}" >&2
        exit 2
        ;;
esac
