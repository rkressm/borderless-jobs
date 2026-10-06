"""Engagement summarizes listing mechanisms, never legal eligibility."""

from itertools import permutations

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
    EngagementDecision,
    EngagementFact,
    EngagementKind,
    evaluate_engagement,
)

BO = CountryCode("BO")


def fact(
    kind: EngagementKind,
    *countries: str,
    worldwide: bool = False,
    requires_foreign_work: bool = False,
) -> EngagementFact:
    quote = "Synthetic explicit engagement statement"
    return EngagementFact(
        kind,
        Evidence("job-v1", "1.0.0", 0, len(quote), quote, "https://example.org/job"),
        FactProvenance("reviewed", "test", "1.0.0", SchemaVersion("1.0.0")),
        tuple(CountryCode(country) for country in countries),
        worldwide,
        requires_foreign_work,
    )


@pytest.mark.parametrize(
    ("facts", "outcome", "rule"),
    [
        ((), DimensionalDecision.UNKNOWN, "mechanism.missing"),
        (
            (fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True),),
            DimensionalDecision.PASS,
            "contractor.supported",
        ),
        (
            (fact(EngagementKind.CONTRACTOR_PERMITTED, "BO"),),
            DimensionalDecision.PASS,
            "contractor.supported",
        ),
        (
            (fact(EngagementKind.EOR_SUPPORTED, "BO"),),
            DimensionalDecision.PASS,
            "eor.supported",
        ),
        (
            (fact(EngagementKind.CONTRACTOR_PERMITTED),),
            DimensionalDecision.UNKNOWN,
            "mechanism.missing",
        ),
        (
            (fact(EngagementKind.EOR_SUPPORTED, "US"),),
            DimensionalDecision.UNKNOWN,
            "mechanism.missing",
        ),
        (
            (fact(EngagementKind.PAYROLL_RESTRICTED, "US"),),
            DimensionalDecision.FAIL,
            "restriction.payroll",
        ),
        (
            (fact(EngagementKind.WORK_AUTHORIZATION_REQUIRED, "US"),),
            DimensionalDecision.FAIL,
            "restriction.work_authorization",
        ),
        (
            (fact(EngagementKind.PAYROLL_RESTRICTED, "BO"),),
            DimensionalDecision.UNKNOWN,
            "mechanism.missing",
        ),
        (
            (fact(EngagementKind.VISA_REQUIRED, "US"),),
            DimensionalDecision.UNKNOWN,
            "mechanism.missing",
        ),
        (
            (fact(EngagementKind.VISA_REQUIRED, "US", requires_foreign_work=True),),
            DimensionalDecision.FAIL,
            "restriction.visa",
        ),
    ],
)
def test_engagement_outcomes(
    facts: tuple[EngagementFact, ...], outcome: DimensionalDecision, rule: str
) -> None:
    result = evaluate_engagement(BO, facts)
    assert result.outcome is outcome
    assert result.rule_id == f"engagement.{rule}"
    assert result.policy_version == PolicyVersion("1.0.0")
    assert result.reference_version == PolicyVersion("1.0.0")
    assert "not legal advice" in result.disclaimer
    assert EngagementDecision.from_dict(result.to_dict()) == result


@pytest.mark.parametrize(
    "negative",
    [
        fact(EngagementKind.CONTRACTOR_PROHIBITED, "BO"),
        fact(EngagementKind.PAYROLL_RESTRICTED, "US"),
        fact(EngagementKind.WORK_AUTHORIZATION_REQUIRED, "US"),
    ],
)
def test_conflicting_mechanisms_require_review(negative: EngagementFact) -> None:
    facts = (fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True), negative)
    expected = evaluate_engagement(BO, facts)
    assert expected.outcome is DimensionalDecision.UNKNOWN
    assert expected.annotation_candidate
    assert expected.rule_id == "engagement.contradiction"
    for ordered in permutations(facts):
        assert evaluate_engagement(BO, ordered) == expected


