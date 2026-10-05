"""Public JSON artifact and stream contracts."""

import json
import sys
from pathlib import Path

import pytest
from borderless.reporting import SearchReport, render_json, write_json


def test_json_golden_utf8_and_round_trip(synthetic_report: SearchReport) -> None:
    rendered = render_json(synthetic_report)
    golden = Path(__file__).parent / "fixtures" / "report.json"
    assert rendered.encode("utf-8") == golden.read_bytes()
    assert "Société" in rendered and "\\u00e9" not in rendered
    data = json.loads(rendered)
    assert data["schema_version"] == {"value": "1.0.0"}
    assert SearchReport.from_dict(data) == synthetic_report
    assert [job["job_id"] for job in data["jobs"]] == [
        "synthetic-01",
        "synthetic-02",
        "synthetic-03",
    ]
    assert rendered == render_json(synthetic_report)


def test_stdout_contains_only_json(
    synthetic_report: SearchReport, capsys: pytest.CaptureFixture[str]
) -> None:
    assert render_json(synthetic_report)
    assert capsys.readouterr().out == ""
    write_json(synthetic_report, sys.stdout)
    captured = capsys.readouterr()
    assert captured.out == render_json(synthetic_report)
    assert captured.err == ""


def test_stream_failure_is_not_hidden(synthetic_report: SearchReport) -> None:
    with open("/dev/null", "w", encoding="utf-8") as stream:
        stream.close()
        with pytest.raises(ValueError, match="closed"):
            write_json(synthetic_report, stream)
