"""Frozen synthetic report shared by renderer contract tests."""

from datetime import UTC, datetime

import pytest
from borderless.domain import CountryCode, PolicyVersion, SchemaVersion
from borderless.reporting import ReportBuilder, SearchReport
from borderless.search import SearchSpecification, SyntheticSearchAdapter


@pytest.fixture
def synthetic_report() -> SearchReport:
    instant = datetime(2026, 10, 5, tzinfo=UTC)
    return ReportBuilder(
        SyntheticSearchAdapter(),
        lambda: instant,
        PolicyVersion("1.0.0"),
        SchemaVersion("1.0.0"),
    ).build(SearchSpecification("data-engineer", CountryCode("BO"), instant, 0, 10))
