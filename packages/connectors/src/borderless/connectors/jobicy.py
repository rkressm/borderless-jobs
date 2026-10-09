"""Offline mapping of public Jobicy responses to the ingestion contract."""

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlsplit

from borderless.domain import Value, require_public_url, require_text

from .contracts import (
    MAX_BATCH_BYTES,
    Checkpoint,
    ConnectorBatch,
    ConnectorError,
    ConnectorFailure,
    FailureCode,
    FetchMetadata,
    RawEnvelope,
    _reject_constant,
    _validate_json_depth,
)
from .policy import JOBICY_POLICY

JOBICY_ENDPOINT = "https://jobicy.com/api/v2/remote-jobs"


@dataclass(frozen=True, slots=True)
class JobicyQuery(Value):
    count: int = 100
    geo: str | None = None
    industry: str | None = None
    tag: str | None = None

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if not 1 <= self.count <= 200:
            raise ValueError("Jobicy count must be between 1 and 200")
        for slug in (self.geo, self.industry):
            if slug is not None and not re.fullmatch(r"[a-z0-9-]{1,100}", slug):
                raise ValueError("Expected a bounded Jobicy taxonomy slug")
        if self.tag is not None:
            require_text(self.tag)
            if (
                self.tag != self.tag.strip()
                or not 3 <= len(self.tag.encode("utf-8")) <= 50
            ):
                raise ValueError("Jobicy keyword must contain 3–50 UTF-8 bytes")
            if "<" in self.tag or ">" in self.tag:
                raise ValueError("Jobicy keyword must be plain text")

    @property
    def query_key(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()

    def request_url(self, checkpoint: Checkpoint | None = None) -> str:
        params = {
            key: str(value)
            for key, value in self.to_dict().items()
            if value is not None
        }
        if checkpoint is not None:
            params["cursor"] = checkpoint.token
        return JOBICY_ENDPOINT + "?" + urlencode(params)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _raw_jobs(text: str, decoder: json.JSONDecoder) -> tuple[str, ...]:
    """Locate exact job object substrings after validating the complete JSON."""
    position = _skip_space(text, 0) + 1
    while True:
        position = _skip_space(text, position)
        if text[position] == "}":
            return ()
        key, position = decoder.raw_decode(text, position)
        position = _skip_space(text, position) + 1  # validated colon
        position = _skip_space(text, position)
        if key == "jobs":
            return _array_items(text, position + 1, decoder)
        _, position = decoder.raw_decode(text, position)
        position = _skip_space(text, position)
        if text[position] == ",":
            position += 1


def _skip_space(text: str, position: int) -> int:
    while text[position] in " \t\r\n":
        position += 1
    return position


def _array_items(
    text: str, position: int, decoder: json.JSONDecoder
) -> tuple[str, ...]:
    items: list[str] = []
    while True:
        position = _skip_space(text, position)
        if text[position] == "]":
            return tuple(items)
        start = position
        _, position = decoder.raw_decode(text, position)
        items.append(text[start:position])
        position = _skip_space(text, position)
        if text[position] == ",":
            position += 1


def _validate_job(job: dict[str, Any]) -> None:
    if type(job.get("id")) is not int or not 1 <= job["id"] <= 2**63 - 1:
        raise ValueError("Expected a positive source identity")
    for name, limit in (
        ("jobTitle", 500),
        ("companyName", 500),
        ("jobGeo", 2000),
        ("jobLevel", 500),
        ("jobExcerpt", 5000),
    ):
        if name in job or name in {"jobTitle", "companyName"}:
            value = job.get(name)
            if type(value) is not str or len(value) > limit:
                raise ValueError("Invalid bounded job field")
            require_text(value)
    if type(job.get("jobDescription")) is not str:
        raise ValueError("Job description must be HTML text")
    for name in ("jobIndustry", "jobType"):
        if name in job:
            values = job[name]
            if type(values) is not list or len(values) > 50:
                raise ValueError("Invalid job label list")
            for value in values:
                if type(value) is not str or len(value) > 200:
                    raise ValueError("Invalid job label")
                require_text(value)
    published = job.get("pubDate")
    if (
        type(published) is not str
        or datetime.fromisoformat(published).utcoffset() is None
    ):
        raise ValueError("Publication time must be timezone-aware")
    url = job.get("url")
    if type(url) is not str:
        raise ValueError("Job URL is required")
    require_public_url(url)
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.netloc != "jobicy.com"
        or not parts.path.startswith("/jobs/")
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Expected a canonical public Jobicy listing URL")


def _map_jobs(
    payload: dict[str, Any], text: str, decoder: json.JSONDecoder, query: JobicyQuery
) -> tuple[RawEnvelope, ...]:
    jobs = payload.get("jobs")
    if type(jobs) is not list or len(jobs) > query.count:
        raise ValueError("Invalid jobs array or page size")
    if type(payload.get("jobCount")) is not int or payload["jobCount"] != len(jobs):
        raise ValueError("Job count must agree with page")
    raw_jobs = _raw_jobs(text, decoder)
    envelopes: list[RawEnvelope] = []
    for job, raw in zip(jobs, raw_jobs, strict=True):
        if type(job) is not dict:
            raise ValueError("Job must be an object")
        _validate_job(job)
        envelopes.append(RawEnvelope("jobicy", str(job["id"]), job["url"], raw))
    return tuple(envelopes)


def _next_checkpoint(
    payload: dict[str, Any], metadata: FetchMetadata, checkpoint: Checkpoint | None
) -> Checkpoint | None:
    if "nextCursor" not in payload or type(payload.get("hasMore")) is not bool:
        raise ValueError("Pagination fields are required")
    token = payload["nextCursor"]
    if payload["hasMore"] != (token is not None):
        raise ValueError("Pagination indicators disagree")
    if token is None:
        return None
    expiry = (
        checkpoint.expires_at
        if checkpoint is not None
        else metadata.started_at + timedelta(hours=24)
    )
    return Checkpoint("jobicy", metadata.query_key, token, expiry)


def map_jobicy_response(
    body: bytes,
    metadata: FetchMetadata,
    query: JobicyQuery,
    checkpoint: Checkpoint | None = None,
) -> ConnectorBatch:
    """Map one public page or raise a sanitized INVALID_RESPONSE failure."""
    try:
        if (
            type(body) is not bytes
            or len(body) > MAX_BATCH_BYTES
            or len(body) != metadata.response_bytes
        ):
            raise ValueError("Response byte count mismatch or size limit")
        if (
            metadata.query_key != query.query_key
            or metadata.request_url != query.request_url(checkpoint)
        ):
            raise ValueError("Fetch metadata must describe this query")
        text = body.decode("utf-8")
        decoder = json.JSONDecoder(
            object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        payload = decoder.decode(text)
        _validate_json_depth(payload)
        if (
            type(payload) is not dict
            or payload.get("success") is not True
            or type(payload.get("statusCode")) is not int
            or payload["statusCode"] != metadata.status_code
        ):
            raise ValueError("Expected a successful Jobicy response")
        if type(payload.get("apiVersion")) is not str or not re.fullmatch(
            r"2\.[0-9]+\.[0-9]+", payload["apiVersion"]
        ):
            raise ValueError("Unsupported Jobicy API version")
        jobs = _map_jobs(payload, text, decoder, query)
        source_metadata = {
            key: value for key, value in payload.items() if key != "jobs"
        }
        metadata = replace(
            metadata,
            source_metadata_json=json.dumps(
                source_metadata,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
        )
        return ConnectorBatch(
            JOBICY_POLICY,
            metadata,
            jobs,
            checkpoint,
            _next_checkpoint(payload, metadata, checkpoint),
        )
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ConnectorError(
            ConnectorFailure("jobicy", FailureCode.INVALID_RESPONSE)
        ) from None
