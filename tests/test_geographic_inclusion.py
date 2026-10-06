"""Explicit inclusion rules over evidenced facts, independent of extraction."""

from dataclasses import replace

import pytest
from borderless.domain import (
    CountryCode,
    DimensionalDecision,
    Evidence,
    FactProvenance,
    PolicyVersion,
    SchemaVersion,
)
from borderless.eligibility import (
    GeographicInclusion,
    InclusionDecision,
    evaluate_geographic_inclusion,
)


def inclusion(alias: str) -> GeographicInclusion:
    return GeographicInclusion(
        alias,
        Evidence(
            "job-v1", "1.0.0", 10, 10 + len(alias), alias, "https://example.org/job"
        ),
        FactProvenance("reviewed", "test", "1.0.0", SchemaVersion("1.0.0")),
    )


@pytest.mark.parametrize(
    ("alias", "rule"),
    [
        ("Bolivia", "country"),
        (" BO ", "country"),
        ("bol", "country"),
        ("bOlIvIa", "country"),
        ("Bolivia (Plurinational State of)", "country"),
        ("LATAM", "region"),
        ("latin america", "region"),
        (" SOUTH   AMERICA ", "region"),
        ("the Americas", "region"),
        ("worldwide", "worldwide"),
        ("GLOBAL", "worldwide"),
        ("anywhere in the world", "worldwide"),
    ],
)
def test_explicit_inclusion_passes_with_trace(alias: str, rule: str) -> None:
    fact = inclusion(alias)
    result = evaluate_geographic_inclusion(fact, CountryCode("BO"))
    assert result.outcome is DimensionalDecision.PASS
    assert result.rule_id == f"geography.inclusion.{rule}"
    assert result.policy_version == PolicyVersion("1.0.0")
    assert result.reference_version == PolicyVersion("1.0.0")
    assert result.fact == fact
    assert result.candidate == CountryCode("BO")
    assert result.explanation
    assert InclusionDecision.from_dict(result.to_dict()) == result


@pytest.mark.parametrize(
    "alias",
    [
        "Americas-friendly",
        "worldwide-ish",
        "remote",
        "Bolivian",
        "xLATAM",
        "South American",
        "not Bolivia",
        "Bolivia excluded",
        "We hire worldwide",
        "BO-US",
        "Bolivia\u200b",
    ],
)
def test_unsupported_values_remain_unknown(alias: str) -> None:
    result = evaluate_geographic_inclusion(inclusion(alias), CountryCode("BO"))
    assert result.outcome is DimensionalDecision.UNKNOWN
    assert result.rule_id == "geography.inclusion.unsupported"


@pytest.mark.parametrize(
    ("alias", "candidate"),
    [("US", "BO"), ("LATAM", "US"), ("worldwide", "ZZ"), ("worldwide", "TW")],
)
def test_noncontaining_or_unknown_identity_stays_unknown(
    alias: str, candidate: str
) -> None:
    assert (
        evaluate_geographic_inclusion(inclusion(alias), CountryCode(candidate)).outcome
        is DimensionalDecision.UNKNOWN
    )


def test_evidence_must_quote_the_extracted_alias() -> None:
    with pytest.raises(ValueError, match="quote"):
        replace(inclusion("not Bolivia"), alias="Bolivia")


def test_unsupported_policy_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="policy"):
        evaluate_geographic_inclusion(
            inclusion("BO"), CountryCode("BO"), PolicyVersion("2.0.0")
        )
