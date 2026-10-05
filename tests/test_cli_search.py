"""CLI behavior through the real offline use case and renderers."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from borderless.cli import main
from borderless.reporting import SearchReport

NOW = datetime(2026, 10, 5, tzinfo=UTC)
ARGS = ["search", "--country", "BO", "--role", "data-engineer"]


def test_json_stdout_is_a_complete_uncertain_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(ARGS, clock=lambda: NOW) == 0
    captured = capsys.readouterr()
    report = SearchReport.from_dict(json.loads(captured.out))
    assert captured.err == ""
    assert report.total == 3
    assert [job.verdict.value for job in report.jobs] == ["UNCERTAIN"] * 3
    assert report.jobs[2].evidence == ()
    assert report.created_at == report.specification.as_of == NOW


@pytest.mark.parametrize(
    "extra",
    [
        ["--role", "astronaut"],
        ["--verdict", "YES"],
        ["--source", "other"],
        ["--offset", "99"],
        ["--as-of", "2020-01-01T00:00:00Z"],
    ],
)
def test_empty_results_are_successful(
    extra: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([*ARGS, *extra], clock=lambda: NOW) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["jobs"] == []
    assert captured.err == ""


def test_normalization_pagination_and_explicit_as_of(
    capsys: pytest.CaptureFixture[str],
) -> None:
    arguments = [
        *ARGS,
        "--country",
        "bo",
        "--role",
        "Data Engineer",
        "--offset",
        "1",
        "--limit",
        "1",
        "--source",
        "synthetic",
        "--verdict",
        "UNCERTAIN",
        "--as-of",
        "2026-10-04T20:00:00-04:00",
    ]
    assert main(arguments, clock=lambda: NOW) == 0
    report = SearchReport.from_dict(json.loads(capsys.readouterr().out))
    assert report.specification.role == "data-engineer"
    assert report.specification.as_of == NOW
    assert report.total == 3
    assert [job.job_id for job in report.jobs] == ["synthetic-02"]


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["unknown"],
        ["search"],
        [*ARGS, "--unknown"],
        [*ARGS, "--country", "invalid"],
        [*ARGS, "--role", "<script>"],
        [*ARGS, "--limit", "0"],
        [*ARGS, "--limit", "101"],
        [*ARGS, "--offset", "-1"],
        [*ARGS, "--limit", "x"],
        [*ARGS, "--verdict", "MAYBE"],
        [*ARGS, "--source", "synthetic", "--source", "synthetic"],
        [*ARGS, "--as-of", "2026-10-05"],
        [*ARGS, "--as-of", "invalid"],
        [*ARGS, "--as-of", ""],
        [*ARGS, "--format", "html", "--output", ""],
        [*ARGS, "--format", "html", "--output", "bad\npath"],
        [*ARGS, "--as-of", "2027-01-01T00:00:00Z"],
        [*ARGS, "--format", "html"],
        [*ARGS, "--output", "unused"],
    ],
)
def test_invalid_arguments_are_machine_readable_without_stdout(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(arguments, clock=lambda: NOW) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["code"] == "invalid_arguments"
    assert "<script>" not in captured.err


def test_html_output_is_utf8_and_does_not_overwrite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "preview"
    arguments = [*ARGS, "--format", "html", "--output", str(output)]
    assert main(arguments, clock=lambda: NOW) == 0
    artifact = output / "report.html"
    original = artifact.read_bytes()
    assert "Société" in original.decode("utf-8")
    assert "<main" in original.decode() and "UNCERTAIN" in original.decode()
    assert capsys.readouterr().out == ""
    assert main(arguments, clock=lambda: NOW) == 3
    assert artifact.read_bytes() == original
    assert sorted(path.name for path in output.iterdir()) == ["report.html"]
    assert json.loads(capsys.readouterr().err)["error"]["code"] == "output_error"


def test_output_directory_failure_and_symlink_are_safe(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    existing = tmp_path / "existing"
    existing.write_text("keep", encoding="utf-8")
    assert (
        main([*ARGS, "--format", "html", "--output", str(existing)], clock=lambda: NOW)
        == 3
    )
    assert existing.read_text() == "keep"
    output = tmp_path / "output"
    output.mkdir()
    (output / "report.html").symlink_to(existing)
    assert (
        main([*ARGS, "--format", "html", "--output", str(output)], clock=lambda: NOW)
        == 3
    )
    assert existing.read_text() == "keep"
    assert capsys.readouterr().out == ""


def test_stdout_failure_has_an_operational_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class BrokenStream:
        def write(self, text: str) -> int:
            raise BrokenPipeError("private diagnostic")

    monkeypatch.setattr("sys.stdout", BrokenStream())
    assert main(ARGS, clock=lambda: NOW) == 3
    captured = capsys.readouterr()
    assert "private diagnostic" not in captured.err
    assert json.loads(captured.err)["error"]["code"] == "output_error"


def test_invalid_report_has_a_sanitized_operational_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from borderless.reporting import ReportBuilder
    from borderless.search import SearchSpecification

    def invalid_report(
        self: ReportBuilder, specification: SearchSpecification
    ) -> SearchReport:
        raise ValueError("private snapshot diagnostic")

    monkeypatch.setattr(ReportBuilder, "build", invalid_report)
    assert main(ARGS, clock=lambda: NOW) == 4
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "private snapshot diagnostic" not in captured.err
    assert json.loads(captured.err)["error"]["code"] == "report_error"


def test_installed_entrypoint_propagates_exit_codes() -> None:
    import subprocess
    import sys

    executable = Path(sys.executable).with_name("borderless")
    valid = subprocess.run(
        [str(executable), *ARGS], capture_output=True, text=True, check=False
    )
    assert valid.returncode == 0 and valid.stderr == ""
    assert json.loads(valid.stdout)["schema_version"] == {"value": "1.0.0"}
    invalid = subprocess.run(
        [str(executable), "search"], capture_output=True, text=True, check=False
    )
    assert invalid.returncode == 2 and invalid.stdout == ""
    assert json.loads(invalid.stderr)["error"]["code"] == "invalid_arguments"


@pytest.mark.parametrize("extra", [[], ["--role", "astronaut"]])
def test_closed_stdout_pipe_returns_the_documented_exit_code(extra: list[str]) -> None:
    import subprocess
    import sys

    executable = Path(sys.executable).with_name("borderless")
    process = subprocess.Popen(
        [str(executable), *ARGS, *extra], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    assert process.stdout is not None
    process.stdout.close()
    assert process.stderr is not None
    error = process.stderr.read().decode("utf-8")
    process.stderr.close()
    assert process.wait(timeout=10) == 3
    assert json.loads(error)["error"]["code"] == "output_error"
