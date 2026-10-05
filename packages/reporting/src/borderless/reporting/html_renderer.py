"""Offline HTML presentation of canonical data; source markup is always text."""

from html import escape

from borderless.domain import require_public_url

from .contracts import JobResult, SearchReport

_DOCUMENT_START = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'none'; form-action 'none'">
<title>Borderless Jobs search report</title>
</head>
<body>
<header><h1>Borderless Jobs search report</h1><a href="#report">Skip to report</a></header>
<main id="report">
"""


def render_html(report: SearchReport) -> str:
    """Render all public fields, preserving array order and existing assessments."""
    metadata = report.to_dict()
    for field in ("jobs", "attributions", "freshness", "disclaimer", "specification"):
        del metadata[field]
    sections = [
        _section("Report metadata", _fields(metadata)),
        _section("Search specification", _fields(report.specification.to_dict())),
        _section(
            "Data freshness", _value([item.to_dict() for item in report.freshness])
        ),
        _section(
            "Source attribution",
            _value([item.to_dict() for item in report.attributions]),
        ),
        _section(
            "Jobs",
            "".join(_job(job) for job in report.jobs) or "<p>No jobs on this page.</p>",
        ),
    ]
    return (
        _DOCUMENT_START
        + "\n".join(sections)
        + (
            "\n</main>\n<footer><p>"
            + escape(report.disclaimer)
            + "</p></footer>\n</body>\n</html>\n"
        )
    )


def _section(title: str, content: str) -> str:
    return "<section><h2>" + escape(title) + "</h2>" + content + "</section>"


def _job(job: JobResult) -> str:
    data = job.to_dict()
    del data["title"]
    return "<article><h3>" + escape(job.title) + "</h3>" + _fields(data) + "</article>"


def _fields(data: dict[str, object]) -> str:
    entries = (
        "<dt>"
        + escape(key.replace("_", " ").capitalize())
        + "</dt><dd>"
        + _value(value, key)
        + "</dd>"
        for key, value in data.items()
    )
    return "<dl>" + "".join(entries) + "</dl>"


def _value(value: object, field: str = "") -> str:
    if isinstance(value, dict):
        return _fields(value)
    if isinstance(value, list):
        if not value:
            return "No evidence provided" if field == "evidence" else "No entries"
        return (
            "<ul>"
            + "".join("<li>" + _value(item) + "</li>" for item in value)
            + "</ul>"
        )
    if field in {"url", "canonical_url", "source_url"}:
        require_public_url(str(value))
        url = escape(str(value), quote=True)
        return '<a href="' + url + '" rel="noopener noreferrer">' + url + "</a>"
    return escape(str(value)) if value is not None else "Not provided"
