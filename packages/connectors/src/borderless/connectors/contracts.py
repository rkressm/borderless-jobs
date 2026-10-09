"""Immutable ingestion seam; payloads are private, untrusted JSON text."""

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from borderless.domain import SchemaVersion, Value, require_public_url, require_text

from .policy import SourcePolicy

MAX_PAYLOAD_BYTES = 1_000_000
MAX_BATCH_BYTES = 10_000_000
MAX_BATCH_JOBS = 1000


def _bounded_identifier(value: str) -> None:
    require_text(value)
    if len(value) > 2048:
        raise ValueError("Identifier exceeds contract limit")


@dataclass(frozen=True, slots=True)
class Checkpoint(Value):
    source_id: str
    query_key: str
    token: str = field(repr=False)
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for value in (self.source_id, self.query_key, self.token):
            _bounded_identifier(value)


@dataclass(frozen=True, slots=True)
class FetchMetadata(Value):
    fetch_id: str
    source_id: str
    query_key: str
    request_url: str
    started_at: datetime
    completed_at: datetime
    response_bytes: int
    status_code: int = 200
    media_type: str = "application/json"
    source_metadata_json: str = field(default="{}", repr=False)

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for value in (self.fetch_id, self.source_id, self.query_key):
            _bounded_identifier(value)
        require_public_url(self.request_url)
        metadata = json.loads(
            self.source_metadata_json, parse_constant=_reject_constant
        )
        _validate_json_depth(metadata)
        if (
            type(metadata) is not dict
            or len(self.source_metadata_json.encode("utf-8")) > MAX_BATCH_BYTES
        ):
            raise ValueError("Source metadata must be a bounded JSON object")
        if self.completed_at < self.started_at:
            raise ValueError("Fetch completion cannot precede start")
        if not 0 <= self.response_bytes <= MAX_BATCH_BYTES:
            raise ValueError("Response exceeds batch byte limit")
        if not 200 <= self.status_code < 300 or self.media_type != "application/json":
            raise ValueError("Successful fetch requires JSON and a success status")


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON numbers are unsupported")


def _validate_json_depth(payload: object) -> None:
    pending = [(payload, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > 64:
            raise ValueError("Raw JSON nesting exceeds 64 levels")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite JSON numbers are unsupported")
        if isinstance(value, str):
            value.encode("utf-8")
        if isinstance(value, dict):
            for key in value:
                key.encode("utf-8")
            pending.extend((child, depth + 1) for child in value.values())
        elif isinstance(value, list):
            pending.extend((child, depth + 1) for child in value)


@dataclass(frozen=True, slots=True)
class RawEnvelope(Value):
    source_id: str
    external_id: str
    canonical_url: str
    payload_json: str = field(repr=False)

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        _bounded_identifier(self.source_id)
        _bounded_identifier(self.external_id)
        require_public_url(self.canonical_url)
        if self.size_bytes > MAX_PAYLOAD_BYTES:
            raise ValueError("Raw payload exceeds byte limit")
        try:
            payload = json.loads(self.payload_json, parse_constant=_reject_constant)
        except (RecursionError, UnicodeError) as error:
            raise ValueError("Invalid raw JSON") from error
        _validate_json_depth(payload)
        if not isinstance(payload, dict):
            raise ValueError("Raw job payload must be a JSON object")

    @property
    def content_hash(self) -> str:
        """Stable semantic raw fingerprint; catalog owns versioning decisions."""
        canonical = json.dumps(
            json.loads(self.payload_json),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def size_bytes(self) -> int:
        try:
            return len(self.payload_json.encode("utf-8"))
        except UnicodeError as error:
            raise ValueError("Raw payload must be valid UTF-8") from error


@dataclass(frozen=True, slots=True)
class ConnectorBatch(Value):
    policy: SourcePolicy
    metadata: FetchMetadata
    jobs: tuple[RawEnvelope, ...]
    requested_checkpoint: Checkpoint | None = None
    next_checkpoint: Checkpoint | None = None
    schema_version: SchemaVersion = SchemaVersion("1.1.0")

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if self.schema_version != SchemaVersion("1.1.0"):
            raise ValueError("Unsupported connector schema")
        if self.policy.source_id != self.metadata.source_id:
            raise ValueError("Policy and fetch source must agree")
        if len(self.jobs) > MAX_BATCH_JOBS:
            raise ValueError("Batch job count exceeds limit")
        if sum(job.size_bytes for job in self.jobs) > self.metadata.response_bytes:
            raise ValueError("Response byte count cannot be smaller than job payloads")
        ids = [job.external_id for job in self.jobs]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate source identity in page")
        if any(job.source_id != self.policy.source_id for job in self.jobs):
            raise ValueError("Every job must belong to the batch source")
        self._validate_checkpoints()

    def _validate_checkpoints(self) -> None:
        for checkpoint in (self.requested_checkpoint, self.next_checkpoint):
            if checkpoint is None:
                continue
            if (checkpoint.source_id, checkpoint.query_key) != (
                self.metadata.source_id,
                self.metadata.query_key,
            ):
                raise ValueError("Checkpoint source and unchanged query must agree")
            if (
                checkpoint.expires_at is not None
                and checkpoint.expires_at <= self.metadata.completed_at
            ):
                raise ValueError("Checkpoint expired before fetch completion")
        if self.requested_checkpoint is not None and self.next_checkpoint is not None:
            if self.requested_checkpoint.token == self.next_checkpoint.token:
                raise ValueError("Pagination must advance the opaque cursor")
            if self.requested_checkpoint.expires_at != self.next_checkpoint.expires_at:
                raise ValueError("Pagination must preserve traversal expiry")


class FailureCode(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    TRANSPORT = "transport"
    INVALID_RESPONSE = "invalid_response"
    INVALID_CHECKPOINT = "invalid_checkpoint"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ConnectorFailure(Value):
    source_id: str
    code: FailureCode
    retry_after_seconds: int | None = None

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        _bounded_identifier(self.source_id)
        if self.retry_after_seconds is not None:
            if self.retry_after_seconds < 0 or self.code not in {
                FailureCode.TIMEOUT,
                FailureCode.RATE_LIMITED,
                FailureCode.TRANSPORT,
            }:
                raise ValueError("Only transient failures support deferred retry")


class ConnectorError(Exception):
    """Sanitized operational failure without a transport exception or raw body."""

    def __init__(self, failure: ConnectorFailure) -> None:
        self.failure = failure
        super().__init__(failure.code.value)


class Connector(Protocol):
    def fetch(self, checkpoint: Checkpoint | None = None) -> ConnectorBatch:
        """Fetch one bounded page or raise ConnectorError; None starts a pass."""
        ...
