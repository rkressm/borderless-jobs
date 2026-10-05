"""Public canonical report values, independent of presentation frameworks."""

from .builder import ReportBuilder
from .contracts import (
    DataFreshness,
    JobResult,
    RuleTrace,
    SearchReport,
    SourceAttribution,
)
from .html_renderer import render_html
from .json_renderer import render_json, write_json

__all__ = [
    "render_html",
    "render_json",
    "write_json",
    "ReportBuilder",
    "DataFreshness",
    "JobResult",
    "RuleTrace",
    "SearchReport",
    "SourceAttribution",
]
