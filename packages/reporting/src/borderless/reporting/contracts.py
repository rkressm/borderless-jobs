"""Immutable public report snapshots; no rendering or eligibility evaluation."""

from dataclasses import dataclass
from datetime import datetime

from borderless.domain import (
    DimensionalDecision,
    Evidence,
    FactProvenance,
    GlobalVerdict,
    PolicyVersion,
    SchemaVersion,
    Value,
    require_public_url,
    require_text,
)
from borderless.search import ResultOrderKey, SearchSpecification


@dataclass(frozen=True, slots=True)
class DataFreshness(Value):
    source_id: str
    observed_at: datetime

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        require_text(self.source_id)


@dataclass(frozen=True, slots=True)
class SourceAttribution(Value):
    source_id: str
    name: str
    url: str
    notice: str

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for value in (self.source_id, self.name, self.notice):
            require_text(value)
        require_public_url(self.url)


@dataclass(frozen=True, slots=True)
class RuleTrace(Value):
    rule_id: str
    policy_version: PolicyVersion
    dimension: str
    outcome: DimensionalDecision
    inputs: tuple[str, ...]
    explanation: str
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if self.dimension not in {"geography", "engagement", "timezone"}:
            raise ValueError("Unknown decision dimension")
        for value in (self.rule_id, self.explanation, *self.inputs):
            require_text(value)


@dataclass(frozen=True, slots=True)
class JobResult(Value):
    job_id: str
    job_version_id: str
    title: str
    company: str
    source_id: str
    canonical_url: str
    published_at: datetime
    assessed_at: datetime
    policy_version: PolicyVersion
    verdict: GlobalVerdict
    geography: DimensionalDecision
    engagement: DimensionalDecision
    timezone: DimensionalDecision
    evidence: tuple[Evidence, ...]
    trace: tuple[RuleTrace, ...]
    unknowns: tuple[str, ...]
    contradictions: tuple[str, ...]
    provenance: tuple[FactProvenance, ...]

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for value in (
            self.job_id,
            self.job_version_id,
            self.title,
            self.company,
            self.source_id,
            *self.unknowns,
            *self.contradictions,
        ):
            require_text(value)
        require_public_url(self.canonical_url)
        if not self.trace or not self.provenance:
            raise ValueError(
                "Every job requires decision trace and extraction provenance"
            )
        if self.verdict is GlobalVerdict.UNCERTAIN and not (
            self.unknowns or self.contradictions
        ):
            raise ValueError("Uncertainty must remain explained in the report")
        for entry in self.trace:
            if entry.policy_version != self.policy_version:
                raise ValueError("Trace and assessment policy versions must agree")
        for evidence in (
            *self.evidence,
            *(item for entry in self.trace for item in entry.evidence),
        ):
            if evidence.job_version_id != self.job_version_id:
                raise ValueError("Evidence must target this immutable job version")


@dataclass(frozen=True, slots=True)
class SearchReport(Value):
    report_id: str
    created_at: datetime
    schema_version: SchemaVersion
    policy_version: PolicyVersion
    specification: SearchSpecification
    freshness: tuple[DataFreshness, ...]
    attributions: tuple[SourceAttribution, ...]
    jobs: tuple[JobResult, ...]
    total: int
    disclaimer: str = "Informational eligibility assessment; not legal advice."

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        require_text(self.report_id)
        require_text(self.disclaimer)
        if self.schema_version != SchemaVersion("1.0.0"):
            raise ValueError("Unsupported report schema version")
        if self.created_at < self.specification.as_of:
            raise ValueError("Report creation cannot precede its as-of instant")
        if self.total < 0 or len(self.jobs) > self.specification.limit:
            raise ValueError("Invalid result count or page size")
        expected_count = min(
            self.specification.limit, max(0, self.total - self.specification.offset)
        )
        if len(self.jobs) != expected_count:
            raise ValueError("Page length must match total, offset and limit")
        ids = [job.job_id for job in self.jobs]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate job identity in report")
        keys = [
            ResultOrderKey(job.published_at, job.job_id).sort_key() for job in self.jobs
        ]
        if keys != sorted(keys):
            raise ValueError("Report must preserve canonical result order")
        sources = [item.source_id for item in self.attributions]
        fresh_sources = [item.source_id for item in self.freshness]
        if len(sources) != len(set(sources)) or len(fresh_sources) != len(
            set(fresh_sources)
        ):
            raise ValueError("Duplicate source metadata")
        if set(sources) != set(fresh_sources):
            raise ValueError("Every attributed source requires freshness metadata")
        if any(item.observed_at > self.specification.as_of for item in self.freshness):
            raise ValueError("Freshness cannot be later than the as-of instant")
        for job in self.jobs:
            if job.source_id not in sources:
                raise ValueError("Every job requires source attribution and freshness")
            if (
                job.policy_version != self.policy_version
                or job.assessed_at != self.specification.as_of
            ):
                raise ValueError("Assessment time and policy must match the report")
