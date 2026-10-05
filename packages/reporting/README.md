# Canonical reports

Own immutable versioned SearchReport and job summaries, report building, and rendering. Consume search and domain values; preserve ordering, verdicts, evidence, freshness, unknowns, traces, and attribution. Renderers never decide eligibility.

Public surface: `render_json`, `write_json`, `render_html`, `ReportBuilder`, `SearchReport`, `JobResult`, `RuleTrace`, `DataFreshness`, and `SourceAttribution`. Import supported values from `borderless.reporting`; implementation submodules are private. Public contracts use standard-library and Borderless values only.

See [architecture](../../docs/architecture.md) and [import rules](../../docs/import-boundaries.md). Run `scripts/check-quality.sh all` from the repository root.

The supported report schema is `1.0.0`; unknown schema versions fail closed.
`SearchReport` stores a report ID, creation instant, independent schema/policy
versions, the complete search specification, source observations and attribution,
ordered job snapshots, total matching count before pagination, and an informational
legal disclaimer. Pagination is inherited from the specification; a page must contain
exactly `min(limit, max(0, total - offset))` jobs.

`JobResult` carries immutable job/version identities, summary and canonical link,
publication and assessment instants, global and three dimensional decisions,
evidence, ordered rule traces, unknowns, contradictions, and extraction provenance.
Trace entries retain rule ID, policy version, dimension, inputs, outcome, explanation,
and supporting evidence. No report type computes eligibility. Every job requires
attribution, freshness, trace and provenance; uncertainty requires a visible reason.
Evidence must reference the same immutable job version. Exact canonical-text checking
remains `Evidence.verify()` at the extraction/validation seam, since reports never
contain private full descriptions.

All instants require a timezone. Source observations cannot follow search `as_of`;
assessments use that exact instant and report policy version. Job IDs are unique,
and ordering follows `ResultOrderKey`. Tuples keep nested data immutable. `to_dict()`
and `from_dict()` preserve every version and reject malformed or additional fields.
JSON formatting and HTML rendering are presentation adapters over this contract.

Offline contract verification: `scripts/check-quality.sh all`, including
`tests/test_report_contract.py`, crosses the actual domain/search/reporting seams.

`ReportBuilder(search, clock, policy_version, schema_version).build(specification)`
is the application interface shared by future CLI/HTTP adapters. Inject any
`JobSearch`, a callable returning an aware datetime, and explicit typed versions.
The clock is called once per build. The use case copies existing assessments,
evidence, traces, provenance and uncertainty without computing eligibility or filling
missing evidence. Search-owned facts and candidate coverage do not enter the public
report. A substituted query, incompatible assessment policy, unsupported schema, or
invalid clock fails closed through the canonical contracts.

Source metadata sorts by source ID; job order and pre-pagination totals are preserved,
including empty and out-of-range pages. The report ID is `report-` plus the SHA-256
of the full report data excluding its ID, encoded as sorted compact UTF-8 JSON.
Identical data and an identical passed clock yield identical report data and identity;
a changed snapshot changes the identity. This internal identity encoding is
independent of the public renderer. A frozen-clock journey with
`SyntheticSearchAdapter` is covered by `tests/test_report_builder.py`, including
missing evidence and deterministic round trips. No new dependency is required.

`render_json(report)` returns the full canonical schema as Unicode JSON text, with
sorted object keys, two-space indentation, original array order, and one final LF.
`schema_version` stays explicit; no fields are renamed or omitted. Encode as UTF-8
when saving a file. This is deterministic project serialization, not an RFC 8785
canonicalization claim. `write_json(report, stream)` writes that exact text to a
caller-owned text stream (including `sys.stdout`), emits no diagnostic output, and
propagates write failures. The caller owns encoding, flushing, and closing.
`tests/fixtures/report.json` locks the complete synthetic schema and UTF-8 output.
CLI argument routing remains W09.

`render_html(report)` returns one standalone Unicode HTML5 document; save it as
UTF-8 and open it directly using a `file:` URL. It includes report/search metadata,
source freshness and attribution, ordered jobs, every assessment, evidence, trace,
unknown, contradiction, and provenance field, plus the report disclaimer. Missing
evidence and empty pages stay explicit. Standard-library HTML escaping covers all
source text and quoted attributes; outbound HTTP(S) URLs are validated again and
use `rel="noopener noreferrer"`. Unsafe links fail closed at the canonical value
seam. Source markup is displayed as text, never inserted as HTML.

The artifact contains no script, stylesheet, image, font, or other remote resource.
A restrictive CSP forbids resource loading, forms, and base URL changes. Native
headings, a skip link, header/main/footer landmarks, definition lists, and UTF-8
metadata support accessible offline reading. The renderer copies public values
without recalculating decisions or reordering jobs. It adds no dependency.
`tests/fixtures/report.html` is the reviewed synthetic snapshot; security tests
cover hostile text/attributes, dangerous URLs, empty pages, and resource absence.
A manual headless Chrome check also opens the snapshot directly from disk.
