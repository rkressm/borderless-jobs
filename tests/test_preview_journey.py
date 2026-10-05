"""M1 journey: CLI arguments produce identical, semantically equivalent artifacts."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import NoReturn

import pytest
from borderless.cli import main
from borderless.reporting import SearchReport


@dataclass
class Element:
    tag: str
    attributes: dict[str, str | None] = field(default_factory=dict)
    children: list["Element | str"] = field(default_factory=list)

    def elements(self, tag: str) -> list["Element"]:
        return [
            item
            for item in self.children
            if isinstance(item, Element) and item.tag == tag
        ]

    def text(self) -> str:
        return "".join(
            item.text() if isinstance(item, Element) else item for item in self.children
        )


class Artifact(HTMLParser):
    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(text)
        self.close()
        assert self.stack == [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = Element(tag, dict(attrs))
        self.stack[-1].children.append(element)
        if tag != "meta":
            self.stack.append(element)

    def handle_endtag(self, tag: str) -> None:
        assert self.stack[-1].tag == tag
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def assert_fields(container: Element, expected: dict[str, object]) -> None:
    definitions = container.elements("dl")
    assert len(definitions) == 1
    labels = definitions[0].elements("dt")
    values = definitions[0].elements("dd")
    assert len(labels) == len(values) == len(expected)
    for label, actual, (name, value) in zip(
        labels, values, expected.items(), strict=True
    ):
        assert label.text() == name.replace("_", " ").capitalize()
        assert_value(actual, value, name)


def assert_value(actual: Element, expected: object, name: str = "") -> None:
    if isinstance(expected, dict):
        assert_fields(actual, expected)
    elif isinstance(expected, list) and expected:
        lists = actual.elements("ul")
        assert len(lists) == 1
        items = lists[0].elements("li")
        assert len(items) == len(expected)
        for item, value in zip(items, expected, strict=True):
            assert_value(item, value)
    else:
        visible = str(expected) if expected is not None else "Not provided"
        if expected == []:
            visible = "No evidence provided" if name == "evidence" else "No entries"
        assert actual.text() == visible
        if name in {"url", "source_url", "canonical_url"}:
            links = actual.elements("a")
            assert len(links) == 1
            assert links[0].attributes["href"] == expected


def assert_same_report(html: str, report: SearchReport) -> None:
    body = Artifact(html).root.elements("html")[0].elements("body")[0]
    sections = body.elements("main")[0].elements("section")
    assert [section.elements("h2")[0].text() for section in sections] == [
        "Report metadata",
        "Search specification",
        "Data freshness",
        "Source attribution",
        "Jobs",
    ]
    data = report.to_dict()
    metadata = {
        key: value
        for key, value in data.items()
        if key
        not in {"specification", "freshness", "attributions", "jobs", "disclaimer"}
    }
    assert_fields(sections[0], metadata)
    assert_fields(sections[1], report.specification.to_dict())
    assert_value(sections[2], data["freshness"])
    assert_value(sections[3], data["attributions"])
    articles = sections[4].elements("article")
    assert len(articles) == len(report.jobs)
    for article, job in zip(articles, report.jobs, strict=True):
        assert article.elements("h3")[0].text() == job.title
        assert_fields(
            article,
            {key: value for key, value in job.to_dict().items() if key != "title"},
        )
    assert body.elements("footer")[0].elements("p")[0].text() == report.disclaimer


def test_cli_preview_artifacts_are_deterministic_and_semantically_equal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def no_network(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError(
            "The synthetic preview must never open a network connection"
        )

    monkeypatch.setattr("socket.socket", no_network)
    monkeypatch.setattr("socket.create_connection", no_network)
    monkeypatch.chdir(tmp_path)
    instant = datetime(2026, 10, 5, tzinfo=UTC)
    arguments = [
        "search",
        "--country",
        "BO",
        "--role",
        "data-engineer",
        "--as-of",
        instant.isoformat(),
    ]
    artifacts: list[tuple[bytes, bytes]] = []
    for output in ("first", "second"):
        assert main([*arguments, "--format", "json"], clock=lambda: instant) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        json_path = tmp_path / (output + ".json")
        json_path.write_text(captured.out, encoding="utf-8", newline="\n")
        assert (
            main(
                [*arguments, "--format", "html", "--output", output],
                clock=lambda: instant,
            )
            == 0
        )
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""
        html_path = tmp_path / output / "report.html"
        report = SearchReport.from_dict(json.loads(json_path.read_bytes()))
        assert_same_report(html_path.read_text(encoding="utf-8"), report)
        artifacts.append((json_path.read_bytes(), html_path.read_bytes()))
    assert artifacts[0] == artifacts[1]
    golden = Path(__file__).parent / "fixtures"
    assert artifacts[0] == (
        (golden / "report.json").read_bytes(),
        (golden / "report.html").read_bytes(),
    )
