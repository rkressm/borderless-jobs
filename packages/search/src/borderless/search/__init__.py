"""Public storage-neutral search contracts and offline demonstration adapter."""

from .contracts import ResultOrderKey, SearchSpecification
from .results import (
    JobSearch,
    SearchFact,
    SearchJob,
    SearchResultPage,
    SearchRuleTrace,
    SearchSource,
)
from .synthetic import SyntheticSearchAdapter

__all__ = [
    "ResultOrderKey",
    "SearchSpecification",
    "SearchFact",
    "SearchJob",
    "SearchResultPage",
    "SearchRuleTrace",
    "JobSearch",
    "SearchSource",
    "SyntheticSearchAdapter",
]
