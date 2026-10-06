"""Kill representative rule defects against independently annotated cases."""

import inspect
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

from borderless.eligibility import assessment, geographic_policy, verdict

from scripts.eligibility_eval import evaluate_cases, load_cases


def mutated_function(
    function: Callable[..., Any], old: str, new: str
) -> Callable[..., Any]:
    source = inspect.getsource(function)
    if source.count(old) != 1:
        raise AssertionError("Fault injection seam changed; review the mutation")
    namespace = dict(function.__globals__)
    exec(compile(source.replace(old, new), "<eligibility-fault>", "exec"), namespace)
    return namespace[function.__name__]  # type: ignore[no-any-return]


def check_fault_detection() -> tuple[str, ...]:
    cases = load_cases()
    faults = (
        (
            "exclusion-precedence",
            geographic_policy,
            "_geographic_outcome",
            "for kind in (RestrictionKind.EXCLUSION, RestrictionKind.ALLOWLIST):",
            "for kind in ():",
        ),
        (
            "fail-composition",
            verdict,
            "compose_verdict",
            "return GlobalVerdict.NO",
            "return GlobalVerdict.YES",
        ),
        (
            "unknown-composition",
            verdict,
            "compose_verdict",
            "return GlobalVerdict.UNCERTAIN",
            "return GlobalVerdict.YES",
        ),
    )
    killed = []
    for name, module, attribute, old, new in faults:
        mutant = mutated_function(getattr(module, attribute), old, new)
        with patch.object(module, attribute, mutant):
            with patch.object(
                assessment,
                "compose_verdict",
                mutant if module is verdict else verdict.compose_verdict,
            ):
                try:
                    evaluate_cases(cases)
                except AssertionError as error:
                    if "Protected case" not in str(error):
                        raise
                    killed.append(name)
                else:
                    raise AssertionError(f"Surviving eligibility fault: {name}")
    return tuple(killed)


def main() -> int:
    print("Eligibility faults killed: " + ", ".join(check_fault_detection()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
