from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from borderless.domain import (
    DimensionalDecision,
    Evidence,
    FactProvenance,
    SchemaVersion,
)
from borderless.eligibility import TimezoneFact, WorkingWindow, evaluate_timezone

ZONES = {name: ZoneInfo(name) for name in ("America/La_Paz", "America/New_York", "UTC")}
PROVENANCE = FactProvenance("reviewed", "test", "1.0.0", SchemaVersion("1.0.0"))
EVIDENCE = Evidence("v1", "1.0.0", 0, 7, "overlap", "https://example.org/job")


def constraint(
    start: int, end: int, minimum: int = 60, mandatory: bool = True
) -> TimezoneFact:
    return TimezoneFact(
        WorkingWindow("America/New_York", start, end),
        minimum,
        mandatory,
        EVIDENCE,
        PROVENANCE,
    )


@pytest.mark.parametrize(
    ("date", "expected"),
    [
        ("2026-03-07", DimensionalDecision.FAIL),
        ("2026-03-08", DimensionalDecision.PASS),
        ("2026-11-01", DimensionalDecision.FAIL),
    ],
)
def test_dst_changes_overlap_at_frozen_date(
    date: str, expected: DimensionalDecision
) -> None:
    result = evaluate_timezone(
        datetime.fromisoformat(date).replace(hour=12, tzinfo=UTC),
        WorkingWindow("America/La_Paz", 540, 600),
        (constraint(540, 600),),
        zones=ZONES,
    )
    assert result.outcome is expected
    assert type(result).from_dict(result.to_dict()) == result


def test_overnight_and_absent_and_preferences() -> None:
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    available = WorkingWindow("America/La_Paz", 1380, 120)
    assert (
        evaluate_timezone(now, available, (constraint(0, 60),), zones=ZONES).outcome
        is DimensionalDecision.PASS
    )
    assert (
        evaluate_timezone(now, None, zones={}).outcome
        is DimensionalDecision.NOT_APPLICABLE
    )
    assert (
        evaluate_timezone(
            now, available, (constraint(0, 60, mandatory=False),), zones=ZONES
        ).outcome
        is DimensionalDecision.UNKNOWN
    )
    assert (
        evaluate_timezone(now, None, (constraint(0, 60),), zones=ZONES).outcome
        is DimensionalDecision.UNKNOWN
    )


@pytest.mark.parametrize(("start", "end"), [(-1, 60), (0, 1440), (60, 60)])
def test_invalid_windows(start: int, end: int) -> None:
    with pytest.raises(ValueError):
        WorkingWindow("UTC", start, end)


def test_missing_zone_and_naive_time_rejected() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert (
        evaluate_timezone(
            now, WorkingWindow("UTC", 0, 60), (constraint(0, 60),), zones={}
        ).outcome
        is DimensionalDecision.UNKNOWN
    )
    with pytest.raises(ValueError):
        evaluate_timezone(now.replace(tzinfo=None), None, zones={})


@pytest.mark.parametrize(("date", "overlap"), [("2026-03-08", 0), ("2026-11-01", 120)])
def test_skipped_and_repeated_wall_minutes(date: str, overlap: int) -> None:
    start, end = (120, 180) if overlap == 0 else (60, 120)
    window = WorkingWindow("America/New_York", start, end)
    fact = TimezoneFact(window, 60, True, EVIDENCE, PROVENANCE)
    result = evaluate_timezone(
        datetime.fromisoformat(date).replace(hour=12, tzinfo=UTC),
        window,
        (fact,),
        zones=ZONES,
    )
    assert result.overlap_minutes == (overlap,)


def test_long_overnight_window_in_negative_offset_zone() -> None:
    name = "Etc/GMT+12"
    window = WorkingWindow(name, 1439, 1438)
    fact = TimezoneFact(window, 1439, True, EVIDENCE, PROVENANCE)
    result = evaluate_timezone(
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        window,
        (fact,),
        zones={name: ZoneInfo(name)},
    )
    assert result.overlap_minutes == (1439,)
    assert result.outcome is DimensionalDecision.PASS


def test_unresolved_fact_cannot_weaken_impossible_overlap() -> None:
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    vague = TimezoneFact(None, 60, False, EVIDENCE, PROVENANCE)
    result = evaluate_timezone(
        now, WorkingWindow("UTC", 0, 60), (constraint(540, 600), vague), zones=ZONES
    )
    assert result.outcome is DimensionalDecision.FAIL


def test_unknown_window_and_mislabeled_zone_cannot_pass() -> None:
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    missing = TimezoneFact(None, 60, True, EVIDENCE, PROVENANCE)
    available = WorkingWindow("UTC", 0, 60)
    assert (
        evaluate_timezone(now, available, (missing,), zones=ZONES).outcome
        is DimensionalDecision.UNKNOWN
    )
    zones = {**ZONES, "America/New_York": ZoneInfo("UTC")}
    assert (
        evaluate_timezone(now, available, (constraint(0, 60),), zones=zones).outcome
        is DimensionalDecision.UNKNOWN
    )


def test_timezone_limits_and_policy_version() -> None:
    from borderless.domain import PolicyVersion

    for minimum in (0, 1441):
        with pytest.raises(ValueError, match="Overlap"):
            TimezoneFact(None, minimum, True, EVIDENCE, PROVENANCE)
    with pytest.raises(ValueError, match="policy"):
        evaluate_timezone(
            datetime(2026, 1, 1, tzinfo=UTC),
            None,
            zones={},
            policy_version=PolicyVersion("2.0.0"),
        )
