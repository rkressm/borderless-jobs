"""Recorded connectors fulfill the source-neutral contract without network I/O."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from borderless.connectors import Connector, ConnectorBatch, ConnectorError, FailureCode
from borderless.connectors.fixture import FixtureConnector

FIXTURES = Path(__file__).parent / "fixtures" / "connectors"


@pytest.mark.parametrize("filename", ["complete.json", "empty.json"])
def test_fixture_satisfies_connector_contract_and_replays(filename: str) -> None:
    connector: Connector = FixtureConnector.load(FIXTURES / filename)
    checkpoint = None
    page_count = 0
    while True:
        batch = connector.fetch(checkpoint)
        assert batch == connector.fetch(checkpoint)
        assert batch == ConnectorBatch.from_dict(
            json.loads(json.dumps(batch.to_dict()))
        )
        assert batch.requested_checkpoint == checkpoint
        assert batch.policy.source_id == "synthetic"
        page_count += 1
        checkpoint = batch.next_checkpoint
        if checkpoint is None:
            break
    assert page_count == (2 if filename == "complete.json" else 1)


def test_checkpoint_resume_and_repeated_source_identity_across_pages() -> None:
    connector = FixtureConnector.load(FIXTURES / "complete.json")
    first = connector.fetch()
    resumed = FixtureConnector.load(FIXTURES / "complete.json").fetch(
        first.next_checkpoint
    )
    assert first.jobs[0].external_id == resumed.jobs[0].external_id
    assert first.jobs[0].payload_json == resumed.jobs[0].payload_json
    assert resumed.next_checkpoint is None
    assert connector == FixtureConnector.from_dict(connector.to_dict())


def test_unknown_or_modified_checkpoint_is_typed_failure() -> None:
    connector = FixtureConnector.load(FIXTURES / "complete.json")
    checkpoint = connector.fetch().next_checkpoint
    assert checkpoint is not None
    for invalid in (
        replace(checkpoint, token="unknown"),
        replace(checkpoint, query_key="other"),
    ):
        with pytest.raises(ConnectorError) as caught:
            connector.fetch(invalid)
        assert caught.value.failure.code is FailureCode.INVALID_CHECKPOINT


@pytest.mark.parametrize(
    "content", [b"{", b"\xff", b"[]", b'{"batches": []}', b"[" * 10000]
)
def test_malformed_recording_returns_sanitized_failure(
    tmp_path: Path, content: bytes
) -> None:
    path = tmp_path / "untrusted.json"
    path.write_bytes(content)
    with pytest.raises(ConnectorError) as caught:
        FixtureConnector.load(path)
    assert str(caught.value) == "invalid_response"
    assert caught.value.__cause__ is None


def test_missing_file_and_size_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ConnectorError):
        FixtureConnector.load(tmp_path / "missing.json")
    monkeypatch.setattr("borderless.connectors.fixture.MAX_RECORDING_BYTES", 10)
    with pytest.raises(ConnectorError):
        FixtureConnector.load(FIXTURES / "complete.json")


def test_provenance_and_traversal_invariants() -> None:
    connector = FixtureConnector.load(FIXTURES / "complete.json")
    data = connector.to_dict()
    invalid: list[dict[str, Any]] = [
        data | {"provenance": data["provenance"] | {"license": ""}},
        data | {"provenance": data["provenance"] | {"kind": "scraped"}},
        data | {"batches": []},
        data | {"batches": [data["batches"][0]]},
        data | {"batches": list(reversed(data["batches"]))},
        data
        | {
            "batches": [
                data["batches"][0],
                data["batches"][1] | {"requested_checkpoint": None},
            ]
        },
    ]
    for recording in invalid:
        with pytest.raises(ValueError):
            FixtureConnector.from_dict(recording)
    first, last = connector.batches
    cursor = last.requested_checkpoint
    assert cursor is not None
    with pytest.raises(ValueError, match="unchanged"):
        replace(
            connector,
            batches=(
                first,
                replace(last, policy=replace(last.policy, raw_retention_days=1)),
            ),
        )
    with pytest.raises(ValueError, match="cycle"):
        replace(
            connector,
            batches=(
                first,
                replace(
                    last,
                    next_checkpoint=replace(cursor, token="third"),
                ),
                replace(
                    last,
                    requested_checkpoint=replace(cursor, token="third"),
                    next_checkpoint=last.requested_checkpoint,
                ),
            ),
        )
