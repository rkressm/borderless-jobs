"""Source-neutral ingestion contracts and reviewed source governance."""

from .contracts import (
    Checkpoint,
    Connector,
    ConnectorBatch,
    ConnectorError,
    ConnectorFailure,
    FailureCode,
    FetchMetadata,
    RawEnvelope,
)
from .fixture import FixtureConnector, FixtureKind, FixtureProvenance
from .jobicy import JobicyQuery, map_jobicy_response
from .policy import JOBICY_POLICY, Redistribution, RemovalRule, SourcePolicy

__all__ = [
    "JOBICY_POLICY",
    "Checkpoint",
    "Connector",
    "ConnectorBatch",
    "ConnectorError",
    "ConnectorFailure",
    "FailureCode",
    "FetchMetadata",
    "FixtureConnector",
    "FixtureKind",
    "FixtureProvenance",
    "JobicyQuery",
    "map_jobicy_response",
    "RawEnvelope",
    "Redistribution",
    "RemovalRule",
    "SourcePolicy",
]
