"""Unknown and incompatible licenses block the inventory gate."""

from scripts.license_inventory import invalid_records, inventory
from scripts.worktree_env import ROOT


def test_safe_locked_inventory_passes() -> None:
    records = inventory(ROOT / "uv.lock")

    assert records
    assert invalid_records(records) == []


def test_unreviewed_license_is_rejected() -> None:
    records = [{"name": "synthetic", "version": "0", "license": "GPL-3.0-only"}]

    assert invalid_records(records) == ["synthetic==0: GPL-3.0-only"]
