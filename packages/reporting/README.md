# Canonical reports

Own immutable versioned SearchReport and job summaries, report building, and rendering. Consume search and domain values; preserve ordering, verdicts, evidence, freshness, unknowns, traces, and attribution. Renderers never decide eligibility.

Public surface: `ReportBuilder`, `SearchReport`, `JobResult`, `RuleTrace`, `DataFreshness`, and `SourceAttribution`. Import supported values from `borderless.reporting`; implementation submodules are private. Public contracts use standard-library and Borderless values only.

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
JSON formatting and HTML rendering are separate W07/W08 tasks.

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
a changed snapshot changes the identity. This internal identity encoding is not a
public renderer (W07 remains pending). A frozen-clock journey with
`SyntheticSearchAdapter` is covered by `tests/test_report_builder.py`, including
missing evidence and deterministic round trips. No new dependency is required.
