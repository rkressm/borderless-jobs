# Catalog ownership

`borderless.catalog` owns private source provenance and canonical normalization;
future tasks add persistence, identity, history, and closure. Connectors cannot write
normalized records directly. The current implementation uses only the standard library
and existing domain/connector contracts, with no database or network access.

`normalize_description(raw, job_version_id, description_html)` receives the immutable
raw envelope and the HTML description selected by a source mapper. It returns a
`NormalizedDocument` containing that exact private envelope, the caller-assigned job
version ID, canonical plain text, and normalization version `1.0.0`. No source-specific
JSON fields are interpreted here. Empty input produces empty text rather than facts.
Both raw payload and canonical text are excluded from diagnostic `repr`. Serialization
is for private catalog storage; public reports must use reviewed summaries/evidence.
Persistence and retention enforcement arrive with the catalog tasks, not this function.

## Canonical text version 1.0.0

- Parse HTML with Python 3.12's standard-library `HTMLParser`, decoding character
  references once. Preserve visible text and inline word boundaries. Ignore attributes,
  URLs, comments, declarations, and image alt text. This is text extraction, not
  browser rendering or HTML sanitization; consumers must still escape plain text.
- Separate known block elements (paragraphs, lists, tables, headings, breaks, etc.)
  with whitespace. Inline markup does not split words such as `Con<b>tractor</b>`.
- Discard `head`, `script`, `style`, `template`, `noscript`, `iframe`, `object`, `svg`,
  and `math` subtrees. An unclosed discarded element suppresses the remaining content.
  Discarded boundaries insert whitespace to avoid merging adjacent words. Discarded
  nesting beyond 64 levels is rejected. Self-closing discarded tags add a boundary.
- Tolerate malformed visible markup using the parser's deterministic recovery; reject
  unsupported declarations/parser errors. There is no browser DOM repair or CSS visibility
  evaluation. Literal escaped markup remains literal text and is not parsed a second time.
- Normalize Unicode to NFC, preserving case, punctuation, repeated text, and joiners
  U+200C/U+200D (including emoji sequences). Replace other Unicode control/format
  characters with spaces. Collapse all Unicode whitespace to one ASCII space, trim ends.
  No compatibility folding, deduplication, transliteration, or semantic inference occurs.
- Require valid UTF-8 and at most 1,000,000 bytes for both input and canonical output.
  No truncation is permitted, as it would silently change evidence and facts.

Normalization changes require a version increment; immutable stored versions must
never be rewritten by a newer algorithm. Offsets are half-open Python character
indices into this exact canonical string, not UTF-8 bytes or raw HTML positions.
`NormalizedDocument.verify_evidence()` checks the job version, normalization version,
canonical source URL, and exact excerpt. Repeated phrases retain distinct offsets.
