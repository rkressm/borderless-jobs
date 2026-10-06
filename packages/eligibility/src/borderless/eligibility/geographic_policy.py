"""Compose explicit geographic facts without extracting or reading source text."""

from dataclasses import dataclass
from enum import StrEnum

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
from .inclusion import GeographicInclusion, evaluate_geographic_inclusion

_GEOGRAPHY_POLICY_VERSION = PolicyVersion("1.0.0")


def _ordered[T: Value](facts: tuple[T, ...]) -> tuple[T, ...]:
    return tuple(sorted(set(facts), key=lambda fact: repr(fact.to_dict())))


def _scope(alias: str) -> frozenset[CountryCode] | None:
    reference = GEOGRAPHIC_REFERENCE
    identity = reference.resolve(alias)
    if identity == "worldwide":
        return frozenset(country.code for country in reference.countries)
    for country in reference.countries:
        if identity == country.code.value:
            return frozenset((country.code,))
    for region in reference.regions:
        if identity == region.identity:
            return frozenset(region.members)
    return None


class RestrictionKind(StrEnum):
    EXCLUSION = "EXCLUSION"
    ALLOWLIST = "ALLOWLIST"


@dataclass(frozen=True, slots=True)
class GeographicRestriction(Value):
    """Aliases extracted from an explicit exclusion or exhaustive hiring allowlist."""

    kind: RestrictionKind
    aliases: tuple[str, ...]
    evidence: Evidence
    provenance: FactProvenance

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if not self.aliases:
            raise ValueError("Restriction requires aliases")
        for alias in self.aliases:
            require_text(alias)
        object.__setattr__(self, "aliases", tuple(sorted(set(self.aliases))))


def _restriction_outcome(
    fact: GeographicRestriction, candidate: CountryCode
) -> DimensionalDecision:
    scopes = tuple(_scope(alias) for alias in fact.aliases)
    contains = any(scope is not None and candidate in scope for scope in scopes)
    if fact.kind is RestrictionKind.EXCLUSION and contains:
        return DimensionalDecision.FAIL
    if fact.kind is RestrictionKind.ALLOWLIST and contains:
        return DimensionalDecision.PASS
    if any(scope is None for scope in scopes):
        return DimensionalDecision.UNKNOWN
    return (
        DimensionalDecision.FAIL
        if fact.kind is RestrictionKind.ALLOWLIST
        else DimensionalDecision.NOT_APPLICABLE
    )


@dataclass(frozen=True, slots=True)
class GeographicDecision(Value):
    outcome: DimensionalDecision
    rule_id: str
    policy_version: PolicyVersion
    reference_version: PolicyVersion
    candidate: CountryCode
    inclusions: tuple[GeographicInclusion, ...]
    restrictions: tuple[GeographicRestriction, ...]
    explanation: str
    annotation_candidate: bool = False


def evaluate_geography(
    candidate: CountryCode,
    inclusions: tuple[GeographicInclusion, ...] = (),
    restrictions: tuple[GeographicRestriction, ...] = (),
    policy_version: PolicyVersion = _GEOGRAPHY_POLICY_VERSION,
) -> GeographicDecision:
    """Specific restrictions dominate broad inclusions; unresolved facts stay visible."""
    if policy_version != _GEOGRAPHY_POLICY_VERSION:
        raise ValueError("Unsupported geography policy version")
    inclusions, restrictions = _ordered(inclusions), _ordered(restrictions)
    outcome, rule, explanation = _geographic_outcome(
        candidate, inclusions, restrictions
    )
    return GeographicDecision(
        outcome,
        f"geography.{rule}",
        policy_version,
        GEOGRAPHIC_REFERENCE.version,
        candidate,
        inclusions,
        restrictions,
        explanation,
        annotation_candidate=rule == "contradiction",
    )


def _geographic_outcome(
    candidate: CountryCode,
    inclusions: tuple[GeographicInclusion, ...],
    restrictions: tuple[GeographicRestriction, ...],
) -> tuple[DimensionalDecision, str, str]:
    if _scope(candidate.value) is None:
        return (
            DimensionalDecision.UNKNOWN,
            "candidate.unsupported",
            "Candidate country is not reviewed.",
        )
    evaluated = tuple(
        (_restriction_outcome(fact, candidate), fact) for fact in restrictions
    )
    if _has_contradiction(candidate, inclusions, evaluated):
        return (
            DimensionalDecision.UNKNOWN,
            "contradiction",
            "Incompatible explicit geographic evidence requires annotation review.",
        )
    for kind in (RestrictionKind.EXCLUSION, RestrictionKind.ALLOWLIST):
        if any(
            outcome is DimensionalDecision.FAIL and fact.kind is kind
            for outcome, fact in evaluated
        ):
            return (
                DimensionalDecision.FAIL,
                f"restriction.{kind.value.lower()}",
                "Explicit restriction excludes the candidate country.",
            )
    if any(outcome is DimensionalDecision.UNKNOWN for outcome, _ in evaluated):
        return (
            DimensionalDecision.UNKNOWN,
            "restriction.unsupported",
            "A restriction contains unreviewed geographic values.",
        )
    if any(outcome is DimensionalDecision.PASS for outcome, _ in evaluated):
        return (
            DimensionalDecision.PASS,
            "allowlist.included",
            "Explicit allowlist contains the candidate country.",
        )
    decisions = tuple(
        evaluate_geographic_inclusion(fact, candidate) for fact in inclusions
    )
    for rule in ("country", "region", "worldwide"):
        if any(
            decision.rule_id == f"geography.inclusion.{rule}" for decision in decisions
        ):
            return (
                DimensionalDecision.PASS,
                f"inclusion.{rule}",
                "Explicit inclusion contains the candidate country.",
            )
    return (
        DimensionalDecision.UNKNOWN,
        "inclusion.missing",
        "No reviewed inclusion establishes geographic eligibility.",
    )


def _has_contradiction(
    candidate: CountryCode,
    inclusions: tuple[GeographicInclusion, ...],
    evaluated: tuple[tuple[DimensionalDecision, GeographicRestriction], ...],
) -> bool:
    failures = tuple(
        fact for outcome, fact in evaluated if outcome is DimensionalDecision.FAIL
    )
    if not failures:
        return False
    if any(outcome is DimensionalDecision.PASS for outcome, _ in evaluated):
        return True
    for fact in failures:
        negative_scope = (
            frozenset(
                country for alias in fact.aliases for country in (_scope(alias) or ())
            )
            if fact.kind is RestrictionKind.EXCLUSION
            else frozenset((candidate,))
        )
        if any(
            scope is not None and candidate in scope and scope <= negative_scope
            for inclusion in inclusions
            for scope in (_scope(inclusion.alias),)
        ):
            return True
    return False
