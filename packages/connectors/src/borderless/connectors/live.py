"""Opt-in Jobicy fetching over an injected transport and durable polling gate."""

import math
import random
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from threading import Event
from typing import Protocol, Self

from .contracts import (
    MAX_BATCH_BYTES,
    Checkpoint,
    ConnectorBatch,
    ConnectorError,
    FailureCode,
    FetchMetadata,
)
from .http_transport import (
    JobicyHttpTransport,
    TransportResponse,
    check_cancelled,
    fail,
)
from .jobicy import JobicyQuery, map_jobicy_response
from .polling import FilePollingGate


class HttpTransport(Protocol):
    def get(
        self,
        url: str,
        timeout_seconds: float,
        max_bytes: int,
        cancelled: Callable[[], bool],
    ) -> TransportResponse: ...


def _now() -> datetime:
    return datetime.now(UTC)


class JobicyConnector:
    def __init__(
        self,
        query: JobicyQuery,
        transport: HttpTransport,
        gate: FilePollingGate,
        *,
        clock: Callable[[], datetime] = _now,
        cancellation: Event | None = None,
        wait: Callable[[float], bool] | None = None,
        jitter: Callable[[], float] = random.random,
        timeout_seconds: float = 10.0,
        max_bytes: int = MAX_BATCH_BYTES,
        max_attempts: int = 3,
    ) -> None:
        if (
            not 0 < timeout_seconds <= 30
            or type(max_bytes) is not int
            or not 1 <= max_bytes <= MAX_BATCH_BYTES
            or type(max_attempts) is not int
            or not 1 <= max_attempts <= 3
        ):
            raise ValueError("Invalid bounded transport configuration")
        self.query, self.transport, self.gate = query, transport, gate
        self.clock, self.cancellation = (
            clock,
            cancellation if cancellation is not None else Event(),
        )
        self.wait, self.jitter = (
            wait if wait is not None else self.cancellation.wait,
            jitter,
        )
        self.timeout_seconds, self.max_bytes, self.max_attempts = (
            timeout_seconds,
            max_bytes,
            max_attempts,
        )
        self._expected: Checkpoint | None = None
        self._seen: set[str] = set()
        self._has_page = False

    @classmethod
    def live(cls, query: JobicyQuery, *, state_path: Path) -> Self:
        """Explicit network opt-in; state_path must be namespaced per worktree."""
        return cls(query, JobicyHttpTransport(), FilePollingGate(state_path))

    def _validate_checkpoint(self, checkpoint: Checkpoint, now: datetime) -> None:
        if (
            checkpoint.source_id != "jobicy"
            or checkpoint.query_key != self.query.query_key
            or checkpoint.expires_at is None
            or not now < checkpoint.expires_at <= now + timedelta(hours=24)
        ):
            raise fail(FailureCode.INVALID_CHECKPOINT)
        if self._has_page and checkpoint != self._expected:
            raise fail(FailureCode.INVALID_CHECKPOINT)

    def fetch(self, checkpoint: Checkpoint | None = None) -> ConnectorBatch:
        check_cancelled(self.cancellation.is_set)
        started = self.clock()
        if started.utcoffset() is None:
            raise ValueError("Fetch clock must return a timezone-aware instant")
        if checkpoint is None:
            self.gate.reserve(started)
            self._seen.clear()
            self._has_page = False
        else:
            self._validate_checkpoint(checkpoint, started)
            self.gate.check_page(started)
            self._seen.add(checkpoint.token)
        url = self.query.request_url(checkpoint)
        response = self._request(url)
        check_cancelled(self.cancellation.is_set)
        metadata = FetchMetadata(
            str(uuid.uuid4()),
            "jobicy",
            self.query.query_key,
            url,
            started,
            self.clock(),
            len(response.body),
            response.status_code,
        )
        batch = map_jobicy_response(response.body, metadata, self.query, checkpoint)
        if (
            batch.next_checkpoint is not None
            and batch.next_checkpoint.token in self._seen
        ):
            raise fail(FailureCode.INVALID_RESPONSE)
        self._expected, self._has_page = batch.next_checkpoint, True
        return batch

    def _request(self, url: str) -> TransportResponse:
        for attempt in range(self.max_attempts):
            check_cancelled(self.cancellation.is_set)
            try:
                response = self.transport.get(
                    url, self.timeout_seconds, self.max_bytes, self.cancellation.is_set
                )
            except ConnectorError as error:
                if (
                    error.failure.code
                    not in {FailureCode.TIMEOUT, FailureCode.TRANSPORT}
                    or attempt + 1 == self.max_attempts
                ):
                    raise
                self._pause(min(30.0, 2**attempt + self._jitter()))
                continue
            check_cancelled(self.cancellation.is_set)
            if 200 <= response.status_code < 300:
                if (
                    type(response.body) is not bytes
                    or len(response.body) > self.max_bytes
                    or response.content_type.split(";", 1)[0].strip().lower()
                    != "application/json"
                ):
                    raise fail(FailureCode.INVALID_RESPONSE)
                return response
            self._retry_status(response, attempt)
        raise AssertionError("Bounded request loop must return or raise")

    def _jitter(self) -> float:
        value = self.jitter()
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Jitter must be between zero and one")
        return value

    def _retry_status(self, response: TransportResponse, attempt: int) -> None:
        retryable = response.status_code in {408, 429, 500, 502, 503, 504}
        code = (
            FailureCode.RATE_LIMITED
            if response.status_code == 429
            else FailureCode.TRANSPORT
        )
        if not retryable:
            raise fail(
                FailureCode.INVALID_CHECKPOINT if response.status_code == 400 else code
            )
        delay = self._retry_after(response.retry_after)
        if delay is not None:
            now = self.clock()
            maximum = (
                math.floor((datetime.max.replace(tzinfo=UTC) - now).total_seconds()) - 1
            )
            self.gate.defer(now + timedelta(seconds=min(delay, maximum)))
        if attempt + 1 == self.max_attempts or (delay is not None and delay > 30):
            raise fail(code, delay)
        self._pause(max(float(delay or 0), min(30.0, 2**attempt + self._jitter())))

    def _retry_after(self, value: str | None) -> int | None:
        if value is None or len(value) > 100:
            return None
        if value.isdecimal():
            return int(value)
        try:
            instant = parsedate_to_datetime(value)
            if instant.utcoffset() is None:
                return None
            return max(0, math.ceil((instant - self.clock()).total_seconds()))
        except (ValueError, TypeError, OverflowError):
            return None

    def _pause(self, seconds: float) -> None:
        if self.wait(seconds):
            raise fail(FailureCode.CANCELLED)
        check_cancelled(self.cancellation.is_set)
