"""Derive local resource names from the current checkout, without dependencies."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def resource_values(checkout: Path) -> dict[str, str]:
    """Return stable, shell-safe names for a checkout's local resources."""
    canonical = checkout.resolve()
    digest = hashlib.sha256(str(canonical).encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9]+", "-", canonical.name.lower()).strip("-")[:20]
    slug = slug.rstrip("-") or "worktree"
    identity = f"{slug}-{digest}"
    return {
        "WORKTREE_ID": identity,
        "COMPOSE_PROJECT_NAME": f"bj-{identity}",
        "POSTGRES_DB": f"bj_{digest}",
        "POSTGRES_PORT": str(20000 + int(digest[:8], 16) % 20000),
        "POSTGRES_TEST_DB": f"bj_test_{digest}",
        "POSTGRES_TEST_PORT": str(40000 + int(digest[:8], 16) % 20000),
        "WORKTREE_CACHE_DIR": f".cache/worktrees/{identity}",
        "WORKTREE_ARTIFACTS_DIR": f".artifacts/worktrees/{identity}",
    }


def write_env(checkout: Path, *, rotate_test_password: bool = False) -> Path:
    """Create per-worktree directories and a Compose-compatible environment file."""
    values = resource_values(checkout)
    root = checkout.resolve()
    output = Path(".worktree") / values["WORKTREE_ID"] / "compose.env"
    for relative in (
        output.parent,
        Path(values["WORKTREE_CACHE_DIR"]),
        Path(values["WORKTREE_ARTIFACTS_DIR"]),
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    target = root / output
    if target.is_symlink():
        raise ValueError("Refusing to overwrite a symlinked environment file")
    if target.exists():
        existing = dict(
            line.split("=", 1)
            for line in target.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
    else:
        existing = {}
    values["POSTGRES_PASSWORD"] = existing.get(
        "POSTGRES_PASSWORD", secrets.token_urlsafe(32)
    )
    values["POSTGRES_TEST_PASSWORD"] = (
        secrets.token_urlsafe(32)
        if rotate_test_password
        else existing.get("POSTGRES_TEST_PASSWORD", secrets.token_urlsafe(32))
    )
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.writelines(f"{key}={value}\n" for key, value in values.items())
    target.chmod(0o600)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print", action="store_true", help="print values without writing"
    )
    parser.add_argument(
        "--rotate-test-password",
        action="store_true",
        help="replace the disposable database password without printing it",
    )
    args = parser.parse_args()
    if args.print and args.rotate_test_password:
        parser.error("--print and --rotate-test-password are mutually exclusive")
    if args.print:
        for key, value in resource_values(ROOT).items():
            print(f"{key}={value}")
    else:
        print(write_env(ROOT, rotate_test_password=args.rotate_test_password))


if __name__ == "__main__":
    main()
