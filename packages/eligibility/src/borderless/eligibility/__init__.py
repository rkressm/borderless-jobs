"""Pure dimensional and global eligibility policy over validated facts."""

from .assessment import (
    EligibilityAssessment,
    EligibilityInputs,
    EligibilityRuleTrace,
    evaluate_eligibility,
)
from .engagement import (
    EngagementDecision,
    EngagementFact,
    EngagementKind,
    evaluate_engagement,
)
from .geographic_policy import (
    GeographicDecision,
    GeographicRestriction,
    RestrictionKind,
    evaluate_geography,
)
from .geography import (
    GEOGRAPHIC_REFERENCE,
    CountryIdentity,
    GeographicReference,
    GeographicRegion,
)
from .inclusion import (
    GeographicInclusion,
    InclusionDecision,
    evaluate_geographic_inclusion,
)
from .timezone_policy import (
    TimezoneDecision,
    TimezoneFact,
    WorkingWindow,
    evaluate_timezone,
)
from .verdict import compose_verdict

__all__ = [
    "EligibilityAssessment",
    "EligibilityInputs",
    "EligibilityRuleTrace",
    "evaluate_eligibility",
    "compose_verdict",
    "TimezoneDecision",
    "TimezoneFact",
    "WorkingWindow",
    "evaluate_timezone",
    "GeographicInclusion",
    "InclusionDecision",
    "evaluate_geographic_inclusion",
    "GEOGRAPHIC_REFERENCE",
    "CountryIdentity",
    "GeographicReference",
    "GeographicRegion",
    "GeographicDecision",
    "GeographicRestriction",
    "RestrictionKind",
    "evaluate_geography",
    "EngagementDecision",
    "EngagementFact",
    "EngagementKind",
    "evaluate_engagement",
]
