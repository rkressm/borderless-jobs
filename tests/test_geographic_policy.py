"""Restrictions protect candidates regardless of broader positive claims."""

from itertools import combinations, permutations

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
    GeographicDecision,
    GeographicInclusion,
    GeographicRestriction,
    RestrictionKind,
    evaluate_geography,
)

BO = CountryCode("BO")
PROVENANCE = FactProvenance("reviewed", "test", "1.0.0", SchemaVersion("1.0.0"))


def evidence(quote: str) -> Evidence:
    return Evidence("job-v1", "1.0.0", 0, len(quote), quote, "https://example.org/job")


def inclusion(alias: str) -> GeographicInclusion:
    return GeographicInclusion(alias, evidence(alias), PROVENANCE)


def restriction(kind: RestrictionKind, *aliases: str) -> GeographicRestriction:
    return GeographicRestriction(
        kind, aliases, evidence(", ".join(aliases)), PROVENANCE
    )


@pytest.mark.parametrize(
    "fact",
    [
        restriction(RestrictionKind.EXCLUSION, "Bolivia"),
        restriction(RestrictionKind.EXCLUSION, "LATAM"),
        restriction(RestrictionKind.ALLOWLIST, "US", "CA"),
    ],
)
def test_broader_inclusions_cannot_override_restrictions(
    fact: GeographicRestriction,
) -> None:
    aliases = (
        ("Americas", "worldwide")
        if "LATAM" in fact.aliases
        else ("LATAM", "Americas", "worldwide")
    )
    broad = tuple(inclusion(alias) for alias in aliases)
    for size in range(len(broad) + 1):
        for subset in combinations(broad, size):
            for ordered in permutations(subset):
                result = evaluate_geography(BO, ordered, (fact,))
                assert result.outcome is DimensionalDecision.FAIL
                assert result.policy_version == PolicyVersion("1.0.0")
                assert result.reference_version == PolicyVersion("1.0.0")
                assert GeographicDecision.from_dict(result.to_dict()) == result


@pytest.mark.parametrize(
    ("facts", "outcome"),
    [
        ((), DimensionalDecision.UNKNOWN),
        (
            (restriction(RestrictionKind.ALLOWLIST, "BO", "US"),),
            DimensionalDecision.PASS,
        ),
        ((restriction(RestrictionKind.ALLOWLIST, "LATAM"),), DimensionalDecision.PASS),
        (
            (restriction(RestrictionKind.ALLOWLIST, "US", "unreviewed"),),
            DimensionalDecision.UNKNOWN,
        ),
        ((restriction(RestrictionKind.EXCLUSION, "US"),), DimensionalDecision.UNKNOWN),
    ],
)
def test_allowlists_and_absence(
    facts: tuple[GeographicRestriction, ...], outcome: DimensionalDecision
) -> None:
    assert evaluate_geography(BO, restrictions=facts).outcome is outcome


def test_unresolved_restriction_blocks_broad_inclusion() -> None:
    result = evaluate_geography(
        BO,
        (inclusion("worldwide"),),
        (restriction(RestrictionKind.EXCLUSION, "unreviewed"),),
    )
    assert result.outcome is DimensionalDecision.UNKNOWN
    assert result.rule_id == "geography.restriction.unsupported"


@pytest.mark.parametrize("candidate", ["ZZ", "TW"])
def test_unknown_candidate_cannot_fail_by_allowlist_omission(candidate: str) -> None:
    assert (
        evaluate_geography(
            CountryCode(candidate),
            restrictions=(restriction(RestrictionKind.ALLOWLIST, "US"),),
        ).outcome
        is DimensionalDecision.UNKNOWN
    )


def test_policy_version_is_explicit() -> None:
    with pytest.raises(ValueError, match="policy"):
        evaluate_geography(BO, policy_version=PolicyVersion("2.0.0"))


def test_empty_restriction_is_invalid() -> None:
    with pytest.raises(ValueError, match="aliases"):
        GeographicRestriction(
            RestrictionKind.ALLOWLIST, (), evidence("only"), PROVENANCE
        )


@pytest.mark.parametrize(
    ("positive", "negative"),
    [
        ((inclusion("BO"),), (restriction(RestrictionKind.EXCLUSION, "Bolivia"),)),
        ((inclusion("Bolivia"),), (restriction(RestrictionKind.ALLOWLIST, "US"),)),
        ((inclusion("LATAM"),), (restriction(RestrictionKind.EXCLUSION, "LATAM"),)),
        (
            (inclusion("worldwide"),),
            (restriction(RestrictionKind.EXCLUSION, "worldwide"),),
        ),
        (
            (),
            (
                restriction(RestrictionKind.ALLOWLIST, "BO"),
                restriction(RestrictionKind.ALLOWLIST, "US"),
            ),
        ),
    ],
)
def test_irreconcilable_evidence_is_permutation_invariant(
    positive: tuple[GeographicInclusion, ...],
    negative: tuple[GeographicRestriction, ...],
) -> None:
    expected = evaluate_geography(BO, positive, negative)
    assert expected.outcome is DimensionalDecision.UNKNOWN
    assert expected.annotation_candidate
    assert expected.rule_id == "geography.contradiction"
    for included in permutations(
        positive + (inclusion("Americas"), inclusion("worldwide"))
    ):
        for restricted in permutations(negative):
            result = evaluate_geography(BO, included, restricted)
            assert result.outcome is DimensionalDecision.UNKNOWN
            assert result.annotation_candidate
            assert result == evaluate_geography(
                BO, tuple(reversed(included)), tuple(reversed(restricted))
            )


def test_precise_exclusion_overrides_broad_inclusion_without_annotation() -> None:
    result = evaluate_geography(
        BO, (inclusion("LATAM"),), (restriction(RestrictionKind.EXCLUSION, "BO"),)
    )
    assert result.outcome is DimensionalDecision.FAIL
    assert not result.annotation_candidate


def test_duplicate_facts_do_not_change_decision() -> None:
    positive = inclusion("BO")
    negative = restriction(RestrictionKind.EXCLUSION, "BO")
    assert evaluate_geography(BO, (positive,), (negative,)) == evaluate_geography(
        BO, (positive, positive), (negative, negative)
    )


@pytest.mark.parametrize("alias", ["BO", "LATAM", "worldwide"])
def test_composed_inclusion_with_unrelated_exclusion(alias: str) -> None:
    result = evaluate_geography(
        BO, (inclusion(alias),), (restriction(RestrictionKind.EXCLUSION, "US"),)
    )
    assert result.outcome is DimensionalDecision.PASS
    assert result.rule_id.startswith("geography.inclusion.")
    assert not result.annotation_candidate


def test_known_exclusion_dominates_unresolved_restriction() -> None:
    facts = (
        restriction(RestrictionKind.EXCLUSION, "BO"),
        restriction(RestrictionKind.ALLOWLIST, "unreviewed"),
    )
    for ordered in permutations(facts):
        assert (
            evaluate_geography(BO, (inclusion("worldwide"),), ordered).outcome
            is DimensionalDecision.FAIL
        )
