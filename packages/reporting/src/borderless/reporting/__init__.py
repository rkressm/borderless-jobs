"""Public canonical report values, independent of presentation frameworks."""

from .builder import ReportBuilder
from .contracts import (
    DataFreshness,
    JobResult,
    RuleTrace,
    SearchReport,
    SourceAttribution,
)

__all__ = [
    "ReportBuilder",
    "DataFreshness",
    "JobResult",
    "RuleTrace",
    "SearchReport",
    "SourceAttribution",
]
