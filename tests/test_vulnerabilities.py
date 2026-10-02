"""A synthetic audit report proves the vulnerability gate fails closed."""

from scripts.check_vulnerabilities import audit_errors


def test_safe_audit_report_passes() -> None:
    report = {
        "summary": {"audited_packages": 21, "vulnerabilities": 0, "adverse_statuses": 0}
    }

    assert audit_errors(report) == []


def test_synthetic_vulnerable_dependency_is_rejected() -> None:
    report = {
        "summary": {"audited_packages": 1, "vulnerabilities": 1, "adverse_statuses": 0}
    }

    assert audit_errors(report) == ["Audit found 1 vulnerabilities"]


def test_missing_audit_data_is_rejected() -> None:
    assert audit_errors({}) == ["Missing audit summary"]


def test_adverse_status_is_rejected() -> None:
    report = {
        "summary": {"audited_packages": 1, "vulnerabilities": 0, "adverse_statuses": 1}
    }

    assert audit_errors(report) == ["Audit found 1 adverse_statuses"]
