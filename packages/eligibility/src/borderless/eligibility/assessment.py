"""A pure assessment with complete typed inputs and ordered decision traces."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, tzinfo

from borderless.domain import (
    CountryCode,
    DimensionalDecision,
    GlobalVerdict,
    PolicyVersion,
    Value,
    require_text,
)

from .engagement import EngagementDecision, EngagementFact, evaluate_engagement
from .geographic_policy import (
    GeographicDecision,
    GeographicRestriction,
    _ordered,
    evaluate_geography,
)
from .inclusion import GeographicInclusion
from .timezone_policy import (
    TimezoneDecision,
    TimezoneFact,
    WorkingWindow,
    evaluate_timezone,
)
from .verdict import compose_verdict

_POLICY_VERSION = PolicyVersion("1.0.0")


@dataclass(frozen=True, slots=True)
class EligibilityInputs(Value):
    candidate: CountryCode
    as_of: datetime
    availability: WorkingWindow | None = None
    inclusions: tuple[GeographicInclusion, ...] = ()
    restrictions: tuple[GeographicRestriction, ...] = ()
    engagement_facts: tuple[EngagementFact, ...] = ()
    timezone_facts: tuple[TimezoneFact, ...] = ()
    timezone_data_version: str = "not-used"

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        require_text(self.timezone_data_version)
        if (
            self.availability
            and self.timezone_facts
            and self.timezone_data_version == "not-used"
        ):
            raise ValueError("Record the caller-loaded IANA data version")
        for name in (
            "inclusions",
            "restrictions",
            "engagement_facts",
            "timezone_facts",
        ):
            object.__setattr__(self, name, _ordered(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class EligibilityRuleTrace(Value):
    dimension: str
    rule_id: str
    policy_version: PolicyVersion
    reference_version: PolicyVersion | None
    inputs: EligibilityInputs
    outcome: str
    explanation: str
    missing_facts: tuple[str, ...]
    annotation_candidate: bool = False

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if self.dimension not in {"geography", "engagement", "timezone", "global"}:
            raise ValueError("Unknown trace dimension")
        require_text(self.rule_id)
        require_text(self.explanation)
        if self.outcome not in (
            {item.value for item in GlobalVerdict}
            if self.dimension == "global"
            else {item.value for item in DimensionalDecision}
        ):
            raise ValueError("Invalid trace outcome")
        for missing in self.missing_facts:
            require_text(missing)


@dataclass(frozen=True, slots=True)
class EligibilityAssessment(Value):
    verdict: GlobalVerdict
    geography: GeographicDecision
    engagement: EngagementDecision
    timezone: TimezoneDecision
    policy_version: PolicyVersion
    trace: tuple[EligibilityRuleTrace, ...]
    disclaimer: str = "Informational summary of listing evidence; not legal advice."

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        dimensions = (self.geography, self.engagement, self.timezone)
        expected = compose_verdict(*(decision.outcome for decision in dimensions))
        if self.verdict is not expected or tuple(
            entry.dimension for entry in self.trace
        ) != ("geography", "engagement", "timezone", "global"):
            raise ValueError(
                "Assessment verdict and ordered trace must match dimensions"
            )
        if tuple(entry.outcome for entry in self.trace) != tuple(
            decision.outcome.value for decision in dimensions
        ) + (expected.value,):
            raise ValueError("Trace outcomes must match the assessment")


def _trace(
    dimension: str,
    decision: GeographicDecision | EngagementDecision | TimezoneDecision,
    inputs: EligibilityInputs,
) -> EligibilityRuleTrace:
    missing = (
        (decision.explanation,)
        if decision.outcome is DimensionalDecision.UNKNOWN
        else ()
    )
    return EligibilityRuleTrace(
        dimension,
        decision.rule_id,
        decision.policy_version,
        getattr(decision, "reference_version", None),
        inputs,
        decision.outcome.value,
        decision.explanation,
        missing,
        getattr(decision, "annotation_candidate", False),
    )


def evaluate_eligibility(
    inputs: EligibilityInputs,
    *,
    zones: Mapping[str, tzinfo],
    policy_version: PolicyVersion = _POLICY_VERSION,
) -> EligibilityAssessment:
    if policy_version != _POLICY_VERSION:
        raise ValueError("Unsupported assessment policy version")
    geography = evaluate_geography(
        inputs.candidate, inputs.inclusions, inputs.restrictions
    )
    engagement = evaluate_engagement(inputs.candidate, inputs.engagement_facts)
    timezone = evaluate_timezone(
        inputs.as_of, inputs.availability, inputs.timezone_facts, zones=zones
    )
    verdict = compose_verdict(geography.outcome, engagement.outcome, timezone.outcome)
    trace = tuple(
        _trace(name, decision, inputs)
        for name, decision in (
            ("geography", geography),
            ("engagement", engagement),
            ("timezone", timezone),
        )
    )
    global_trace = EligibilityRuleTrace(
        "global",
        f"global.{verdict.value.lower()}",
        policy_version,
        None,
        inputs,
        verdict.value,
        "Any FAIL yields NO; otherwise UNKNOWN yields UNCERTAIN; otherwise YES.",
        tuple(missing for entry in trace for missing in entry.missing_facts),
        any(entry.annotation_candidate for entry in trace),
    )
    return EligibilityAssessment(
        verdict, geography, engagement, timezone, policy_version, (*trace, global_trace)
    )
