"""Replay reviewed recordings through the production connector interface."""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Self

from borderless.domain import Value, require_text

from .contracts import (
    Checkpoint,
    ConnectorBatch,
    ConnectorError,
    ConnectorFailure,
    FailureCode,
)

MAX_RECORDING_BYTES = 20_000_000
MAX_RECORDING_PAGES = 100


class FixtureKind(StrEnum):
    SYNTHETIC = "synthetic"
    LICENSED = "licensed"
    TRANSFORMED = "transformed"


@dataclass(frozen=True, slots=True)
class FixtureProvenance(Value):
    kind: FixtureKind
    origin: str
    license: str
    notes: str

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for value in (self.origin, self.license, self.notes):
            require_text(value)


@dataclass(frozen=True, slots=True)
class FixtureConnector(Value):
    """Immutable traversal: repeated requests replay the same recorded page."""

    provenance: FixtureProvenance
    batches: tuple[ConnectorBatch, ...]

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if not 1 <= len(self.batches) <= MAX_RECORDING_PAGES:
            raise ValueError("Recording requires a bounded complete traversal")
        previous: Checkpoint | None = None
        seen: set[str] = set()
        first = self.batches[0]
        for index, batch in enumerate(self.batches):
            if (
                batch.policy != first.policy
                or batch.metadata.query_key != first.metadata.query_key
            ):
                raise ValueError("Recording policy and query must remain unchanged")
            if batch.requested_checkpoint != previous or (index and previous is None):
                raise ValueError("Recording pages must form one connected traversal")
            previous = batch.next_checkpoint
            if previous is not None:
                if previous.token in seen:
                    raise ValueError("Recording contains a cursor cycle")
                seen.add(previous.token)
        if previous is not None:
            raise ValueError("Recording must include the terminal page")

    @classmethod
    def load(cls, path: Path) -> Self:
        """Read a bounded UTF-8 recording; never expose file contents in errors."""
        try:
            with path.open("rb") as recording:
                raw = recording.read(MAX_RECORDING_BYTES + 1)
            if len(raw) > MAX_RECORDING_BYTES:
                raise ValueError("Recording exceeds byte limit")
            return cls.from_dict(json.loads(raw.decode("utf-8")))
        except (OSError, ValueError, RecursionError):
            raise ConnectorError(
                ConnectorFailure("fixture", FailureCode.INVALID_RESPONSE)
            ) from None

    def fetch(self, checkpoint: Checkpoint | None = None) -> ConnectorBatch:
        for batch in self.batches:
            if batch.requested_checkpoint == checkpoint:
                return batch
        raise ConnectorError(
            ConnectorFailure(
                self.batches[0].policy.source_id, FailureCode.INVALID_CHECKPOINT
            )
        )
