"""Search normalization, pagination and deterministic ordering contracts."""

import json
from datetime import UTC, datetime

import pytest
from borderless.domain import CountryCode, GlobalVerdict
from borderless.search import ResultOrderKey, SearchSpecification

NOW = datetime(2026, 10, 4, tzinfo=UTC)


def test_search_normalizes_and_round_trips() -> None:
    spec = SearchSpecification(
        " Data Engineer ",
        CountryCode("bo"),
        NOW,
        0,
        20,
        (GlobalVerdict.YES,),
        ("synthetic",),
    )
    assert spec.role == "data-engineer"
    assert SearchSpecification.from_dict(json.loads(json.dumps(spec.to_dict()))) == spec


@pytest.mark.parametrize(
    "changes",
    [
        dict(role=""),
        dict(role="<script>"),
        dict(offset=-1),
        dict(limit=0),
        dict(limit=101),
        dict(limit=True),
        dict(as_of=datetime(2026, 10, 4)),
        dict(sources=("bad source",)),
        dict(verdicts=(GlobalVerdict.YES, GlobalVerdict.YES)),
        dict(verdicts=("MAYBE",)),
    ],
)
def test_search_rejects_invalid_filters(changes: dict[str, object]) -> None:
    data: dict[str, object] = dict(
        role="engineer", country=CountryCode("BO"), as_of=NOW, offset=0, limit=10
    )
    data.update(changes)
    with pytest.raises(ValueError):
        SearchSpecification(**data)  # type: ignore[arg-type]


def test_pagination_is_explicit_and_order_ties_use_job_identity() -> None:
    with pytest.raises(TypeError):
        SearchSpecification("engineer", CountryCode("BO"), NOW)  # type: ignore[call-arg]
    older = ResultOrderKey(datetime(2026, 10, 3, tzinfo=UTC), "a")
    first = ResultOrderKey(NOW, "a")
    second = ResultOrderKey(NOW, "b")
    assert sorted([older, second, first], key=lambda item: item.sort_key()) == [
        first,
        second,
        older,
    ]
    assert ResultOrderKey.from_dict(first.to_dict()) == first


def test_constructor_requires_typed_nested_values() -> None:
    with pytest.raises(ValueError):
        SearchSpecification("engineer", CountryCode("BO"), NOW, 0, 10, ("YES",))  # type: ignore[arg-type]


def test_order_keeps_microsecond_precision_for_all_supported_datetimes() -> None:
    earlier = ResultOrderKey(datetime(9999, 1, 1, microsecond=1, tzinfo=UTC), "a")
    later = ResultOrderKey(datetime(9999, 1, 1, microsecond=2, tzinfo=UTC), "b")
    assert later.sort_key() < earlier.sort_key()
