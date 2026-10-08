"""Offline invariants of the production connector seam."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from borderless.connectors.contracts import (
    MAX_BATCH_BYTES,
    Checkpoint,
    ConnectorBatch,
    ConnectorError,
    ConnectorFailure,
    FailureCode,
    FetchMetadata,
    RawEnvelope,
)
from borderless.connectors.policy import JOBICY_POLICY
from borderless.domain import SchemaVersion

NOW = datetime(2026, 10, 8, tzinfo=UTC)
JOB = RawEnvelope("jobicy", "1", "https://jobicy.com/jobs/example", '{"id":1}')
META = FetchMetadata(
    "fetch-1", "jobicy", "all", "https://jobicy.com/api/v2/remote-jobs", NOW, NOW, 100
)
CURSOR = Checkpoint("jobicy", "all", "opaque-next", NOW + timedelta(days=1))


def test_batches_preserve_raw_bytes_policy_and_cursor_in_json() -> None:
    batch = ConnectorBatch(JOBICY_POLICY, META, (JOB,), next_checkpoint=CURSOR)
    restored = ConnectorBatch.from_dict(json.loads(json.dumps(batch.to_dict())))
    assert restored == batch
    assert restored.jobs[0].payload_json == '{"id":1}'
    assert "payload_json" not in repr(JOB)
    assert "opaque-next" not in repr(batch)
    final = replace(batch, requested_checkpoint=CURSOR, next_checkpoint=None, jobs=())
    assert final.next_checkpoint is None
    assert ConnectorBatch.from_dict(final.to_dict()) == final


@pytest.mark.parametrize(
    "changes",
    [
        {"source_id": "other"},
        {"query_key": "changed"},
        {"token": ""},
        {"token": "x" * 2049},
        {"expires_at": NOW},
    ],
)
def test_invalid_checkpoint_or_scope_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        cursor = Checkpoint.from_dict(CURSOR.to_dict() | changes)
        ConnectorBatch(JOBICY_POLICY, META, (JOB,), next_checkpoint=cursor)


def test_pagination_cannot_loop_or_extend_expiry() -> None:
    with pytest.raises(ValueError, match="advance"):
        ConnectorBatch(JOBICY_POLICY, META, (), CURSOR, CURSOR)
    with pytest.raises(ValueError, match="expiry"):
        ConnectorBatch(
            JOBICY_POLICY,
            META,
            (),
            CURSOR,
            replace(
                CURSOR,
                token="new",
                expires_at=NOW + timedelta(days=2),
            ),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"response_bytes": -1},
        {"response_bytes": MAX_BATCH_BYTES + 1},
        {"response_bytes": True},
        {"completed_at": NOW - timedelta(seconds=1)},
        {"started_at": NOW.replace(tzinfo=None)},
        {"status_code": 429},
        {"media_type": "text/html"},
        {"request_url": "file:///etc/passwd"},
    ],
)
def test_fetch_metadata_rejects_invalid_response(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        FetchMetadata.from_dict(META.to_dict() | changes)


@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        "null",
        "{",
        '{"number":NaN}',
        '{"number":Infinity}',
        '{"text":"' + "é" * 500_000 + '"}',
        '{"text":"\ud800"}',
        '{"nested":' + "[" * 2000 + "0" + "]" * 2000 + "}",
    ],
)
def test_raw_payload_is_bounded_utf8_json_object(payload: str) -> None:
    with pytest.raises(ValueError):
        replace(JOB, payload_json=payload)


def test_batch_rejects_source_duplicate_count_size_and_schema_mismatches() -> None:
    batch = ConnectorBatch(JOBICY_POLICY, META, (JOB,))
    invalid: list[dict[str, Any]] = [
        {"jobs": (JOB, JOB)},
        {"jobs": (replace(JOB, source_id="other"),)},
        {"metadata": replace(META, source_id="other")},
        {"metadata": replace(META, response_bytes=0)},
        {"jobs": tuple(replace(JOB, external_id=str(i)) for i in range(1001))},
        {"schema_version": SchemaVersion("2.0.0")},
    ]
    for changes in invalid:
        with pytest.raises(ValueError):
            replace(batch, **changes)


def test_failure_is_serializable_and_exception_exposes_only_safe_code() -> None:
    failure = ConnectorFailure("jobicy", FailureCode.RATE_LIMITED, 3600)
    assert ConnectorFailure.from_dict(failure.to_dict()) == failure
    error = ConnectorError(failure)
    assert error.failure == failure
    assert str(error) == "rate_limited"
    for code, delay in [(FailureCode.INVALID_RESPONSE, 1), (FailureCode.TIMEOUT, -1)]:
        with pytest.raises(ValueError):
            ConnectorFailure("jobicy", code, delay)
    with pytest.raises(ValueError):
        ConnectorFailure.from_dict(failure.to_dict() | {"code": "arbitrary"})


def test_unknown_fields_and_mutable_input_rejected() -> None:
    with pytest.raises(ValueError):
        ConnectorBatch.from_dict(
            ConnectorBatch(JOBICY_POLICY, META, ()).to_dict() | {"has_more": True}
        )
    with pytest.raises(ValueError):
        ConnectorBatch(JOBICY_POLICY, META, [JOB])  # type: ignore[arg-type]
