"""Synthetic public responses exercise the common ingestion contract offline."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from borderless.catalog import normalize_description
from borderless.connectors import (
    Connector,
    ConnectorBatch,
    ConnectorError,
    FetchMetadata,
    FixtureConnector,
    FixtureKind,
    FixtureProvenance,
)
from borderless.connectors.jobicy import JobicyQuery, map_jobicy_response

NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)
BODY = (Path(__file__).parent / "fixtures" / "jobicy" / "page.json").read_bytes()
QUERY = JobicyQuery()


def metadata(body: bytes = BODY) -> FetchMetadata:
    return FetchMetadata(
        "recorded-1",
        "jobicy",
        QUERY.query_key,
        QUERY.request_url(),
        NOW,
        NOW,
        len(body),
    )


def mapped(payload: dict[str, Any]) -> ConnectorBatch:
    body = json.dumps(payload).encode()
    return map_jobicy_response(body, metadata(body), QUERY)


def test_raw_objects_metadata_policy_hash_and_shared_contract() -> None:
    batch = map_jobicy_response(BODY, metadata(), QUERY)
    raw = batch.jobs[0]
    assert (
        raw.payload_json
        == BODY.decode().split('"jobs": [\n    ', 1)[1].split("\n  ],", 1)[0]
    )
    assert json.loads(raw.payload_json)["customMetadata"] == {"synthetic": True}
    assert json.loads(batch.metadata.source_metadata_json)["apiVersion"] == "2.2.19"
    assert batch.policy.source_id == "jobicy" and batch.policy.raw_private
    assert ConnectorBatch.from_dict(batch.to_dict()) == batch
    connector: Connector = FixtureConnector(
        FixtureProvenance(
            FixtureKind.SYNTHETIC, "test authors", "MIT", "Invented content"
        ),
        (batch,),
    )
    assert connector.fetch() == connector.fetch()
    reordered = replace(
        raw, payload_json=json.dumps(json.loads(raw.payload_json), sort_keys=True)
    )
    assert raw.content_hash == reordered.content_hash
    assert (
        raw.content_hash
        != replace(
            raw,
            payload_json=raw.payload_json.replace("Invented Company", "Other Company"),
        ).content_hash
    )
    document = normalize_description(
        raw, "version-1", json.loads(raw.payload_json)["jobDescription"]
    )
    assert document.canonical_text == "Remote from Bolivia & LATAM. Contractor work."


def test_empty_page_and_additive_schema_drift() -> None:
    payload = json.loads(BODY)
    payload.update(jobs=[], jobCount=0, newMetadata={"version": 1})
    batch = mapped(payload)
    assert batch.jobs == () and batch.next_checkpoint is None
    assert json.loads(batch.metadata.source_metadata_json)["newMetadata"] == {
        "version": 1
    }


def test_pagination_expiry_is_fixed_and_query_is_unchanged() -> None:
    payload = json.loads(BODY)
    payload.update(nextCursor="opaque+/=next", hasMore=True)
    first = mapped(payload)
    cursor = first.next_checkpoint
    assert cursor is not None and cursor.expires_at == NOW + timedelta(hours=24)
    body = json.dumps(json.loads(BODY)).encode()
    meta = replace(
        metadata(body),
        request_url=QUERY.request_url(cursor),
        started_at=NOW + timedelta(hours=1),
        completed_at=NOW + timedelta(hours=1),
    )
    last = map_jobicy_response(body, meta, QUERY, cursor)
    assert last.requested_checkpoint == cursor and last.next_checkpoint is None
    assert "opaque%2B%2F%3Dnext" in meta.request_url


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", True),
        ("id", -1),
        ("id", "1"),
        ("url", "javascript:alert(1)"),
        ("url", "https://jobicy.com.evil/jobs/1"),
        ("url", "http://jobicy.com/jobs/1"),
        ("url", "https://jobicy.com/jobs/1?token=secret"),
        ("jobTitle", "a" * 501),
        ("companyName", None),
        ("jobDescription", []),
        ("jobDescription", "\ud800"),
        ("pubDate", "2026-10-09"),
        ("jobIndustry", "Engineering"),
        ("jobType", [1]),
        ("jobDescription", "é" * 500_001),
    ],
)
def test_invalid_job_fields_fail_closed(field: str, value: object) -> None:
    payload = json.loads(BODY)
    payload["jobs"][0][field] = value
    with pytest.raises(ConnectorError, match="invalid_response"):
        mapped(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("success", False),
        ("statusCode", True),
        ("jobCount", 2),
        ("apiVersion", "3.0.0"),
        ("hasMore", True),
        ("nextCursor", ""),
        ("jobs", {}),
    ],
)
def test_schema_and_pagination_drift_fail_closed(field: str, value: object) -> None:
    payload = json.loads(BODY)
    payload[field] = value
    with pytest.raises(ConnectorError):
        mapped(payload)


def test_missing_fields_duplicates_and_bad_json_are_sanitized() -> None:
    for field in ("id", "url", "jobTitle", "jobDescription", "pubDate"):
        payload = json.loads(BODY)
        del payload["jobs"][0][field]
        with pytest.raises(ConnectorError):
            mapped(payload)
    for body in (b"{", b"\xff", b'{"jobs":[],"jobs":[]}', b"[" * 10000):
        with pytest.raises(ConnectorError):
            map_jobicy_response(body, metadata(body), QUERY)
    with pytest.raises(ConnectorError):
        map_jobicy_response(BODY, replace(metadata(), response_bytes=1), QUERY)
    payload = json.loads(BODY)
    payload["jobs"] *= 2
    payload["jobCount"] = 2
    with pytest.raises(ConnectorError):
        mapped(payload)


@pytest.mark.parametrize(
    "query",
    [
        {"count": 0},
        {"count": True},
        {"geo": "USA"},
        {"tag": "ab"},
        {"tag": "<b>python</b>"},
        {"tag": "é" * 26},
    ],
)
def test_invalid_queries(query: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        JobicyQuery(**query)
