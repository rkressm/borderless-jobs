"""Validate annotations and run the offline protected eligibility smoke eval."""

import json
from dataclasses import dataclass, replace
from pathlib import Path
from zoneinfo import TZPATH, ZoneInfo

from borderless.domain import (
    DimensionalDecision,
    GlobalVerdict,
    SchemaVersion,
    Value,
    require_text,
)
from borderless.eligibility import EligibilityInputs, evaluate_eligibility

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "evals" / "cases" / "m2-core.jsonl"


@dataclass(frozen=True, slots=True)
class ProtectedCase(Value):
    case_id: str
    schema_version: SchemaVersion
    canonical_text: str
    inputs: EligibilityInputs
    expected_geography: DimensionalDecision
    expected_engagement: DimensionalDecision
    expected_timezone: DimensionalDecision
    expected_verdict: GlobalVerdict
    expected_annotation: bool
    rationale: str
    reviewed_by: str
    review_reference: str

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        for text in (
            self.case_id,
            self.rationale,
            self.reviewed_by,
            self.review_reference,
        ):
            require_text(text)
        if not self.canonical_text.strip():
            raise ValueError("Canonical text must be nonempty")
        if self.schema_version != SchemaVersion("1.0.0"):
            raise ValueError("Unsupported annotation schema")
        if self.reviewed_by == "pending":
            raise ValueError("Protected case needs independent review")
        evidence = (
            *(fact.evidence for fact in self.inputs.inclusions),
            *(fact.evidence for fact in self.inputs.restrictions),
            *(fact.evidence for fact in self.inputs.engagement_facts),
            *(fact.evidence for fact in self.inputs.timezone_facts),
        )
        for span in evidence:
            span.verify(self.canonical_text)
            if span.job_version_id != self.case_id:
                raise ValueError("Evidence belongs to a different immutable case")


def load_cases(path: Path = CORPUS) -> tuple[ProtectedCase, ...]:
    if path.stat().st_size > 1_000_000:
        raise ValueError("Annotation corpus exceeds size limit")
    cases = tuple(
        ProtectedCase.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    if not cases:
        raise ValueError("Empty annotation corpus")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("Duplicate protected case identifier")
    fingerprints = [json.dumps(case.inputs.to_dict(), sort_keys=True) for case in cases]
    if len(set(fingerprints)) != len(cases) or len(
        {case.canonical_text for case in cases}
    ) != len(cases):
        raise ValueError("Duplicate protected case content")
    return cases


def timezone_data_version() -> str:
    for directory in TZPATH:
        metadata = Path(directory) / "tzdata.zi"
        if metadata.is_file():
            line = metadata.read_text(encoding="utf-8").splitlines()[0]
            if line.startswith("# version "):
                return line.removeprefix("# version ")
    raise ValueError(
        "System IANA tzdata.zi version metadata is required for eval replay"
    )


def evaluate_cases(cases: tuple[ProtectedCase, ...]) -> tuple[str, ...]:
    version = timezone_data_version()
    results = []
    for case in cases:
        inputs = case.inputs
        zone_names = {fact.window.zone for fact in inputs.timezone_facts if fact.window}
        if inputs.availability:
            zone_names.add(inputs.availability.zone)
        zones = {name: ZoneInfo(name) for name in sorted(zone_names)}
        if zone_names:
            inputs = replace(inputs, timezone_data_version=version)
        result = evaluate_eligibility(inputs, zones=zones)
        actual = (
            result.geography.outcome,
            result.engagement.outcome,
            result.timezone.outcome,
            result.verdict,
            result.trace[-1].annotation_candidate,
        )
        expected = (
            case.expected_geography,
            case.expected_engagement,
            case.expected_timezone,
            case.expected_verdict,
            case.expected_annotation,
        )
        if actual != expected:
            raise AssertionError(
                f"Protected case {case.case_id}: expected {expected}, got {actual}"
            )
        results.append(
            json.dumps(
                {"case_id": case.case_id, "assessment": result.to_dict()},
                sort_keys=True,
            )
        )
    return tuple(results)


def main() -> int:
    cases = load_cases()
    evaluate_cases(cases)
    print(
        f"Protected eligibility eval: {len(cases)} passed (IANA {timezone_data_version()})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
