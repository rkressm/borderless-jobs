"""Minute-resolution daily overlap using caller-loaded IANA timezone data."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, tzinfo

from borderless.domain import (
    DimensionalDecision,
    Evidence,
    FactProvenance,
    PolicyVersion,
    Value,
    require_text,
)

from .geographic_policy import _ordered

_TIMEZONE_POLICY_VERSION = PolicyVersion("1.0.0")


@dataclass(frozen=True, slots=True)
class WorkingWindow(Value):
    zone: str
    start_minute: int
    end_minute: int

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        require_text(self.zone)
        if not (0 <= self.start_minute < 1440 and 0 <= self.end_minute < 1440):
            raise ValueError("Window minutes must be within a day")
        if self.start_minute == self.end_minute:
            raise ValueError("Equal endpoints are ambiguous; specify a nonempty window")

    def contains(self, minute: int) -> bool:
        if self.start_minute < self.end_minute:
            return self.start_minute <= minute < self.end_minute
        return minute >= self.start_minute or minute < self.end_minute


@dataclass(frozen=True, slots=True)
class TimezoneFact(Value):
    window: WorkingWindow | None
    minimum_minutes: int
    mandatory: bool
    evidence: Evidence
    provenance: FactProvenance

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if not 1 <= self.minimum_minutes <= 1440:
            raise ValueError("Overlap must be between 1 and 1440 minutes")


@dataclass(frozen=True, slots=True)
class TimezoneDecision(Value):
    outcome: DimensionalDecision
    rule_id: str
    policy_version: PolicyVersion
    as_of: datetime
    availability: WorkingWindow | None
    facts: tuple[TimezoneFact, ...]
    overlap_minutes: tuple[int, ...]
    explanation: str


def _overlap(
    as_of: datetime,
    available: WorkingWindow,
    required: WorkingWindow,
    zones: Mapping[str, tzinfo],
) -> int:
    """Count actual UTC minutes; repeated/skipped wall times follow IANA rules."""
    required_zone, candidate_zone = zones[required.zone], zones[available.zone]
    anchor = as_of.astimezone(required_zone).date()
    start = datetime(anchor.year, anchor.month, anchor.day, tzinfo=UTC) - timedelta(
        days=1
    )
    count = 0
    overnight = required.start_minute > required.end_minute
    for offset in range(4 * 1440):
        instant = start + timedelta(minutes=offset)
        local = instant.astimezone(required_zone)
        minute = local.hour * 60 + local.minute
        day = anchor + timedelta(days=int(overnight and minute < required.end_minute))
        if local.date() != day or not required.contains(minute):
            continue
        candidate = instant.astimezone(candidate_zone)
        count += available.contains(candidate.hour * 60 + candidate.minute)
    return count


def evaluate_timezone(
    as_of: datetime,
    availability: WorkingWindow | None,
    facts: tuple[TimezoneFact, ...] = (),
    *,
    zones: Mapping[str, tzinfo],
    policy_version: PolicyVersion = _TIMEZONE_POLICY_VERSION,
) -> TimezoneDecision:
    """Zones must be preloaded IANA tzinfo objects; this function never loads them."""
    if as_of.utcoffset() is None:
        raise ValueError("Expected a timezone-aware as_of")
    if policy_version != PolicyVersion("1.0.0"):
        raise ValueError("Unsupported timezone policy version")
    facts = _ordered(facts)
    overlaps = tuple(
        _overlap(as_of, availability, fact.window, zones)
        if availability is not None
        and fact.window is not None
        and getattr(zones.get(availability.zone), "key", None) == availability.zone
        and getattr(zones.get(fact.window.zone), "key", None) == fact.window.zone
        else -1
        for fact in facts
    )
    if any(
        fact.mandatory and 0 <= overlap < fact.minimum_minutes
        for fact, overlap in zip(facts, overlaps, strict=True)
    ):
        outcome, rule, explanation = (
            DimensionalDecision.FAIL,
            "overlap.impossible",
            "Mandatory overlap cannot be satisfied.",
        )
    elif any(
        not fact.mandatory or overlap < 0
        for fact, overlap in zip(facts, overlaps, strict=True)
    ):
        outcome, rule, explanation = (
            DimensionalDecision.UNKNOWN,
            "overlap.unresolved",
            "Preference, available hours or timezone data requires clarification.",
        )
    elif facts:
        outcome, rule, explanation = (
            DimensionalDecision.PASS,
            "overlap.satisfied",
            "All explicit mandatory overlaps are satisfied.",
        )
    else:
        outcome, rule, explanation = (
            DimensionalDecision.NOT_APPLICABLE,
            "constraint.absent",
            "No stated timezone constraint.",
        )
    return TimezoneDecision(
        outcome,
        f"timezone.{rule}",
        policy_version,
        as_of,
        availability,
        facts,
        overlaps,
        explanation,
    )
