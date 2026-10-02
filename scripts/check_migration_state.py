"""Assert the disposable database's exact Alembic revision."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from sqlalchemy import create_engine

from scripts.migrate import local_database_url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", choices=("base", "0001"))
    args = parser.parse_args()
    engine = create_engine(local_database_url("test"))
    try:
        with engine.connect() as connection:
            table: str | None = connection.exec_driver_sql(
                "SELECT to_regclass('public.alembic_version')"
            ).scalar_one()
            if table is None:
                actual = "base"
            else:
                revisions: Sequence[str] = (
                    connection.exec_driver_sql(
                        "SELECT version_num FROM alembic_version"
                    )
                    .scalars()
                    .all()
                )
                actual = "base" if not revisions else ",".join(revisions)
    finally:
        engine.dispose()
    if actual != args.expected:
        raise SystemExit(f"Expected migration {args.expected}, found {actual}")


if __name__ == "__main__":
    main()
