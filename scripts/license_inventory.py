"""Inventory every locked registry package and reject unknown licenses."""

from __future__ import annotations

import json
import tomllib
from importlib import metadata
from pathlib import Path
from typing import Any

from scripts.worktree_env import ROOT, resource_values

ALLOWED_LICENSES = {
    "Apache-2.0",
    "Apache-2.0 OR BSD-2-Clause",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "LGPL-3.0-only",
    "MIT",
    "MPL-2.0",
    "PSF-2.0",
}

# Platform-specific locked packages are absent on the verified Linux host.
# Recheck these exact-version records whenever the lockfile changes.
LICENSE_OVERRIDES = {
    ("colorama", "0.4.6"): "BSD-3-Clause",  # github.com/tartley/colorama
    ("tzdata", "2026.4"): "Apache-2.0",  # pypi.org/project/tzdata/2026.4
}


def license_for(name: str, version: str) -> tuple[str, str]:
    try:
        distribution = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        override = LICENSE_OVERRIDES.get((name, version))
        return (override, "reviewed platform override") if override else ("", "missing")
    if distribution.version != version:
        return "", "installed version differs from lockfile"
    details = distribution.metadata
    expression = details.get("License-Expression") or details.get("License")
    if expression:
        return expression, "installed metadata"
    classifiers = details.get_all("Classifier", [])
    if "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)" in classifiers:
        return "MPL-2.0", "installed classifier"
    return "", "missing"


def inventory(lockfile: Path) -> list[dict[str, str]]:
    with lockfile.open("rb") as stream:
        locked: dict[str, Any] = tomllib.load(stream)
    records: list[dict[str, str]] = []
    for package in locked["package"]:
        if "registry" not in package["source"]:
            continue
        name, version = package["name"], package["version"]
        expression, source = license_for(name, version)
        records.append(
            {"name": name, "version": version, "license": expression, "source": source}
        )
    return sorted(records, key=lambda record: record["name"])


def invalid_records(records: list[dict[str, str]]) -> list[str]:
    return [
        f"{record['name']}=={record['version']}: {record['license'] or 'unknown'}"
        for record in records
        if record["license"] not in ALLOWED_LICENSES
    ]


def main() -> None:
    records = inventory(ROOT / "uv.lock")
    invalid = invalid_records(records)
    if invalid:
        raise SystemExit("Unreviewed dependency licenses:\n" + "\n".join(invalid))
    output = (
        ROOT
        / resource_values(ROOT)["WORKTREE_ARTIFACTS_DIR"]
        / "license-inventory.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(
        f"License inventory: {len(records)} reviewed packages; {output.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
