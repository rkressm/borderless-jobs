"""Versioned engagement rules over explicit listing facts, not legal advice."""

from dataclasses import dataclass
from enum import StrEnum

from borderless.domain import (
    CountryCode,
    DimensionalDecision,
    Evidence,
    FactProvenance,
    PolicyVersion,
    Value,
)

from .geographic_policy import _ordered
from .geography import GEOGRAPHIC_REFERENCE

_ENGAGEMENT_POLICY_VERSION = PolicyVersion("1.0.0")
_REVIEWED_COUNTRIES = frozenset(
    country.code for country in GEOGRAPHIC_REFERENCE.countries
)


class EngagementKind(StrEnum):
    CONTRACTOR_PERMITTED = "CONTRACTOR_PERMITTED"
    CONTRACTOR_PROHIBITED = "CONTRACTOR_PROHIBITED"
    EOR_SUPPORTED = "EOR_SUPPORTED"
    EOR_UNSUPPORTED = "EOR_UNSUPPORTED"
    PAYROLL_RESTRICTED = "PAYROLL_RESTRICTED"
    WORK_AUTHORIZATION_REQUIRED = "WORK_AUTHORIZATION_REQUIRED"
    VISA_REQUIRED = "VISA_REQUIRED"


@dataclass(frozen=True, slots=True)
class EngagementFact(Value):
    """Validated facts applying to this job; countries are explicit coverage/scope.

    Payroll and authorization countries are exhaustive mandatory jurisdictions.
    Visa facts matter only with an explicit requirement to relocate/work abroad.
    EOR coverage must be attested for the candidate, never inferred from a brand.
    """

    kind: EngagementKind
    evidence: Evidence
    provenance: FactProvenance
    countries: tuple[CountryCode, ...] = ()
    worldwide: bool = False
    requires_foreign_work: bool = False

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        if self.worldwide and self.kind not in {
            EngagementKind.CONTRACTOR_PERMITTED,
            EngagementKind.CONTRACTOR_PROHIBITED,
        }:
            raise ValueError("Only explicit contractor facts support worldwide scope")
        if self.requires_foreign_work and self.kind is not EngagementKind.VISA_REQUIRED:
            raise ValueError("Foreign work flag applies only to visa requirements")
        object.__setattr__(
            self,
            "countries",
            tuple(sorted(set(self.countries), key=lambda code: code.value)),
        )


def _covers(fact: EngagementFact, candidate: CountryCode) -> bool:
    return fact.worldwide or candidate in fact.countries


def _restriction_rule(fact: EngagementFact, candidate: CountryCode) -> str | None:
    rules = {
        EngagementKind.PAYROLL_RESTRICTED: "payroll",
        EngagementKind.WORK_AUTHORIZATION_REQUIRED: "work_authorization",
        EngagementKind.VISA_REQUIRED: "visa",
    }
    if fact.kind not in rules or (
        fact.kind is EngagementKind.VISA_REQUIRED and not fact.requires_foreign_work
    ):
        return None
    if (
        fact.countries
        and set(fact.countries) <= _REVIEWED_COUNTRIES
        and candidate not in fact.countries
    ):
        return rules[fact.kind]
    return None


def _unresolved(fact: EngagementFact) -> bool:
    if fact.kind is EngagementKind.VISA_REQUIRED and not fact.requires_foreign_work:
        return False
    return bool(set(fact.countries) - _REVIEWED_COUNTRIES) or (
        not fact.countries and not fact.worldwide
    )


@dataclass(frozen=True, slots=True)
class EngagementDecision(Value):
    outcome: DimensionalDecision
    rule_id: str
    policy_version: PolicyVersion
    reference_version: PolicyVersion
    candidate: CountryCode
    facts: tuple[EngagementFact, ...]
    explanation: str
    annotation_candidate: bool = False
    disclaimer: str = "Informational summary of listing evidence; not legal advice."


def evaluate_engagement(
    candidate: CountryCode,
    facts: tuple[EngagementFact, ...] = (),
    policy_version: PolicyVersion = _ENGAGEMENT_POLICY_VERSION,
) -> EngagementDecision:
    if policy_version != _ENGAGEMENT_POLICY_VERSION:
        raise ValueError("Unsupported engagement policy version")
    facts = _ordered(facts)
    outcome, rule, explanation = _engagement_outcome(candidate, facts)
    return EngagementDecision(
        outcome,
        f"engagement.{rule}",
        policy_version,
        GEOGRAPHIC_REFERENCE.version,
        candidate,
        facts,
        explanation,
        annotation_candidate=rule == "contradiction",
    )


def _engagement_outcome(
    candidate: CountryCode, facts: tuple[EngagementFact, ...]
) -> tuple[DimensionalDecision, str, str]:
    if candidate not in _REVIEWED_COUNTRIES:
        return (
            DimensionalDecision.UNKNOWN,
            "candidate.unsupported",
            "Candidate country is not reviewed.",
        )
    supported = {fact.kind for fact in facts if _covers(fact, candidate)} & {
        EngagementKind.CONTRACTOR_PERMITTED,
        EngagementKind.EOR_SUPPORTED,
    }
    denied = {fact.kind for fact in facts if _covers(fact, candidate)}
    restrictions = sorted(
        {rule for fact in facts if (rule := _restriction_rule(fact, candidate))}
    )
    conflict = (
        EngagementKind.CONTRACTOR_PERMITTED in supported
        and EngagementKind.CONTRACTOR_PROHIBITED in denied
    ) or (
        EngagementKind.EOR_SUPPORTED in supported
        and EngagementKind.EOR_UNSUPPORTED in denied
    )
    if conflict or (supported and restrictions):
        return (
            DimensionalDecision.UNKNOWN,
            "contradiction",
            "Incompatible engagement evidence requires annotation review.",
        )
    if restrictions:
        return (
            DimensionalDecision.FAIL,
            f"restriction.{restrictions[0]}",
            "Mandatory foreign payroll, authorization or visa requirement excludes this remote engagement.",
        )
    if any(_unresolved(fact) for fact in facts):
        return (
            DimensionalDecision.UNKNOWN,
            "mechanism.missing",
            "Engagement scope or coverage is not established.",
        )
    for kind, rule in (
        (EngagementKind.CONTRACTOR_PERMITTED, "contractor"),
        (EngagementKind.EOR_SUPPORTED, "eor"),
    ):
        if kind in supported:
            return (
                DimensionalDecision.PASS,
                f"{rule}.supported",
                "An explicit engagement mechanism covers the candidate country.",
            )
    return (
        DimensionalDecision.UNKNOWN,
        "mechanism.missing",
        "No supported engagement mechanism is established for the candidate country.",
    )
