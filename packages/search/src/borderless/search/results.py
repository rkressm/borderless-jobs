"""Storage-neutral search snapshots of facts and existing assessments."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from borderless.domain import (
    CountryCode,
    DimensionalDecision,
    Evidence,
    FactProvenance,
    GlobalVerdict,
    PolicyVersion,
    Value,
    require_public_url,
    require_text,
)

from .contracts import ResultOrderKey, SearchSpecification


@dataclass(frozen=True, slots=True)
class SearchFact(Value):
    dimension: str
    value: str
    evidence: tuple[Evidence, ...]
    provenance: FactProvenance

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if self.dimension not in {"geography", "engagement", "timezone"}:
            raise ValueError("Unknown fact dimension")
        require_text(self.value)


@dataclass(frozen=True, slots=True)
class SearchRuleTrace(Value):
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
class SearchJob(Value):
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
    trace: tuple[SearchRuleTrace, ...]
    unknowns: tuple[str, ...]
    contradictions: tuple[str, ...]
    provenance: tuple[FactProvenance, ...]
    role: str
    countries: tuple[CountryCode, ...]
    facts: tuple[SearchFact, ...]

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
        if (
            not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.role)
            or len(self.role) > 100
            or not self.countries
        ):
            raise ValueError("Job requires canonical role and candidate countries")
        if not self.trace or not self.provenance:
            raise ValueError("Assessment requires trace and provenance")
        if self.verdict is GlobalVerdict.UNCERTAIN and not (
            self.unknowns or self.contradictions
        ):
            raise ValueError("Uncertainty requires an explanation")
        if any(entry.policy_version != self.policy_version for entry in self.trace):
            raise ValueError("Trace policy must match assessment")
        evidence = (
            *self.evidence,
            *(item for entry in self.trace for item in entry.evidence),
            *(item for fact in self.facts for item in fact.evidence),
        )
        if any(item.job_version_id != self.job_version_id for item in evidence):
            raise ValueError("Evidence must target the job version")


@dataclass(frozen=True, slots=True)
class SearchSource(Value):
    source_id: str
    name: str
    url: str
    notice: str
    observed_at: datetime

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for value in (self.source_id, self.name, self.notice):
            require_text(value)
        require_public_url(self.url)


@dataclass(frozen=True, slots=True)
class SearchResultPage(Value):
    specification: SearchSpecification
    jobs: tuple[SearchJob, ...]
    total: int
    sources: tuple[SearchSource, ...]

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        expected = min(
            self.specification.limit, max(0, self.total - self.specification.offset)
        )
        if self.total < 0 or len(self.jobs) != expected:
            raise ValueError("Page count must match total and pagination")
        ids = [job.job_id for job in self.jobs]
        keys = [
            ResultOrderKey(job.published_at, job.job_id).sort_key() for job in self.jobs
        ]
        if len(ids) != len(set(ids)) or keys != sorted(keys):
            raise ValueError("Page requires unique jobs in canonical order")
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("Duplicate source metadata")
        if any(
            source.observed_at > self.specification.as_of for source in self.sources
        ):
            raise ValueError("Source observation cannot follow as-of")
        for job in self.jobs:
            if (
                job.source_id not in source_ids
                or job.assessed_at != self.specification.as_of
            ):
                raise ValueError(
                    "Job requires source metadata and matching assessment time"
                )
            if (
                job.role != self.specification.role
                or self.specification.country not in job.countries
                or (
                    self.specification.sources
                    and job.source_id not in self.specification.sources
                )
                or (
                    self.specification.verdicts
                    and job.verdict not in self.specification.verdicts
                )
            ):
                raise ValueError("Job must satisfy the requested filters")
            if job.published_at > self.specification.as_of:
                raise ValueError("Job publication cannot follow as-of")


class JobSearch(Protocol):
    def search(self, specification: SearchSpecification) -> SearchResultPage: ...
