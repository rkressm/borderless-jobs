"""Exact canonical text and evidence offsets, independent of source markup."""

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from borderless.catalog import NormalizedDocument, normalize_description
from borderless.connectors import FixtureConnector, RawEnvelope
from borderless.domain import Evidence

RAW = RawEnvelope(
    "synthetic", "one", "https://example.com/jobs/one", '{"raw":"private"}'
)


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("", ""),
        (
            "<p>Remote <b>work</b></p><p>Bolivia<br>LATAM</p>",
            "Remote work Bolivia LATAM",
        ),
        ("Con<b>tractor</b> work", "Contractor work"),
        ("<ul><li>One<li>Two</ul>", "One Two"),
        ("<p>Broken <b>markup", "Broken markup"),
        ("Salary < 10 & unknown &bogus;", "Salary < 10 & unknown &bogus;"),
        ("A &amp; B&nbsp;&#66;&#x4f;", "A & B BO"),
        (
            "&amp;lt;b&amp;gt; &lt;script&gt;literal&lt;/script&gt;",
            "&lt;b&gt; <script>literal</script>",
        ),
        (
            "Cafe\u0301\t\n  Bolivia\u00a0—\u2003remote 👩🏽‍💻",
            "Café Bolivia — remote 👩🏽‍💻",
        ),
        ("A\x00B\u202eC\ufeffD", "A B C D"),
        ("<!-- secret --><!DOCTYPE html><p>Visible</p>", "Visible"),
        (
            "No<script>alert(1)</script>contractors<style>.yes{}</style> here",
            "No contractors here",
        ),
        ("<head><title>Private</title></head><p>Visible</p>", "Visible"),
        ("<template><p>Hidden</p><script>x</script></template>Visible", "Visible"),
        ("<svg><text>Hidden</text></svg><math>Hidden</math>Visible", "Visible"),
        (
            "<iframe src='https://example.com'>Hidden</iframe><object>Hidden</object>Visible",
            "Visible",
        ),
        ("<noscript>Hidden</noscript>Visible", "Visible"),
        ("Visible<script>unterminated", "Visible"),
        ("A<script/>B", "A B"),
        ("Remote Remote<p>Remote</p>", "Remote Remote Remote"),
        (
            "<a href='javascript:alert(1)' onclick='x()'>Visible</a><img alt='hidden'>",
            "Visible",
        ),
    ],
)
def test_exact_canonical_outputs(html: str, expected: str) -> None:
    result = normalize_description(RAW, "version-1", html)
    assert result.canonical_text == expected
    assert result.normalization_version == "1.0.0"
    assert result.raw is RAW
    assert result == normalize_description(RAW, "version-1", html)


def test_raw_retention_serialization_and_immutability() -> None:
    document = normalize_description(RAW, "version-1", "<p>Private description</p>")
    assert document.raw.payload_json == '{"raw":"private"}'
    assert (
        NormalizedDocument.from_dict(json.loads(json.dumps(document.to_dict())))
        == document
    )
    assert "private" not in repr(document)
    with pytest.raises(FrozenInstanceError):
        document.canonical_text = "modified"  # type: ignore[misc]
    with pytest.raises(ValueError):
        replace(document, normalization_version="unknown")


def test_repeated_unicode_text_has_exact_offsets_in_canonical_version() -> None:
    document = normalize_description(
        RAW, "version-1", "<p>Cafe\u0301 Bolivia</p><p>Café Bolivia</p>"
    )
    assert document.canonical_text == "Café Bolivia Café Bolivia"
    evidence = Evidence("version-1", "1.0.0", 13, 25, "Café Bolivia", RAW.canonical_url)
    document.verify_evidence(evidence)
    for invalid in (
        replace(evidence, job_version_id="version-2"),
        replace(evidence, normalization_version="2.0.0"),
        replace(evidence, start=12, end=24),
        replace(evidence, source_url="https://example.com/other"),
    ):
        with pytest.raises(ValueError):
            document.verify_evidence(invalid)


def test_size_limits_count_utf8_bytes_and_reject_invalid_unicode() -> None:
    assert (
        len(normalize_description(RAW, "v1", "a" * 1_000_000).canonical_text)
        == 1_000_000
    )
    for html in ("a" * 1_000_001, "é" * 500_001, "\ud800"):
        with pytest.raises(ValueError):
            normalize_description(RAW, "v1", html)


def test_fixture_to_document_to_verified_evidence_journey() -> None:
    path = Path(__file__).parent / "fixtures" / "connectors" / "complete.json"
    connector = FixtureConnector.load(path)
    raw = connector.fetch().jobs[0]
    description = json.loads(raw.payload_json)["description"]
    document = normalize_description(raw, "synthetic-version-1", description)
    assert document.canonical_text == "Remote from Bolivia & LATAM. Contractor work."
    evidence = Evidence(
        document.job_version_id,
        document.normalization_version,
        12,
        19,
        "Bolivia",
        raw.canonical_url,
    )
    document.verify_evidence(evidence)
    assert connector.fetch().jobs[0].payload_json == raw.payload_json


def test_excessive_discarded_nesting_is_bounded() -> None:
    with pytest.raises(ValueError, match="malformed"):
        normalize_description(RAW, "v1", "<template>" * 65 + "hidden")


def test_document_rejects_noncanonical_text_and_wrong_input_type() -> None:
    for text in (" Cafe\u0301 ", "A\nB", "A\u202eB"):
        with pytest.raises(ValueError):
            NormalizedDocument("v1", RAW, text)
    with pytest.raises(ValueError):
        normalize_description(RAW, "v1", b"bytes")  # type: ignore[arg-type]
