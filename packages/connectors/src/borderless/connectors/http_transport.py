"""Private stdlib HTTP adapter: a fixed destination, verified TLS, bounded reads."""

import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from .contracts import MAX_BATCH_BYTES, ConnectorError, ConnectorFailure, FailureCode
from .jobicy import JOBICY_ENDPOINT

USER_AGENT = "BorderlessJobs/0.1 (+https://github.com/rkressm/borderless-jobs)"


@dataclass(frozen=True, slots=True)
class TransportResponse:
    status_code: int
    content_type: str
    body: bytes = field(repr=False)
    retry_after: str | None = None


def fail(code: FailureCode, retry_after: int | None = None) -> ConnectorError:
    return ConnectorError(ConnectorFailure("jobicy", code, retry_after))


def check_cancelled(cancelled: Callable[[], bool]) -> None:
    if cancelled():
        raise fail(FailureCode.CANCELLED)


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> Request | None:
        return None


class JobicyHttpTransport:
    """Construction has no network effects; get is called only by opt-in users."""

    def get(
        self,
        url: str,
        timeout_seconds: float,
        max_bytes: int,
        cancelled: Callable[[], bool],
    ) -> TransportResponse:
        parts, endpoint = urlsplit(url), urlsplit(JOBICY_ENDPOINT)
        if (
            (parts.scheme, parts.netloc, parts.path)
            != (endpoint.scheme, endpoint.netloc, endpoint.path)
            or parts.fragment
            or any(ord(char) <= 32 for char in url)
        ):
            raise fail(FailureCode.INVALID_RESPONSE)
        if not 0 < timeout_seconds <= 30 or not 1 <= max_bytes <= MAX_BATCH_BYTES:
            raise ValueError("Invalid timeout or response limit")
        check_cancelled(cancelled)
        opener = build_opener(
            ProxyHandler({}),
            HTTPSHandler(context=ssl.create_default_context()),
            _NoRedirects(),
        )
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            },
            method="GET",
        )
        deadline = time.monotonic() + timeout_seconds
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                if (
                    response.headers.get("Content-Encoding", "identity").lower()
                    != "identity"
                ):
                    raise fail(FailureCode.INVALID_RESPONSE)
                length = response.headers.get("Content-Length")
                if length is not None and (
                    not length.isdecimal() or int(length) > max_bytes
                ):
                    raise fail(FailureCode.INVALID_RESPONSE)
                content_type = response.headers.get("Content-Type", "")
                if content_type.split(";", 1)[0].strip().lower() != "application/json":
                    raise fail(FailureCode.INVALID_RESPONSE)
                chunks: list[bytes] = []
                size = 0
                while True:
                    check_cancelled(cancelled)
                    if time.monotonic() >= deadline:
                        raise fail(FailureCode.TIMEOUT)
                    chunk = response.read1(min(65536, max_bytes - size + 1))
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise fail(FailureCode.INVALID_RESPONSE)
                    chunks.append(chunk)
                return TransportResponse(
                    response.status, content_type, b"".join(chunks)
                )
        except HTTPError as error:
            try:
                return TransportResponse(
                    error.code,
                    error.headers.get("Content-Type", ""),
                    b"",
                    error.headers.get("Retry-After"),
                )
            finally:
                error.close()
        except TimeoutError:
            raise fail(FailureCode.TIMEOUT) from None
        except URLError as error:
            code = (
                FailureCode.TIMEOUT
                if isinstance(error.reason, TimeoutError)
                else FailureCode.TRANSPORT
            )
            raise fail(code) from None
        except OSError:
            raise fail(FailureCode.TRANSPORT) from None
