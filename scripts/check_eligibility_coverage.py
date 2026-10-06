"""Fail when measured eligibility branch coverage is below 90 percent."""

import json
from pathlib import Path
from typing import Any

PREFIX = "packages/eligibility/src/borderless/eligibility/"


def branch_percentage(report: dict[str, Any]) -> float:
    files = [
        data["summary"]
        for path, data in report["files"].items()
        if path.startswith(PREFIX)
    ]
    total = sum(int(file["num_branches"]) for file in files)
    covered = sum(int(file["covered_branches"]) for file in files)
    if not files or total <= 0:
        raise ValueError("Missing eligibility branch coverage")
    percentage = 100 * covered / total
    if percentage < 90:
        raise ValueError(f"Eligibility branch coverage {percentage:.2f}% is below 90%")
    return percentage


def main() -> int:
    report = json.loads(Path(".coverage.eligibility.json").read_text(encoding="utf-8"))
    print(
        f"Eligibility branch coverage: {branch_percentage(report):.2f}% (minimum 90%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
