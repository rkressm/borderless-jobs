"""Simulated urllib responses verify actual transport security and read bounds."""

import io
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler

import pytest
from borderless.connectors import ConnectorError
from borderless.connectors.http_transport import (
    USER_AGENT,
    JobicyHttpTransport,
    _NoRedirects,
)
from borderless.connectors.jobicy import JOBICY_ENDPOINT


class Response:
    status = 200

    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self.body, self.headers = io.BytesIO(body), headers
        self.closed = False

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def read1(self, size: int) -> bytes:
        return self.body.read(size)


class Opener:
    def __init__(self, response: Response | Exception) -> None:
        self.response = response
        self.request: Any = None

    def open(self, request: object, *, timeout: float) -> Response:
        self.request = request
        assert timeout == 10.0
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def setup_opener(
    monkeypatch: pytest.MonkeyPatch, response: Response | Exception
) -> Opener:
    opener = Opener(response)

    def build(*handlers: object) -> Opener:
        proxy = next(
            handler for handler in handlers if isinstance(handler, ProxyHandler)
        )
        tls = next(handler for handler in handlers if isinstance(handler, HTTPSHandler))
        assert vars(proxy)["proxies"] == {}
        assert vars(tls)["_context"].verify_mode == ssl.CERT_REQUIRED
        assert vars(tls)["_context"].check_hostname
        assert any(isinstance(handler, _NoRedirects) for handler in handlers)
        return opener

    monkeypatch.setattr("borderless.connectors.http_transport.build_opener", build)
    return opener


def test_fixed_tls_destination_headers_and_resource_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = Response(b"{}", {"Content-Type": "application/json"})
    opener = setup_opener(monkeypatch, response)
    assert (
        JobicyHttpTransport().get(JOBICY_ENDPOINT, 10.0, 10, lambda: False).body
        == b"{}"
    )
    assert response.closed
    assert opener.request.get_header("User-agent") == USER_AGENT
    assert opener.request.get_header("Accept-encoding") == "identity"
    assert (
        _NoRedirects().redirect_request(
            opener.request, None, 302, "redirect", None, "https://evil.example"
        )
        is None
    )


@pytest.mark.parametrize(
    "headers",
    [
        {"Content-Type": "text/html"},
        {"Content-Type": "application/json", "Content-Length": "11"},
        {"Content-Type": "application/json", "Content-Length": "bad"},
        {"Content-Type": "application/json", "Content-Encoding": "gzip"},
    ],
)
def test_untrusted_response_headers_are_rejected_before_reading(
    monkeypatch: pytest.MonkeyPatch, headers: dict[str, str]
) -> None:
    response = Response(b"a" * 11, headers)
    setup_opener(monkeypatch, response)
    with pytest.raises(ConnectorError, match="invalid_response"):
        JobicyHttpTransport().get(JOBICY_ENDPOINT, 10.0, 10, lambda: False)
    assert response.closed and response.body.tell() == 0


def test_streaming_size_limit_without_content_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = Response(b"a" * 11, {"Content-Type": "application/json"})
    setup_opener(monkeypatch, response)
    with pytest.raises(ConnectorError, match="invalid_response"):
        JobicyHttpTransport().get(JOBICY_ENDPOINT, 10.0, 10, lambda: False)
    assert response.closed and response.body.tell() == 11


@pytest.mark.parametrize(
    "url",
    [
        "http://jobicy.com/api/v2/remote-jobs",
        "https://jobicy.com.evil/api/v2/remote-jobs",
        "https://user:password@jobicy.com/api/v2/remote-jobs",
        JOBICY_ENDPOINT + "#fragment",
        "https://127.0.0.1/api/v2/remote-jobs",
    ],
)
def test_unsafe_destination_rejected_without_opening(url: str) -> None:
    with pytest.raises(ConnectorError, match="invalid_response"):
        JobicyHttpTransport().get(url, 10.0, 10, lambda: False)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (TimeoutError(), "timeout"),
        (URLError(TimeoutError()), "timeout"),
        (URLError("network"), "transport"),
        (OSError(), "transport"),
    ],
)
def test_operational_errors_are_sanitized(
    monkeypatch: pytest.MonkeyPatch, error: Exception, code: str
) -> None:
    setup_opener(monkeypatch, error)
    with pytest.raises(ConnectorError, match=code):
        JobicyHttpTransport().get(JOBICY_ENDPOINT, 10.0, 10, lambda: False)


def test_error_status_retains_only_retry_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from email.message import Message

    headers = Message()
    headers["Retry-After"] = "3"
    error = HTTPError(
        JOBICY_ENDPOINT, 429, "private reason", headers, io.BytesIO(b"private body")
    )
    setup_opener(monkeypatch, error)
    response = JobicyHttpTransport().get(JOBICY_ENDPOINT, 10.0, 10, lambda: False)
    assert (
        response.status_code == 429
        and response.retry_after == "3"
        and response.body == b""
    )


def test_cancellation_and_total_read_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Response(b"{}", {"Content-Type": "application/json"})
    setup_opener(monkeypatch, response)
    calls = iter([False, True])
    with pytest.raises(ConnectorError, match="cancelled"):
        JobicyHttpTransport().get(JOBICY_ENDPOINT, 10.0, 10, lambda: next(calls))
    assert response.closed
    clock = iter([0.0, 11.0])
    monkeypatch.setattr(
        "borderless.connectors.http_transport.time.monotonic", lambda: next(clock)
    )
    with pytest.raises(ConnectorError, match="timeout"):
        JobicyHttpTransport().get(JOBICY_ENDPOINT, 10.0, 10, lambda: False)
