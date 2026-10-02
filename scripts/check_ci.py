"""Check the repo's CI action pins and low-privilege invariants without deps."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/backend.yml"
SECURITY_WORKFLOW = ROOT / ".github/workflows/security.yml"
ALLOWED_ACTIONS = {
    "actions/checkout": "11bd71901bbe5b1630ceea73d27597364c9af683",
    "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/dependency-review-action": "2031cfc080254a8a887f58cffee85186f0e49e48",
    "actions/upload-artifact": "ea165f8d65b6e75b540449e92b4886f43607fa02",
}
COMMON_REQUIRED = (
    "permissions:\n  contents: read",
    "cancel-in-progress: true",
    "persist-credentials: false",
    "timeout-minutes:",
    "uv sync --locked --all-packages --all-groups",
)
BACKEND_REQUIRED = ("scripts/check-quality.sh all", "bash scripts/check-migrations.sh")
SECURITY_REQUIRED = (
    "actions/dependency-review-action@",
    "python3 -m scripts.check_secrets",
    "python -m scripts.check_vulnerabilities",
    "python -m scripts.license_inventory",
    "actions/upload-artifact@",
)


def validate_workflow(
    text: str, *, required: tuple[str, ...] = BACKEND_REQUIRED
) -> list[str]:
    errors: list[str] = []
    actions = re.findall(r"(?m)^\s*- uses:\s*(\S+)", text)
    if not actions:
        errors.append("No pinned actions found")
    for action in actions:
        name, separator, revision = action.partition("@")
        if not separator or ALLOWED_ACTIONS.get(name) != revision:
            errors.append(f"Unapproved action or pin: {action}")
    for marker in COMMON_REQUIRED + required:
        if marker not in text:
            errors.append(f"Missing CI invariant: {marker}")
    if "pull_request_target:" in text or "secrets." in text:
        errors.append("Privileged trigger or application secret reference")
    return errors


def validate_security_workflow(text: str) -> list[str]:
    return validate_workflow(text, required=SECURITY_REQUIRED)


def main() -> None:
    errors = validate_workflow(WORKFLOW.read_text(encoding="utf-8"))
    errors.extend(
        validate_security_workflow(SECURITY_WORKFLOW.read_text(encoding="utf-8"))
    )
    if errors:
        raise SystemExit("\n".join(errors))
    print("CI action pins and minimum-rights markers: OK")


if __name__ == "__main__":
    main()
