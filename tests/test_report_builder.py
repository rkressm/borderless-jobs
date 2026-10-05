"""Report use case across the real offline search and canonical report seams."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from borderless.domain import CountryCode, GlobalVerdict, PolicyVersion, SchemaVersion
from borderless.reporting import ReportBuilder, SearchReport
from borderless.search import (
    SearchResultPage,
    SearchSpecification,
    SyntheticSearchAdapter,
)

NOW = datetime(2026, 10, 5, tzinfo=UTC)


def specification() -> SearchSpecification:
    return SearchSpecification("data-engineer", CountryCode("BO"), NOW, 0, 10)


def builder() -> ReportBuilder:
    return ReportBuilder(
        SyntheticSearchAdapter(),
        lambda: NOW,
        PolicyVersion("1.0.0"),
        SchemaVersion("1.0.0"),
    )


def encode(report: SearchReport) -> bytes:
    return json.dumps(
        report.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def test_frozen_clock_produces_byte_stable_complete_report() -> None:
    use_case = builder()
    report = use_case.build(specification())
    assert encode(report) == encode(use_case.build(specification()))
    assert SearchReport.from_dict(json.loads(encode(report))) == report
    assert report.created_at == NOW
    assert report.policy_version == PolicyVersion("1.0.0")
    assert report.schema_version == SchemaVersion("1.0.0")
    assert report.freshness[0].observed_at == datetime(2026, 10, 1, tzinfo=UTC)
    assert report.attributions[0].notice.startswith("Invented")
    assert report.total == 3
    for job, hit in zip(
        report.jobs, SyntheticSearchAdapter().search(specification()).jobs, strict=True
    ):
        assert job.verdict == hit.verdict
        assert job.evidence == hit.evidence
        assert job.unknowns == hit.unknowns
        assert job.provenance == hit.provenance
        assert [entry.to_dict() for entry in job.trace] == [
            entry.to_dict() for entry in hit.trace
        ]
    assert "Société".encode() in encode(report)


def test_missing_evidence_stays_visible_without_inventing_permission() -> None:
    job = builder().build(specification()).jobs[2]
    assert job.evidence == ()
    assert all(entry.evidence == () for entry in job.trace)
    assert "supporting evidence unavailable" in job.unknowns
    assert job.verdict is GlobalVerdict.UNCERTAIN


def test_empty_and_paginated_reports_keep_totals_and_metadata() -> None:
    page = builder().build(replace(specification(), offset=1, limit=1))
    assert page.total == 3
    assert page.jobs[0].job_id == "synthetic-02"
    empty = builder().build(replace(specification(), role="astronaut"))
    assert empty.total == 0 and empty.jobs == ()
    assert empty.attributions and empty.freshness
    beyond = builder().build(replace(specification(), offset=99))
    assert beyond.total == 3 and beyond.jobs == ()
    assert page.report_id != empty.report_id


def test_clock_is_explicit_called_once_and_changes_snapshot_identity() -> None:
    calls: list[int] = []

    def clock() -> datetime:
        calls.append(1)
        return NOW + timedelta(seconds=1)

    use_case = replace(builder(), clock=clock)
    report = use_case.build(specification())
    assert calls == [1]
    assert report.created_at == NOW + timedelta(seconds=1)
    assert report.report_id != builder().build(specification()).report_id


@pytest.mark.parametrize(
    "instant", [NOW.replace(tzinfo=None), NOW - timedelta(seconds=1)]
)
def test_invalid_clock_fails_closed(instant: datetime) -> None:
    with pytest.raises(ValueError):
        replace(builder(), clock=lambda: instant).build(specification())


def test_version_mismatch_and_unsupported_schema_are_rejected() -> None:
    with pytest.raises(ValueError):
        replace(builder(), policy_version=PolicyVersion("2.0.0")).build(specification())
    with pytest.raises(ValueError):
        replace(builder(), schema_version=SchemaVersion("2.0.0")).build(specification())


def test_adapter_cannot_substitute_another_query() -> None:
    class WrongQuery:
        def search(self, query: SearchSpecification) -> SearchResultPage:
            return SyntheticSearchAdapter().search(replace(query, role="designer"))

    with pytest.raises(ValueError):
        replace(builder(), search=WrongQuery()).build(specification())
