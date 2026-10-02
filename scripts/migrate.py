"""Run a migration against the current worktree's local database."""

from __future__ import annotations

import argparse
import os

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL

from scripts.worktree_env import ROOT, write_env


def local_database_url(profile: str) -> str:
    env_file = ROOT / write_env(ROOT)
    values = dict(
        line.split("=", 1)
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    if profile == "test":
        user, prefix = "bj_test", "POSTGRES_TEST_"
    else:
        user, prefix = "bj_local", "POSTGRES_"
    return URL.create(
        "postgresql+psycopg",
        username=user,
        password=values[f"{prefix}PASSWORD"],
        host="127.0.0.1",
        port=int(values[f"{prefix}PORT"]),
        database=values[f"{prefix}DB"],
    ).render_as_string(hide_password=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=("dev", "test"))
    parser.add_argument("command", choices=("upgrade", "downgrade", "current"))
    parser.add_argument("revision", nargs="?")
    args = parser.parse_args()
    if args.command != "current" and args.revision is None:
        parser.error("upgrade and downgrade require a revision")
    if args.command == "current" and args.revision is not None:
        parser.error("current does not accept a revision")

    os.environ["BORDERLESS_DATABASE_URL"] = local_database_url(args.profile)
    config = Config(str(ROOT / "alembic.ini"))
    if args.command == "upgrade":
        command.upgrade(config, args.revision)
    elif args.command == "downgrade":
        command.downgrade(config, args.revision)
    else:
        command.current(config)


if __name__ == "__main__":
    main()
