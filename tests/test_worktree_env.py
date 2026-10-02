"""Resource naming must stay deterministic across independent checkouts."""

import re
from pathlib import Path

import pytest

from scripts.worktree_env import resource_values, write_env


def test_resource_values_are_stable_safe_and_distinct() -> None:
    first = resource_values(Path("/tmp/borderless jobs!?/alpha"))
    second = resource_values(Path("/tmp/borderless jobs!?/beta"))

    assert first == resource_values(Path("/tmp/borderless jobs!?/alpha"))
    assert first["WORKTREE_ID"] != second["WORKTREE_ID"]
    assert first["COMPOSE_PROJECT_NAME"] != second["COMPOSE_PROJECT_NAME"]
    assert first["POSTGRES_DB"] != second["POSTGRES_DB"]
    assert first["POSTGRES_TEST_DB"] != second["POSTGRES_TEST_DB"]
    assert all(re.fullmatch(r"[a-zA-Z0-9_./-]+", value) for value in first.values())
    assert 20000 <= int(first["POSTGRES_PORT"]) < 40000
    assert 40000 <= int(first["POSTGRES_TEST_PORT"]) < 60000
    assert all(not value.startswith("/") for value in first.values())


def test_long_punctuated_names_remain_bounded_and_unique() -> None:
    prefix = "a!?" * 100
    first = resource_values(Path("/tmp") / f"{prefix}-one")
    second = resource_values(Path("/tmp") / f"{prefix}-two")

    assert len(first["WORKTREE_ID"]) <= 33
    assert first["WORKTREE_ID"] != second["WORKTREE_ID"]
    assert re.fullmatch(r"[a-z0-9-]+", first["WORKTREE_ID"])


def test_generated_environment_is_local_and_repeatable(tmp_path: Path) -> None:
    output = write_env(tmp_path)
    first = (tmp_path / output).read_text(encoding="utf-8")

    assert output.parts[0] == ".worktree"
    assert write_env(tmp_path) == output
    assert (tmp_path / output).read_text(encoding="utf-8") == first
    assert "POSTGRES_PASSWORD=" in first
    assert "POSTGRES_TEST_PASSWORD=" in first
    assert (tmp_path / output).stat().st_mode & 0o777 == 0o600
    assert (tmp_path / resource_values(tmp_path)["WORKTREE_CACHE_DIR"]).is_dir()
    assert (tmp_path / resource_values(tmp_path)["WORKTREE_ARTIFACTS_DIR"]).is_dir()


def test_rotating_test_password_preserves_development_password(tmp_path: Path) -> None:
    output = write_env(tmp_path)
    before = dict(
        line.split("=", 1)
        for line in (tmp_path / output).read_text(encoding="utf-8").splitlines()
    )
    write_env(tmp_path, rotate_test_password=True)
    after = dict(
        line.split("=", 1)
        for line in (tmp_path / output).read_text(encoding="utf-8").splitlines()
    )

    assert after["POSTGRES_PASSWORD"] == before["POSTGRES_PASSWORD"]
    assert after["POSTGRES_TEST_PASSWORD"] != before["POSTGRES_TEST_PASSWORD"]


def test_symlinked_environment_file_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / ".worktree" / resource_values(tmp_path)["WORKTREE_ID"]
    target.mkdir(parents=True)
    (target / "compose.env").symlink_to(tmp_path / "elsewhere")

    with pytest.raises(ValueError, match="symlinked"):
        write_env(tmp_path)
