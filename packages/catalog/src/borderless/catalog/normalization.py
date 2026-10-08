"""Canonical plain text v1: private raw retention and exact evidence addressing."""

import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser

from borderless.connectors import RawEnvelope
from borderless.domain import Evidence, Value, require_text

NORMALIZATION_VERSION = "1.0.0"
MAX_DESCRIPTION_BYTES = 1_000_000
BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
DISCARDED_TAGS = frozenset(
    {
        "head",
        "script",
        "style",
        "template",
        "noscript",
        "iframe",
        "object",
        "svg",
        "math",
    }
)


class _DescriptionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.discarded: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in DISCARDED_TAGS:
            if len(self.discarded) >= 64:
                raise ValueError("Discarded markup nesting exceeds 64 levels")
            self.discarded.append(tag)
            self.parts.append(" ")
        elif not self.discarded and tag in BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.discarded:
            index = len(self.discarded) - 1 - self.discarded[::-1].index(tag)
            del self.discarded[index:]
            self.parts.append(" ")
        elif not self.discarded and tag in BLOCK_TAGS:
            self.parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.discarded and tag in BLOCK_TAGS | DISCARDED_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.discarded:
            self.parts.append(data)


def _check_text_size(text: str) -> None:
    if type(text) is not str:
        raise ValueError("Description must be text")
    if len(text) > MAX_DESCRIPTION_BYTES:
        raise ValueError("Description exceeds byte limit")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError:
        raise ValueError("Description must be valid UTF-8") from None
    if size > MAX_DESCRIPTION_BYTES:
        raise ValueError("Description exceeds byte limit")


def _canonical_whitespace(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = "".join(
        " "
        if unicodedata.category(char) in {"Cc", "Cf"}
        and char not in {"\u200c", "\u200d"}
        else char
        for char in text
    )
    return " ".join(text.split())


def _normalize_html(description_html: str) -> str:
    _check_text_size(description_html)
    parser = _DescriptionParser()
    try:
        parser.feed(description_html)
        parser.close()
    except (ValueError, AssertionError):
        raise ValueError("Unsupported malformed description markup") from None
    text = _canonical_whitespace("".join(parser.parts))
    _check_text_size(text)
    return text


@dataclass(frozen=True, slots=True)
class NormalizedDocument(Value):
    job_version_id: str
    raw: RawEnvelope = field(repr=False)
    canonical_text: str = field(repr=False)
    normalization_version: str = NORMALIZATION_VERSION

    def __post_init__(self) -> None:
        Value.__post_init__(self)
        require_text(self.job_version_id)
        if self.normalization_version != NORMALIZATION_VERSION:
            raise ValueError("Unsupported normalization version")
        _check_text_size(self.canonical_text)
        if self.canonical_text != _canonical_whitespace(self.canonical_text):
            raise ValueError("Canonical text must use NFC and canonical whitespace")

    def verify_evidence(self, evidence: Evidence) -> None:
        if (
            evidence.job_version_id,
            evidence.normalization_version,
            evidence.source_url,
        ) != (
            self.job_version_id,
            self.normalization_version,
            self.raw.canonical_url,
        ):
            raise ValueError("Evidence must address this canonical source version")
        evidence.verify(self.canonical_text)


def normalize_description(
    raw: RawEnvelope,
    job_version_id: str,
    description_html: str,
) -> NormalizedDocument:
    """Normalize mapper-selected HTML while preserving its private raw envelope."""
    return NormalizedDocument(job_version_id, raw, _normalize_html(description_html))
