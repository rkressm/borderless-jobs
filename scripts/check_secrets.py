"""Fail on common committed credential shapes without echoing their values."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_FILE_BYTES = 2_000_000
PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"
    ),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "credential literal": re.compile(
        r"(?i)\b[A-Z_]*(?:SECRET[_-]?ACCESS[_-]?KEY|API[_-]?KEY|"
        r"ACCESS[_-]?TOKEN|PASSWORD|SECRET|"
        r"PRIVATE[_-]?KEY|DATABASE[_-]?URL)\s*[:=]\s*"
        r"[\"'][A-Za-z0-9_./+=-]{16,}[\"']"
    ),
}


def scan_text(source: str) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        for label, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append((line_number, label))
    return findings


def tracked_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [ROOT / name.decode("utf-8") for name in result.stdout.split(b"\0") if name]


def scan_repository() -> list[str]:
    findings: list[str] = []
    for path in tracked_paths():
        if path.is_symlink() or not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            findings.append(f"{path.relative_to(ROOT)}: file exceeds scan size limit")
            continue
        content = path.read_bytes()
        if b"\0" in content:
            continue
        for line_number, label in scan_text(content.decode("utf-8", errors="replace")):
            findings.append(f"{path.relative_to(ROOT)}:{line_number}: {label}")
    return findings


def main() -> None:
    findings = scan_repository()
    if findings:
        raise SystemExit("Potential secrets detected:\n" + "\n".join(findings))
    print("Tracked-file secret scan: OK")


if __name__ == "__main__":
    main()
