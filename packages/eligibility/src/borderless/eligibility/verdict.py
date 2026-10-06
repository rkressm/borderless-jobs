"""Three-valued composition of the three policy dimensions."""

from borderless.domain import DimensionalDecision, GlobalVerdict


def compose_verdict(
    geography: DimensionalDecision,
    engagement: DimensionalDecision,
    timezone: DimensionalDecision,
) -> GlobalVerdict:
    dimensions = (geography, engagement, timezone)
    if any(type(value) is not DimensionalDecision for value in dimensions):
        raise ValueError("Expected dimensional decisions")
    if DimensionalDecision.FAIL in dimensions:
        return GlobalVerdict.NO
    if DimensionalDecision.UNKNOWN in dimensions:
        return GlobalVerdict.UNCERTAIN
    return GlobalVerdict.YES
