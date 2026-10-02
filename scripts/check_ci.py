"""Check the repo's CI action pins and low-privilege invariants without deps."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/backend.yml"
ALLOWED_ACTIONS = {
    "actions/checkout": "11bd71901bbe5b1630ceea73d27597364c9af683",
    "actions/setup-python": "a26af69be951a213d495a4c3e4e4022e16d87065",
}


def validate_workflow(text: str) -> list[str]:
    errors: list[str] = []
    actions = re.findall(r"(?m)^\s*- uses:\s*(\S+)", text)
    if not actions:
        errors.append("No pinned actions found")
    for action in actions:
        name, separator, revision = action.partition("@")
        if not separator or ALLOWED_ACTIONS.get(name) != revision:
            errors.append(f"Unapproved action or pin: {action}")
    required = (
        "permissions:\n  contents: read",
        "cancel-in-progress: true",
        "persist-credentials: false",
        "timeout-minutes:",
        "uv sync --locked --all-packages --all-groups",
        "scripts/check-quality.sh all",
        "bash scripts/check-migrations.sh",
    )
    for marker in required:
        if marker not in text:
            errors.append(f"Missing CI invariant: {marker}")
    if "pull_request_target:" in text or "secrets." in text:
        errors.append("Privileged trigger or application secret reference")
    return errors


def main() -> None:
    errors = validate_workflow(WORKFLOW.read_text(encoding="utf-8"))
    if errors:
        raise SystemExit("\n".join(errors))
    print("CI action pins and minimum-rights markers: OK")


if __name__ == "__main__":
    main()
