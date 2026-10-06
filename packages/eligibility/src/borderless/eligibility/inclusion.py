"""Evaluate one explicit inclusion fact; listing composition uses evaluate_geography."""

from dataclasses import dataclass

from borderless.domain import (
    CountryCode,
    DimensionalDecision,
    Evidence,
    FactProvenance,
    PolicyVersion,
    Value,
    require_text,
)

from .geography import GEOGRAPHIC_REFERENCE

_INCLUSION_POLICY_VERSION = PolicyVersion("1.0.0")


@dataclass(frozen=True, slots=True)
class GeographicInclusion(Value):
    """An extraction assertion of hiring inclusion, not an arbitrary text mention."""

    alias: str
    evidence: Evidence
    provenance: FactProvenance

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        require_text(self.alias)
        if self.alias != self.evidence.quote:
            raise ValueError("Inclusion alias must equal its evidence quote")


@dataclass(frozen=True, slots=True)
class InclusionDecision(Value):
    outcome: DimensionalDecision
    rule_id: str
    policy_version: PolicyVersion
    reference_version: PolicyVersion
    candidate: CountryCode
    fact: GeographicInclusion
    explanation: str


def _inclusion_rule(fact: GeographicInclusion, candidate: CountryCode) -> str | None:
    reference = GEOGRAPHIC_REFERENCE
    if candidate not in {country.code for country in reference.countries}:
        return None
    identity = reference.resolve(fact.alias)
    if identity == candidate.value:
        return "country"
    if identity == "worldwide":
        return "worldwide"
    if any(
        region.identity == identity and candidate in region.members
        for region in reference.regions
    ):
        return "region"
    return None


def evaluate_geographic_inclusion(
    fact: GeographicInclusion,
    candidate: CountryCode,
    policy_version: PolicyVersion = _INCLUSION_POLICY_VERSION,
) -> InclusionDecision:
    """Assess positive evidence only; absence of inclusion never implies exclusion."""
    if policy_version != _INCLUSION_POLICY_VERSION:
        raise ValueError("Unsupported geographic inclusion policy version")
    rule = _inclusion_rule(fact, candidate)
    return InclusionDecision(
        DimensionalDecision.PASS if rule else DimensionalDecision.UNKNOWN,
        f"geography.inclusion.{rule or 'unsupported'}",
        policy_version,
        GEOGRAPHIC_REFERENCE.version,
        candidate,
        fact,
        "Explicit inclusion contains the candidate country."
        if rule
        else "No reviewed inclusion of the candidate country is established.",
    )
