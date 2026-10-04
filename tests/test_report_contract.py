"""Canonical report contract across domain, search and reporting packages."""

import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest
from borderless.domain import (
    CountryCode,
    DimensionalDecision,
    Evidence,
    FactProvenance,
    GlobalVerdict,
    PolicyVersion,
    SchemaVersion,
)
from borderless.reporting import (
    DataFreshness,
    JobResult,
    RuleTrace,
    SearchReport,
    SourceAttribution,
)
from borderless.search import SearchSpecification

NOW = datetime(2026, 10, 4, tzinfo=UTC)
POLICY = PolicyVersion("1.0.0")
SCHEMA = SchemaVersion("1.0.0")


def sample_report() -> SearchReport:
    evidence = Evidence("job-v1", "n1", 0, 6, "Remote", "https://example.org/job")
    trace = RuleTrace(
        "geography.missing-country",
        POLICY,
        "geography",
        DimensionalDecision.UNKNOWN,
        ("remote",),
        "Remote alone does not establish permission.",
        (evidence,),
    )
    job = JobResult(
        "job-1",
        "job-v1",
        "Data engineer",
        "Société",
        "synthetic",
        "https://example.org/job",
        NOW,
        NOW,
        POLICY,
        GlobalVerdict.UNCERTAIN,
        DimensionalDecision.UNKNOWN,
        DimensionalDecision.UNKNOWN,
        DimensionalDecision.NOT_APPLICABLE,
        (evidence,),
        (trace,),
        ("candidate-country permission", "engagement"),
        (),
        (FactProvenance("synthetic", "fixture", "1.0.0", SCHEMA),),
    )
    return SearchReport(
        "report-1",
        NOW,
        SCHEMA,
        POLICY,
        SearchSpecification("data-engineer", CountryCode("BO"), NOW, 0, 10),
        (DataFreshness("synthetic", NOW),),
        (
            SourceAttribution(
                "synthetic",
                "Synthetic jobs",
                "https://example.org",
                "Synthetic demonstration",
            ),
        ),
        (job,),
        1,
    )


def encode(report: SearchReport) -> str:
    return json.dumps(
        report.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def test_report_round_trip_is_deterministic_and_preserves_versions() -> None:
    report = sample_report()
    encoded = encode(report)
    decoded = SearchReport.from_dict(json.loads(encoded))
    assert decoded == report
    assert encode(decoded) == encoded
    assert decoded.schema_version == SCHEMA
    assert decoded.policy_version == POLICY
    assert decoded.jobs[0].trace[0].policy_version == POLICY
    assert "Société" in encoded
    assert decoded.jobs[0].evidence[0].quote == "Remote"
    assert decoded.jobs[0].unknowns
    with pytest.raises(FrozenInstanceError):
        report.total = 2  # type: ignore[misc]


def test_empty_report_keeps_search_and_source_metadata() -> None:
    report = replace(sample_report(), jobs=(), total=0)
    assert SearchReport.from_dict(report.to_dict()) == report


@pytest.mark.parametrize(
    "changes",
    [
        dict(schema_version=SchemaVersion("2.0.0")),
        dict(policy_version=PolicyVersion("2.0.0")),
        dict(total=0),
        dict(total=True),
        dict(attributions=()),
        dict(freshness=()),
        dict(jobs=[]),
        dict(created_at=datetime(2026, 10, 3, tzinfo=UTC)),
    ],
)
def test_report_rejects_inconsistent_contracts(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        replace(sample_report(), **changes)  # type: ignore[arg-type]


def test_job_requires_evidence_version_trace_unknowns_and_safe_links() -> None:
    job = sample_report().jobs[0]
    for changes in [
        dict(trace=()),
        dict(unknowns=()),
        dict(canonical_url="javascript:x"),
        dict(job_version_id="another-version"),
        dict(provenance=()),
    ]:
        with pytest.raises(ValueError):
            replace(job, **changes)  # type: ignore[arg-type]


def test_order_uniqueness_and_page_size_are_contract_invariants() -> None:
    report = sample_report()
    job = report.jobs[0]
    with pytest.raises(ValueError):
        replace(report, jobs=(job, job), total=2)
    second = replace(job, job_id="job-2")
    with pytest.raises(ValueError):
        replace(report, jobs=(second, job), total=2)
    with pytest.raises(ValueError):
        replace(
            report,
            specification=replace(report.specification, limit=1),
            jobs=(job, second),
            total=2,
        )


def test_untrusted_nested_data_is_rejected() -> None:
    for change in ("extra", "verdict", "offset", "timestamp", "provenance"):
        data = sample_report().to_dict()
        if change == "extra":
            data["jobs"][0]["private_raw_html"] = "<script>secret</script>"
        elif change == "verdict":
            data["jobs"][0]["verdict"] = "PROBABLY"
        elif change == "offset":
            data["jobs"][0]["evidence"][0]["start"] = True
        elif change == "timestamp":
            data["created_at"] = "2026-10-04T00:00:00"
        else:
            data["jobs"][0]["provenance"][0]["schema_version"]["value"] = "invalid"
        with pytest.raises(ValueError):
            SearchReport.from_dict(data)
