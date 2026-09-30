#!/bin/sh

set -eu

required_minor=3.12
python_command=${1:-python3}

if ! command -v "$python_command" >/dev/null 2>&1; then
    printf '%s\n' "Python executable not found: $python_command" >&2
    printf '%s\n' "Install the supported runtime with: uv python install $required_minor" >&2
    exit 1
fi

detected_minor=$("$python_command" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null) || {
    printf '%s\n' "Could not inspect Python executable: $python_command" >&2
    printf '%s\n' "Install the supported runtime with: uv python install $required_minor" >&2
    exit 1
}

if [ "$detected_minor" != "$required_minor" ]; then
    printf '%s\n' "Unsupported Python version from $python_command: $detected_minor (expected CPython $required_minor.x)." >&2
    printf '%s\n' "Install it with: uv python install $required_minor" >&2
    exit 1
fi

implementation=$("$python_command" -c 'import platform; print(platform.python_implementation())')
if [ "$implementation" != "CPython" ]; then
    printf '%s\n' "Unsupported Python implementation from $python_command: $implementation (expected CPython)." >&2
    exit 1
fi

full_version=$("$python_command" -c 'import platform; print(platform.python_version())')
printf '%s\n' "Supported runtime: CPython $full_version"
