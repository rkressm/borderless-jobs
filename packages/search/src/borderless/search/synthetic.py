"""Offline demonstration adapter; assessments are fixtures, never computed policy."""

from dataclasses import replace
from datetime import UTC, datetime

from borderless.domain import (
    CountryCode,
    DimensionalDecision,
    Evidence,
    FactProvenance,
    GlobalVerdict,
    PolicyVersion,
    SchemaVersion,
)

from .contracts import ResultOrderKey, SearchSpecification
from .results import (
    SearchFact,
    SearchJob,
    SearchResultPage,
    SearchRuleTrace,
    SearchSource,
)

_OBSERVED_AT = datetime(2026, 10, 1, tzinfo=UTC)
_POLICY = PolicyVersion("1.0.0")
_SOURCE = SearchSource(
    "synthetic",
    "Synthetic jobs",
    "https://example.org",
    "Invented demonstration data; not actual job listings.",
    _OBSERVED_AT,
)
_PROVENANCE = FactProvenance(
    "synthetic", "walking-skeleton", "1.0.0", SchemaVersion("1.0.0")
)


def _job(
    number: int, role: str, countries: tuple[str, ...], *, missing: bool = False
) -> SearchJob:
    identity = f"synthetic-{number:02}"
    version = f"{identity}-v1"
    url = f"https://example.org/jobs/{identity}"
    text = "Remote"
    evidence = (
        ()
        if missing
        else (Evidence(version, "synthetic-1.0.0", 0, len(text), text, url),)
    )
    for item in evidence:
        item.verify(text)
    unknowns: tuple[str, ...] = (
        "candidate-country permission",
        "engagement mechanism",
        "timezone requirements",
    )
    if missing:
        unknowns += ("supporting evidence unavailable",)
    trace = tuple(
        SearchRuleTrace(
            f"synthetic.{dimension}.unverified",
            _POLICY,
            dimension,
            DimensionalDecision.UNKNOWN,
            (),
            "Prebuilt synthetic assessment: required facts are unverified.",
            evidence if dimension == "geography" else (),
        )
        for dimension in ("geography", "engagement", "timezone")
    )
    return SearchJob(
        identity,
        version,
        role.replace("-", " ").title(),
        "Société synthétique",
        "synthetic",
        url,
        datetime(2026, 9, 30 if number <= 2 else 29, tzinfo=UTC),
        _OBSERVED_AT,
        _POLICY,
        GlobalVerdict.UNCERTAIN,
        DimensionalDecision.UNKNOWN,
        DimensionalDecision.UNKNOWN,
        DimensionalDecision.UNKNOWN,
        evidence,
        trace,
        unknowns,
        (),
        (_PROVENANCE,),
        role,
        tuple(CountryCode(country) for country in countries),
        (SearchFact("geography", text, evidence, _PROVENANCE),),
    )


# Deliberately unsorted: equal publication times exercise the stable ID tie-breaker.
_JOBS = (
    _job(3, "data-engineer", ("BO",), missing=True),
    _job(2, "data-engineer", ("BO",)),
    _job(1, "data-engineer", ("BO", "FR")),
    _job(4, "designer", ("BO",)),
)


class SyntheticSearchAdapter:
    """Exact normalized role/candidate coverage; immutable prebuilt uncertain fixtures."""

    def search(self, specification: SearchSpecification) -> SearchResultPage:
        sources = (
            (_SOURCE,)
            if _OBSERVED_AT <= specification.as_of
            and (not specification.sources or "synthetic" in specification.sources)
            else ()
        )
        matches = [job for job in _JOBS if sources and _matches(job, specification)]
        matches.sort(
            key=lambda job: ResultOrderKey(job.published_at, job.job_id).sort_key()
        )
        start = specification.offset
        jobs = tuple(
            replace(job, assessed_at=specification.as_of)
            for job in matches[start : start + specification.limit]
        )
        return SearchResultPage(specification, jobs, len(matches), sources)


def _matches(job: SearchJob, specification: SearchSpecification) -> bool:
    return (
        job.role == specification.role
        and specification.country in job.countries
        and job.published_at <= specification.as_of
        and (not specification.verdicts or job.verdict in specification.verdicts)
    )
