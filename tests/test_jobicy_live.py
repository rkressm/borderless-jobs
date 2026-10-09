"""Deterministic network simulations cover retries, governance and cancellation."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from typing import Any

import pytest
from borderless.connectors import Connector, ConnectorError, FailureCode
from borderless.connectors.http_transport import TransportResponse, fail
from borderless.connectors.jobicy import JobicyQuery
from borderless.connectors.live import JobicyConnector
from borderless.connectors.polling import FilePollingGate

BODY = (Path(__file__).parent / "fixtures" / "jobicy" / "page.json").read_bytes()
OK = TransportResponse(200, "application/json; charset=utf-8", BODY)
NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)


@dataclass
class Clock:
    now: datetime = NOW

    def __call__(self) -> datetime:
        return self.now


class FakeTransport:
    def __init__(self, responses: list[TransportResponse | ConnectorError]) -> None:
        self.responses = responses.copy()
        self.calls: list[tuple[str, float, int]] = []

    def get(
        self,
        url: str,
        timeout_seconds: float,
        max_bytes: int,
        cancelled: Callable[[], bool],
    ) -> TransportResponse:
        self.calls.append((url, timeout_seconds, max_bytes))
        response = self.responses.pop(0)
        if isinstance(response, ConnectorError):
            raise response
        return response


def make_connector(
    tmp_path: Path, transport: FakeTransport, **options: Any
) -> JobicyConnector:
    options.setdefault("clock", Clock())
    options.setdefault("jitter", lambda: 0.25)
    options.setdefault("wait", lambda seconds: False)
    return JobicyConnector(
        JobicyQuery(), transport, FilePollingGate(tmp_path / "poll.json"), **options
    )


def record_wait(delays: list[float]) -> Callable[[float], bool]:
    def wait(seconds: float) -> bool:
        delays.append(seconds)
        return False

    return wait


def test_success_is_the_same_contract_and_new_passes_are_durably_limited(
    tmp_path: Path,
) -> None:
    clock = Clock()
    transport = FakeTransport([OK, OK])
    connector: Connector = make_connector(tmp_path, transport, clock=clock)
    batch = connector.fetch()
    assert batch.jobs[0].external_id == "123456"
    assert batch.metadata.response_bytes == len(BODY)
    assert transport.calls[0][1:] == (10.0, 10_000_000)
    recreated = make_connector(tmp_path, transport, clock=clock)
    with pytest.raises(ConnectorError) as caught:
        recreated.fetch()
    assert caught.value.failure.code is FailureCode.RATE_LIMITED
    assert caught.value.failure.retry_after_seconds == 3600
    assert len(transport.calls) == 1
    clock.now += timedelta(hours=1)
    recreated.fetch()
    assert (tmp_path / "poll.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "failure",
    [
        fail(FailureCode.TIMEOUT),
        fail(FailureCode.TRANSPORT),
        TransportResponse(503, "text/html", b"private error"),
    ],
)
def test_transient_failures_retry_with_bounded_jitter(
    tmp_path: Path, failure: TransportResponse | ConnectorError
) -> None:
    transport = FakeTransport([failure, failure, OK])
    delays: list[float] = []
    connector = make_connector(tmp_path, transport, wait=record_wait(delays))
    assert connector.fetch().jobs
    assert delays == [1.25, 2.25]
    assert len(transport.calls) == 3


def test_timeout_exhaustion_and_failed_pass_still_reserves_polling(
    tmp_path: Path,
) -> None:
    transport = FakeTransport([fail(FailureCode.TIMEOUT)] * 3)
    connector = make_connector(tmp_path, transport)
    with pytest.raises(ConnectorError, match="timeout"):
        connector.fetch()
    assert len(transport.calls) == 3
    with pytest.raises(ConnectorError, match="rate_limited"):
        make_connector(tmp_path, transport).fetch()


@pytest.mark.parametrize("status", [301, 302, 401, 403, 404])
def test_permanent_status_does_not_retry(tmp_path: Path, status: int) -> None:
    transport = FakeTransport([TransportResponse(status, "text/html", b"error")])
    with pytest.raises(ConnectorError, match="transport"):
        make_connector(tmp_path, transport).fetch()
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        TransportResponse(200, "text/html", BODY),
        TransportResponse(200, "application/json", b"{malformed"),
        TransportResponse(200, "application/json", BODY + b" " * 1000),
    ],
)
def test_invalid_or_oversized_response_does_not_retry(
    tmp_path: Path, response: TransportResponse
) -> None:
    transport = FakeTransport([response])
    with pytest.raises(ConnectorError, match="invalid_response"):
        make_connector(tmp_path, transport, max_bytes=len(BODY)).fetch()
    assert len(transport.calls) == 1


def test_retry_after_defers_new_passes_without_a_long_sleep(tmp_path: Path) -> None:
    transport = FakeTransport([TransportResponse(429, "application/json", b"", "7200")])
    connector = make_connector(tmp_path, transport)
    with pytest.raises(ConnectorError) as caught:
        connector.fetch()
    assert caught.value.failure.retry_after_seconds == 7200
    with pytest.raises(ConnectorError) as caught:
        make_connector(tmp_path, transport).fetch()
    assert caught.value.failure.retry_after_seconds == 7200
    assert len(transport.calls) == 1


@pytest.mark.parametrize("header", ["3", "Fri, 09 Oct 2026 12:00:03 GMT"])
def test_retry_after_is_honored_before_retry(tmp_path: Path, header: str) -> None:
    transport = FakeTransport(
        [TransportResponse(429, "application/json", b"", header), OK]
    )
    delays: list[float] = []
    connector = make_connector(tmp_path, transport, wait=record_wait(delays))
    connector.fetch()
    assert delays == [3.0]


def test_cancellation_before_request_and_during_backoff(tmp_path: Path) -> None:
    event = Event()
    event.set()
    transport = FakeTransport([OK])
    with pytest.raises(ConnectorError, match="cancelled"):
        make_connector(tmp_path, transport, cancellation=event).fetch()
    assert transport.calls == [] and not (tmp_path / "poll.json").exists()
    event.clear()
    transport = FakeTransport([fail(FailureCode.TIMEOUT), OK])
    with pytest.raises(ConnectorError, match="cancelled"):
        make_connector(
            tmp_path, transport, cancellation=event, wait=lambda seconds: True
        ).fetch()
    assert len(transport.calls) == 1


def test_pagination_does_not_start_another_pass_and_rejects_cycles(
    tmp_path: Path,
) -> None:
    payload = json.loads(BODY)
    payload.update(nextCursor="page2", hasMore=True)
    first = TransportResponse(200, "application/json", json.dumps(payload).encode())
    transport = FakeTransport([first, OK])
    connector = make_connector(tmp_path, transport)
    cursor = connector.fetch().next_checkpoint
    assert cursor is not None
    assert connector.fetch(cursor).next_checkpoint is None
    with pytest.raises(ConnectorError, match="invalid_checkpoint"):
        connector.fetch(cursor)
    assert len(transport.calls) == 2


def test_checkpoint_scope_and_expiry_are_checked_before_network(tmp_path: Path) -> None:
    from borderless.connectors import Checkpoint

    transport = FakeTransport([])
    connector = make_connector(tmp_path, transport)
    for checkpoint in (
        Checkpoint(
            "other", connector.query.query_key, "token", NOW + timedelta(hours=1)
        ),
        Checkpoint("jobicy", connector.query.query_key, "token", NOW),
    ):
        with pytest.raises(ConnectorError, match="invalid_checkpoint"):
            connector.fetch(checkpoint)
    assert transport.calls == []


def test_corrupt_state_fails_closed_and_symlinks_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "poll.json"
    path.write_text("{broken")
    transport = FakeTransport([OK])
    with pytest.raises(ConnectorError, match="transport"):
        make_connector(tmp_path, transport).fetch()
    assert transport.calls == []
    link = tmp_path / "link.json"
    link.symlink_to(path)
    with pytest.raises(ConnectorError, match="transport"):
        FilePollingGate(link).reserve(NOW)
    assert path.read_text() == "{broken"


@pytest.mark.parametrize(
    "options",
    [
        {"max_attempts": 4},
        {"timeout_seconds": 0},
        {"max_bytes": 10_000_001},
        {"max_attempts": True},
    ],
)
def test_configuration_is_bounded(tmp_path: Path, options: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        make_connector(tmp_path, FakeTransport([]), **options)


def test_multi_page_cycle_and_server_deferral_cannot_be_bypassed(
    tmp_path: Path,
) -> None:
    payload = json.loads(BODY)
    payload.update(nextCursor="page2", hasMore=True)
    page2 = TransportResponse(200, "application/json", json.dumps(payload).encode())
    payload["nextCursor"] = "page3"
    page3 = TransportResponse(200, "application/json", json.dumps(payload).encode())
    transport = FakeTransport([page2, page3, page2])
    connector = make_connector(tmp_path, transport)
    second = connector.fetch().next_checkpoint
    third = connector.fetch(second).next_checkpoint
    with pytest.raises(ConnectorError, match="invalid_response"):
        connector.fetch(third)


def test_retry_after_also_blocks_resumed_pages(tmp_path: Path) -> None:
    from borderless.connectors import Checkpoint

    transport = FakeTransport(
        [TransportResponse(429, "application/json", b"", "172800")]
    )
    connector = make_connector(tmp_path, transport)
    cursor = Checkpoint(
        "jobicy", connector.query.query_key, "resume", NOW + timedelta(hours=1)
    )
    with pytest.raises(ConnectorError) as caught:
        connector.fetch(cursor)
    assert caught.value.failure.retry_after_seconds == 172800
    with pytest.raises(ConnectorError, match="rate_limited"):
        make_connector(tmp_path, transport).fetch(cursor)
    assert len(transport.calls) == 1
