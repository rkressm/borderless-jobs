"""Behavior checks for the architectural import gate."""

from pathlib import Path

from scripts.check_imports import check_repository, check_source


def test_legal_empty_package_graph_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    assert check_repository(root) == []


def test_eligibility_rejects_framework_and_io_imports() -> None:
    source = "import fastapi\nfrom pathlib import Path\n"
    violations = check_source(source, "eligibility", "fixture.py")
    assert len(violations) == 2
    assert "fastapi" in violations[0]
    assert "pathlib" in violations[1]


def test_inward_domain_import_is_allowed() -> None:
    assert (
        check_source(
            "from borderless.domain import Country\n", "eligibility", "fixture.py"
        )
        == []
    )


def test_application_module_cannot_import_cli_adapter() -> None:
    violations = check_source("from borderless import cli\n", "search", "fixture.py")
    assert len(violations) == 1
    assert "borderless.cli" in violations[0]


def test_relative_import_cannot_cross_forbidden_boundary() -> None:
    violations = check_source("from ..cli import main\n", "eligibility", "fixture.py")
    assert len(violations) == 1
    assert "borderless.cli" in violations[0]
