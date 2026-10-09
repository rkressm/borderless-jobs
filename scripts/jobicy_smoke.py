"""Manual public Jobicy smoke check; never part of mandatory offline CI."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from borderless.connectors import ConnectorError
from borderless.connectors.jobicy import JobicyQuery
from borderless.connectors.live import JobicyConnector

from scripts.worktree_env import resource_values


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="explicitly permit one public network fetch"
    )
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("Pass --live to opt in; deterministic tests never fetch Jobicy")
    root = Path(__file__).resolve().parents[1]
    resources = resource_values(root)
    state = root / resources["WORKTREE_CACHE_DIR"] / "jobicy-poll.json"
    connector = JobicyConnector.live(JobicyQuery(count=1), state_path=state)
    try:
        batch = connector.fetch()
    except ConnectorError as error:
        print(json.dumps({"error": error.failure.to_dict()}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "source": batch.policy.source_id,
                "jobs": len(batch.jobs),
                "schema_version": batch.schema_version.value,
                "status_code": batch.metadata.status_code,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
