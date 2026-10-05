"""Application use case projecting search snapshots into the canonical report."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from datetime import datetime

from borderless.domain import PolicyVersion, SchemaVersion
from borderless.search import JobSearch, SearchJob, SearchSpecification

from .contracts import DataFreshness, JobResult, SearchReport, SourceAttribution


@dataclass(frozen=True, slots=True)
class ReportBuilder:
    search: JobSearch
    clock: Callable[[], datetime]
    policy_version: PolicyVersion
    schema_version: SchemaVersion

    def build(self, specification: SearchSpecification) -> SearchReport:
        created_at = self.clock()
        page = self.search.search(specification)
        if page.specification != specification:
            raise ValueError("Search response must correspond to the requested query")
        sources = sorted(page.sources, key=lambda source: source.source_id)
        report = SearchReport(
            report_id="pending",
            created_at=created_at,
            schema_version=self.schema_version,
            policy_version=self.policy_version,
            specification=specification,
            freshness=tuple(
                DataFreshness(source.source_id, source.observed_at)
                for source in sources
            ),
            attributions=tuple(
                SourceAttribution(
                    source.source_id, source.name, source.url, source.notice
                )
                for source in sources
            ),
            jobs=tuple(_project_job(job) for job in page.jobs),
            total=page.total,
        )
        return replace(report, report_id=_report_identity(report))


def _project_job(job: SearchJob) -> JobResult:
    """Copy public assessment fields; facts/coverage remain search-owned."""
    snapshot = job.to_dict()
    return JobResult.from_dict(
        {field.name: snapshot[field.name] for field in fields(JobResult)}
    )


def _report_identity(report: SearchReport) -> str:
    data = report.to_dict()
    del data["report_id"]
    canonical = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return "report-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
