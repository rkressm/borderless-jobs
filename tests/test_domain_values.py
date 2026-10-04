"""Foundational values remain immutable, validated, and JSON compatible."""

import json
from dataclasses import FrozenInstanceError

import pytest
from borderless.domain import (
    CountryCode,
    DimensionalDecision,
    Evidence,
    FactProvenance,
    GlobalVerdict,
    PolicyVersion,
    SchemaVersion,
)


def test_values_round_trip_and_equality() -> None:
    values = [
        CountryCode(" bo "),
        PolicyVersion("1.0.0"),
        SchemaVersion("1.0.0"),
        Evidence(
            "job-v1", "normalization-v1", 0, 6, "Remote", "https://example.org/job"
        ),
        FactProvenance("parser", "rules", "1.0.0", SchemaVersion("1.0.0")),
    ]
    for value in values:
        assert type(value).from_dict(json.loads(json.dumps(value.to_dict()))) == value
    assert CountryCode("bo") == CountryCode("BO")
    assert DimensionalDecision("UNKNOWN") is DimensionalDecision.UNKNOWN
    assert GlobalVerdict("UNCERTAIN") is GlobalVerdict.UNCERTAIN
    with pytest.raises(FrozenInstanceError):
        country = CountryCode("BO")
        country.value = "US"  # type: ignore[misc]


@pytest.mark.parametrize("code", ["", "B", "BOL", "12", "ß"])
def test_country_rejects_invalid_codes(code: str) -> None:
    with pytest.raises(ValueError):
        CountryCode(code)


@pytest.mark.parametrize("version", ["", "1", "v1.0.0", "01.0.0", "1.0.-1"])
def test_versions_reject_invalid_values(version: str) -> None:
    for cls in (PolicyVersion, SchemaVersion):
        with pytest.raises(ValueError):
            cls(version)


def test_evidence_checks_offsets_quote_and_destination() -> None:
    evidence = Evidence("v1", "n1", 2, 8, "Remote", "https://example.org/job")
    evidence.verify("  Remote job")
    with pytest.raises(ValueError):
        evidence.verify("  Office job")
    for start, end, quote, url in [
        (-1, 5, "Remote", "https://example.org"),
        (0, 0, "", "https://example.org"),
        (0, 5, "Remote", "https://example.org"),
        (0, 6, "Remote", "javascript:alert(1)"),
        (0, 6, "Remote", "https://user:pass@example.org"),
    ]:
        with pytest.raises(ValueError):
            Evidence("v1", "n1", start, end, quote, url)


def test_provenance_requires_paired_model_metadata_and_known_method() -> None:
    with pytest.raises(ValueError):
        FactProvenance("guess", "provider", "1", SchemaVersion("1.0.0"))
    with pytest.raises(ValueError):
        FactProvenance("model", "provider", "1", SchemaVersion("1.0.0"), model="m")


def test_deserialization_rejects_unknown_fields_and_wrong_types() -> None:
    with pytest.raises(ValueError):
        CountryCode.from_dict({"value": "BO", "extra": "ignored"})
    with pytest.raises(ValueError):
        CountryCode.from_dict({"value": 12})


def test_model_provenance_and_unicode_evidence_round_trip() -> None:
    value = FactProvenance(
        "model",
        "local",
        "1.0.0",
        SchemaVersion("1.0.0"),
        "p1",
        "model",
        "immutable-revision",
        "runtime-v1",
        ("review needed",),
    )
    assert FactProvenance.from_dict(value.to_dict()) == value
    evidence = Evidence("v1", "n1", 0, 2, "é🌎", "https://example.org")
    evidence.verify("é🌎 remote")
    with pytest.raises(ValueError):
        Evidence("v1", "n1", 0, 2001, "x" * 2001, "https://example.org")