def test_eor_conflict_and_supported_alternative() -> None:
    denied = fact(EngagementKind.EOR_UNSUPPORTED, "BO")
    assert evaluate_engagement(
        BO, (denied, fact(EngagementKind.EOR_SUPPORTED, "BO"))
    ).annotation_candidate
    result = evaluate_engagement(
        BO, (denied, fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True))
    )
    assert result.outcome is DimensionalDecision.PASS


def test_visa_without_foreign_work_does_not_block_contracting() -> None:
    result = evaluate_engagement(
        BO,
        (
            fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True),
            fact(EngagementKind.VISA_REQUIRED, "US"),
        ),
    )
    assert result.outcome is DimensionalDecision.PASS


def test_unreviewed_restriction_blocks_pass() -> None:
    result = evaluate_engagement(
        BO,
        (
            fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True),
            fact(EngagementKind.PAYROLL_RESTRICTED, "ZZ"),
        ),
    )
    assert result.outcome is DimensionalDecision.UNKNOWN


@pytest.mark.parametrize("candidate", ["ZZ", "TW"])
def test_unknown_candidate_cannot_pass(candidate: str) -> None:
    assert (
        evaluate_engagement(
            CountryCode(candidate),
            (fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True),),
        ).outcome
        is DimensionalDecision.UNKNOWN
    )


def test_unsupported_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="policy"):
        evaluate_engagement(BO, policy_version=PolicyVersion("2.0.0"))


def test_eor_requires_explicit_country_coverage() -> None:
    with pytest.raises(ValueError, match="worldwide"):
        fact(EngagementKind.EOR_SUPPORTED, worldwide=True)


@pytest.mark.parametrize(
    "facts",
    [
        (
            fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True),
            fact(EngagementKind.CONTRACTOR_PROHIBITED, "US"),
        ),
        (
            fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True),
            fact(EngagementKind.EOR_SUPPORTED, "BO"),
        ),
        (
            fact(EngagementKind.EOR_SUPPORTED, "BO"),
            fact(EngagementKind.CONTRACTOR_PROHIBITED, worldwide=True),
        ),
    ],
)
def test_supported_alternatives_are_not_contradictions(
    facts: tuple[EngagementFact, ...],
) -> None:
    expected = evaluate_engagement(BO, facts)
    assert expected.outcome is DimensionalDecision.PASS
    assert not expected.annotation_candidate
    for ordered in permutations(facts):
        assert evaluate_engagement(BO, ordered + ordered) == expected


def test_mandatory_foreign_visa_conflicts_with_remote_contracting() -> None:
    result = evaluate_engagement(
        BO,
        (
            fact(EngagementKind.CONTRACTOR_PERMITTED, worldwide=True),
            fact(EngagementKind.VISA_REQUIRED, "US", requires_foreign_work=True),
        ),
    )
    assert result.outcome is DimensionalDecision.UNKNOWN
    assert result.annotation_candidate


def test_confirmed_restriction_is_not_weakened_by_missing_coverage() -> None:
    result = evaluate_engagement(
        BO,
        (
            fact(EngagementKind.PAYROLL_RESTRICTED, "US"),
            fact(EngagementKind.EOR_SUPPORTED),
        ),
    )
    assert result.outcome is DimensionalDecision.FAIL


def test_matching_work_authorization_is_not_a_legal_eligibility_assertion() -> None:
    result = evaluate_engagement(
        BO, (fact(EngagementKind.WORK_AUTHORIZATION_REQUIRED, "BO"),)
    )
    assert result.outcome is DimensionalDecision.UNKNOWN
    assert "not legal advice" in result.disclaimer


def test_foreign_work_flag_cannot_be_attached_to_a_mechanism() -> None:
    with pytest.raises(ValueError, match="Foreign work"):
        fact(EngagementKind.EOR_SUPPORTED, "BO", requires_foreign_work=True)
