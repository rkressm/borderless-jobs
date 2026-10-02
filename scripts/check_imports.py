"""Enforce the permitted static dependency graph between Borderless modules."""

import argparse
import ast
import importlib.util
import sys
from pathlib import Path

MODULES = frozenset(
    {
        "catalog",
        "cli",
        "connectors",
        "domain",
        "eligibility",
        "extraction",
        "reporting",
        "search",
    }
)
ALLOWED_INTERNAL = {
    "domain": frozenset(),
    "eligibility": frozenset({"domain"}),
    "connectors": frozenset({"domain"}),
    "catalog": frozenset({"domain", "connectors"}),
    "extraction": frozenset({"domain", "catalog"}),
    "search": frozenset({"domain", "catalog", "eligibility", "extraction"}),
    "reporting": frozenset({"domain", "eligibility", "search"}),
    "cli": MODULES - {"cli"},
}
PURE_STDLIB = frozenset(
    {
        "collections",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "functools",
        "itertools",
        "math",
        "operator",
        "re",
        "statistics",
        "typing",
    }
)


def check_source(source: str, owner: str, location: str) -> list[str]:
    """Find forbidden imports in one module without executing its contents."""
    tree = ast.parse(source, filename=location)
    violations: list[str] = []
    package = f"borderless.{owner}"

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        targets: list[str] = []
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative = "." * node.level + (node.module or "")
                base = importlib.util.resolve_name(relative, package)
            else:
                base = node.module or ""
            if base == "borderless":
                targets = [f"borderless.{alias.name}" for alias in node.names]
            else:
                targets = [base]

        for target in targets:
            parts = target.split(".")
            if parts[0] == "borderless":
                if len(parts) < 2 or parts[1] not in MODULES:
                    violations.append(
                        f"{location}:{node.lineno}: unknown internal import {target}"
                    )
                elif parts[1] != owner and parts[1] not in ALLOWED_INTERNAL[owner]:
                    violations.append(
                        f"{location}:{node.lineno}: {owner} must not import {target}"
                    )
            elif owner in {"domain", "eligibility"} and parts[0] not in PURE_STDLIB:
                violations.append(
                    f"{location}:{node.lineno}: {owner} must not import {target}"
                )

    return violations


def check_repository(root: Path) -> list[str]:
    """Check every Python file in the owned package and adapter source trees."""
    violations: list[str] = []
    for base in (root / "apps", root / "packages"):
        for source_file in sorted(base.glob("*/src/borderless/**/*.py")):
            relative = source_file.relative_to(root)
            owner = source_file.parts[source_file.parts.index("borderless") + 1]
            if owner not in MODULES:
                violations.append(f"{relative}: unregistered Borderless module {owner}")
                continue
            violations.extend(
                check_source(
                    source_file.read_text(encoding="utf-8"), owner, str(relative)
                )
            )
    return violations


def main() -> int:
    """Report violations with a nonzero exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    violations = check_repository(args.root)
    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1
    print("Architectural imports: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
