"""Durable source-wide pass and Retry-After gates, isolated by worktree."""

import fcntl
import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from .contracts import FailureCode
from .http_transport import fail
from .policy import JOBICY_POLICY


class FilePollingGate:
    def __init__(self, path: Path) -> None:
        self.path = path

    def reserve(self, now: datetime) -> None:
        self._update(now, "reserve")

    def check_page(self, now: datetime) -> None:
        self._update(now, "check")

    def defer(self, until: datetime) -> None:
        self._update(until, "defer")

    def _update(
        self, now: datetime, mode: Literal["reserve", "check", "defer"]
    ) -> None:
        if now.utcoffset() is None:
            raise ValueError("Polling requires timezone-aware instants")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(descriptor, "r+", encoding="utf-8") as state:
                fcntl.flock(state, fcntl.LOCK_EX)
                next_pass, next_request = self._read_state(state.read(2049))
                barriers = (
                    [next_request, next_pass] if mode == "reserve" else [next_request]
                )
                for barrier in barriers:
                    if mode != "defer" and barrier is not None and now < barrier:
                        raise fail(
                            FailureCode.RATE_LIMITED,
                            math.ceil((barrier - now).total_seconds()),
                        )
                if mode == "reserve":
                    next_pass = now + timedelta(
                        seconds=JOBICY_POLICY.minimum_poll_interval_seconds
                    )
                if mode == "defer":
                    next_request = (
                        max(now, next_request) if next_request is not None else now
                    )
                os.fchmod(state.fileno(), 0o600)
                state.seek(0)
                state.write(
                    json.dumps(
                        {
                            "next_pass_at": next_pass.isoformat()
                            if next_pass
                            else None,
                            "next_request_at": next_request.isoformat()
                            if next_request
                            else None,
                        }
                    )
                )
                state.truncate()
                state.flush()
                os.fsync(state.fileno())
        except (OSError, ValueError):
            raise fail(FailureCode.TRANSPORT) from None

    @staticmethod
    def _read_state(text: str) -> tuple[datetime | None, datetime | None]:
        if not text:
            return None, None
        if len(text) > 2048:
            raise ValueError("Polling state is oversized")
        data = json.loads(text)
        if type(data) is not dict or set(data) != {"next_pass_at", "next_request_at"}:
            raise ValueError("Invalid polling state")
        values: list[datetime | None] = []
        for key in ("next_pass_at", "next_request_at"):
            if data[key] is None:
                values.append(None)
                continue
            if type(data[key]) is not str:
                raise ValueError("Invalid polling state time")
            instant = datetime.fromisoformat(data[key])
            if instant.utcoffset() is None:
                raise ValueError("Invalid polling state time")
            values.append(instant)
        return values[0], values[1]
