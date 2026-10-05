"""Offline HTML contract and hostile-source presentation checks."""

from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path

import pytest
from borderless.reporting import SearchReport, render_html


class Document(HTMLParser):
    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.attributes: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attributes.append((tag, dict(attrs)))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def test_html_snapshot_landmarks_and_complete_visible_data(
    synthetic_report: SearchReport,
) -> None:
    rendered = render_html(synthetic_report)
    assert rendered == render_html(synthetic_report)
    assert (
        rendered.encode()
        == (Path(__file__).parent / "fixtures" / "report.html").read_bytes()
    )
    document = Document(rendered)
    assert document.tags.count("main") == 1
    assert document.tags.count("h1") == 1
    assert document.tags.count("article") == 3
    assert {"header", "footer", "h2", "h3", "dl", "dt", "dd"} <= set(document.tags)
    visible = " ".join(document.text)
    for value in (
        "Société",
        "UNCERTAIN",
        "UNKNOWN",
        synthetic_report.disclaimer,
        synthetic_report.report_id,
        "supporting evidence unavailable",
        "No evidence provided",
        "synthetic.geography.unverified",
        "Invented",
    ):
        assert value in visible
    assert [visible.index(job.job_id) for job in synthetic_report.jobs] == sorted(
        visible.index(job.job_id) for job in synthetic_report.jobs
    )
    assert 'lang="en"' in rendered and 'charset="utf-8"' in rendered


def test_source_markup_is_only_text_and_attribute_values(
    synthetic_report: SearchReport,
) -> None:
    payload = '<script>alert("x")</script><img src=x onerror=alert(1)>'
    job = synthetic_report.jobs[0]
    url = 'https://example.org/?q="><script>alert(1)</script>&x="'
    evidence = replace(job.evidence[0], quote=payload, end=len(payload), source_url=url)
    hostile_job = replace(
        job,
        title=payload,
        company=payload,
        canonical_url=url,
        evidence=(evidence,),
        unknowns=(payload,),
        contradictions=(payload,),
        trace=tuple(
            replace(entry, explanation=payload, inputs=(payload,), evidence=(evidence,))
            for entry in job.trace
        ),
        provenance=tuple(
            replace(item, provider=payload, warnings=(payload,))
            for item in job.provenance
        ),
    )
    report = replace(
        synthetic_report,
        jobs=(hostile_job, *synthetic_report.jobs[1:]),
        disclaimer=payload,
        attributions=tuple(
            replace(item, name=payload, notice=payload, url=url)
            for item in synthetic_report.attributions
        ),
    )
    document = Document(render_html(report))
    assert not {"script", "img", "iframe", "object", "embed", "form", "style"} & set(
        document.tags
    )
    assert payload in " ".join(document.text)
    for tag, attributes in document.attributes:
        assert not any(name.startswith("on") for name in attributes)
        if tag == "a" and attributes.get("href") != "#report":
            assert attributes["rel"] == "noopener noreferrer"
            assert attributes["href"] in {
                url,
                "https://example.org/jobs/synthetic-02",
                "https://example.org/jobs/synthetic-03",
            }
    assert any(attrs.get("href") == url for _, attrs in document.attributes)


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,<script>x</script>",
        "file:///etc/passwd",
        "//example.org",
        "https://user:pass@example.org",
        "https://example.org/\n",
    ],
)
def test_unsafe_links_fail_closed(synthetic_report: SearchReport, url: str) -> None:
    with pytest.raises(ValueError):
        replace(synthetic_report.jobs[0], canonical_url=url)
    with pytest.raises(ValueError):
        replace(synthetic_report.attributions[0], url=url)
    with pytest.raises(ValueError):
        replace(synthetic_report.jobs[0].evidence[0], source_url=url)


def test_empty_and_missing_metadata_remain_visible(
    synthetic_report: SearchReport,
) -> None:
    report = replace(synthetic_report, jobs=(), total=0, attributions=(), freshness=())
    visible = " ".join(Document(render_html(report)).text)
    assert "No jobs on this page" in visible
    assert "No entries" in visible
    assert "0" in visible and report.disclaimer in visible


def test_saved_utf8_artifact_needs_no_remote_resources(
    synthetic_report: SearchReport,
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "report.html"
    artifact.write_text(render_html(synthetic_report), encoding="utf-8")
    document = Document(artifact.read_text(encoding="utf-8"))
    assert artifact.as_uri().startswith("file:")
    assert not {"script", "style", "link", "img", "iframe", "object", "embed"} & set(
        document.tags
    )
    assert not any(
        "src" in attrs or "srcset" in attrs for _, attrs in document.attributes
    )
    assert any(
        attrs.get("http-equiv") == "Content-Security-Policy"
        for _, attrs in document.attributes
    )
