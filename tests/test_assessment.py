import json
from datetime import UTC, datetime

import pytest
from borderless.domain import (
    CountryCode,
    Evidence,
    FactProvenance,
    GlobalVerdict,
    SchemaVersion,
)
from borderless.eligibility import (
    EligibilityAssessment,
    EligibilityInputs,
    EngagementFact,
    EngagementKind,
    GeographicInclusion,
    GeographicRestriction,
    RestrictionKind,
    evaluate_eligibility,
)

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)
PROVENANCE = FactProvenance("reviewed", "test", "1.0.0", SchemaVersion("1.0.0"))


def evidence(quote: str) -> Evidence:
    return Evidence("v1", "1.0.0", 0, len(quote), quote, "https://example.org/job")


@pytest.mark.parametrize(
    ("alias", "excluded", "expected"),
    [
        ("worldwide", False, GlobalVerdict.YES),
        ("worldwide", True, GlobalVerdict.NO),
        ("Bolivia", True, GlobalVerdict.UNCERTAIN),
        ("remote", False, GlobalVerdict.UNCERTAIN),
    ],
)
def test_all_verdicts_have_replayable_traces(
    alias: str, excluded: bool, expected: GlobalVerdict
) -> None:
    inputs = EligibilityInputs(
        CountryCode("BO"),
        NOW,
        None,
        (GeographicInclusion(alias, evidence(alias), PROVENANCE),),
        (
            GeographicRestriction(
                RestrictionKind.EXCLUSION,
                ("Bolivia",),
                evidence("except Bolivia"),
                PROVENANCE,
            ),
        )
        if excluded
        else (),
        (
            EngagementFact(
                EngagementKind.CONTRACTOR_PERMITTED,
                evidence("contractor"),
                PROVENANCE,
                worldwide=True,
            ),
        ),
        (),
    )
    result = evaluate_eligibility(inputs, zones={})
    assert result.verdict is expected
    assert [entry.dimension for entry in result.trace] == [
        "geography",
        "engagement",
        "timezone",
        "global",
    ]
    assert all(
        entry.rule_id and entry.explanation and entry.inputs == inputs
        for entry in result.trace
    )
    encoded = json.dumps(result.to_dict(), sort_keys=True)
    assert EligibilityAssessment.from_dict(json.loads(encoded)) == result
    assert (
        json.dumps(evaluate_eligibility(inputs, zones={}).to_dict(), sort_keys=True)
        == encoded
    )
    if expected is GlobalVerdict.UNCERTAIN:
        assert result.trace[0].missing_facts


def test_absent_facts_are_explicit() -> None:
    result = evaluate_eligibility(EligibilityInputs(CountryCode("BO"), NOW), zones={})
    assert result.verdict is GlobalVerdict.UNCERTAIN
    assert result.trace[0].missing_facts
    assert result.trace[1].missing_facts
    assert not result.trace[2].missing_facts


def test_invalid_assessment_and_trace_contracts() -> None:
    from dataclasses import replace

    from borderless.domain import PolicyVersion
    from borderless.eligibility import (
        EligibilityRuleTrace,
        TimezoneFact,
        WorkingWindow,
        compose_verdict,
    )

    inputs = EligibilityInputs(CountryCode("BO"), NOW)
    result = evaluate_eligibility(inputs, zones={})
    with pytest.raises(ValueError, match="verdict"):
        replace(result, verdict=GlobalVerdict.YES)
    trace = result.trace[0]
    with pytest.raises(ValueError, match="outcomes"):
        replace(result, trace=(replace(trace, outcome="PASS"), *result.trace[1:]))
    with pytest.raises(ValueError, match="dimension"):
        replace(trace, dimension="invented")
    with pytest.raises(ValueError, match="outcome"):
        replace(trace, outcome="YES")
    with pytest.raises(ValueError, match="nonempty"):
        replace(trace, missing_facts=("",))
    with pytest.raises(ValueError, match="policy"):
        evaluate_eligibility(inputs, zones={}, policy_version=PolicyVersion("2.0.0"))
    with pytest.raises(ValueError, match="IANA"):
        replace(
            inputs,
            availability=WorkingWindow("UTC", 0, 60),
            timezone_facts=(
                TimezoneFact(None, 60, True, evidence("overlap"), PROVENANCE),
            ),
        )
    with pytest.raises(ValueError, match="dimensional"):
        compose_verdict("PASS", result.engagement.outcome, result.timezone.outcome)  # type: ignore[arg-type]
    assert EligibilityRuleTrace.from_dict(trace.to_dict()) == trace
