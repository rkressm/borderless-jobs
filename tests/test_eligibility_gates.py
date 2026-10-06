import builtins
import io
import socket
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from borderless.domain import CountryCode
from borderless.eligibility import EligibilityInputs, evaluate_eligibility

from scripts.check_eligibility_coverage import PREFIX, branch_percentage
from scripts.check_eligibility_faults import check_fault_detection
from scripts.eligibility_eval import load_cases


def test_branch_gate_rejects_low_or_absent_measurements() -> None:
    def report(total: int, covered: int) -> dict[str, Any]:
        return {
            "files": {
                PREFIX + "rules.py": {
                    "summary": {"num_branches": total, "covered_branches": covered}
                }
            }
        }

    assert branch_percentage(report(10, 9)) == 90
    reports: tuple[dict[str, Any], ...] = (report(10, 8), report(0, 0), {"files": {}})
    for value in reports:
        with pytest.raises(ValueError):
            branch_percentage(value)


def test_protected_cases_kill_representative_rule_faults() -> None:
    assert check_fault_detection() == (
        "exclusion-precedence",
        "fail-composition",
        "unknown-composition",
    )


def test_assessment_needs_no_io_or_timezone_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = load_cases()[9].inputs
    zones = {name: ZoneInfo(name) for name in ("America/New_York", "America/La_Paz")}
    expected = evaluate_eligibility(inputs, zones=zones)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Eligibility attempted I/O")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(io, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr("zoneinfo.ZoneInfo", forbidden)
    assert evaluate_eligibility(inputs, zones=zones) == expected
    assert evaluate_eligibility(
        EligibilityInputs(CountryCode("BO"), datetime(2026, 1, 1, tzinfo=UTC)), zones={}
    ).trace
