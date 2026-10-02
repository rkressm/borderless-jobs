"""Audit all locked groups against OSV and fail closed on unknown results."""

from __future__ import annotations

import json
import subprocess
from typing import Any


def audit_errors(report: dict[str, Any]) -> list[str]:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return ["Missing audit summary"]
    errors: list[str] = []
    for key in ("vulnerabilities", "adverse_statuses"):
        count = summary.get(key)
        if not isinstance(count, int) or count < 0:
            errors.append(f"Invalid audit count: {key}")
        elif count:
            errors.append(f"Audit found {count} {key}")
    if not isinstance(summary.get("audited_packages"), int):
        errors.append("Missing audited package count")
    return errors


def main() -> None:
    result = subprocess.run(
        ["uv", "audit", "--locked", "--output-format", "json"],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise SystemExit("Audit failed or returned unreadable JSON") from None
    if not isinstance(report, dict):
        raise SystemExit("Audit returned an unexpected document")
    errors = audit_errors(report)
    if result.returncode != 0 or errors:
        raise SystemExit("\n".join(errors) or "Audit command failed")
    print(f"OSV audit: {report['summary']['audited_packages']} packages, no findings")


if __name__ == "__main__":
    main()
