"""Offline behavior through the production search interface."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from borderless.domain import CountryCode, GlobalVerdict
from borderless.search import (
    JobSearch,
    SearchResultPage,
    SearchSpecification,
    SyntheticSearchAdapter,
)

NOW = datetime(2026, 10, 5, tzinfo=UTC)


def specification() -> SearchSpecification:
    return SearchSpecification(" Data Engineer ", CountryCode("bo"), NOW, 0, 10)


def test_search_filters_orders_and_preserves_hand_built_facts() -> None:
    service: JobSearch = SyntheticSearchAdapter()
    page = service.search(specification())
    assert [job.job_id for job in page.jobs] == [
        "synthetic-01",
        "synthetic-02",
        "synthetic-03",
    ]
    assert page.total == 3
    assert page.jobs[0].facts[0].value == "Remote"
    assert page.jobs[0].facts[0].evidence == page.jobs[0].evidence
    assert all(job.provenance[0].method == "synthetic" for job in page.jobs)
    assert all(job.assessed_at == NOW for job in page.jobs)
    assert (
        service.search(replace(specification(), country=CountryCode("FR"))).total == 1
    )
    assert service.search(replace(specification(), role="designer")).total == 1


def test_pagination_counts_before_slicing_and_is_repeatable() -> None:
    service = SyntheticSearchAdapter()
    query = replace(specification(), offset=1, limit=1)
    page = service.search(query)
    assert page.total == 3
    assert [job.job_id for job in page.jobs] == ["synthetic-02"]
    assert page == service.search(query)
    assert service.search(replace(query, offset=20)).jobs == ()
    assert service.search(replace(query, offset=20)).total == 3


def test_empty_and_optional_filters_and_historical_cutoff() -> None:
    service = SyntheticSearchAdapter()
    for changes in (
        dict(role="astronaut"),
        dict(sources=("another-source",)),
        dict(verdicts=(GlobalVerdict.YES,)),
        dict(as_of=datetime(2020, 1, 1, tzinfo=UTC)),
    ):
        page = service.search(replace(specification(), **changes))
        assert page.jobs == ()
        assert page.total == 0
    assert (
        service.search(
            replace(specification(), verdicts=(GlobalVerdict.UNCERTAIN,))
        ).total
        == 3
    )
    assert service.search(replace(specification(), sources=("synthetic",))).total == 3


def test_page_round_trip_and_rejects_corrupted_adapter_output() -> None:

    page = SyntheticSearchAdapter().search(specification())
    assert SearchResultPage.from_dict(page.to_dict()) == page
    for changes in (
        dict(total=0),
        dict(jobs=tuple(reversed(page.jobs))),
        dict(sources=()),
        dict(sources=(page.sources[0], page.sources[0])),
        dict(
            jobs=(
                replace(page.jobs[0], assessed_at=datetime(2020, 1, 1, tzinfo=UTC)),
                *page.jobs[1:],
            )
        ),
    ):
        with pytest.raises(ValueError):
            replace(page, **changes)


def test_search_page_rejects_results_outside_requested_filters() -> None:

    page = SyntheticSearchAdapter().search(specification())
    for changes in (
        dict(role="designer"),
        dict(country=CountryCode("US")),
        dict(sources=("other-source",)),
        dict(verdicts=(GlobalVerdict.YES,)),
    ):
        with pytest.raises(ValueError):
            replace(page, specification=replace(specification(), **changes))
