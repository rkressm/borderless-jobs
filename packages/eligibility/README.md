# Pure eligibility decisions

Evaluate validated facts with immutable domain values. Import domain only; never
extract facts or perform I/O.

The public surface exposes `GEOGRAPHIC_REFERENCE`, `CountryIdentity`,
`GeographicRegion`, `GeographicReference`, `GeographicInclusion`,
`InclusionDecision`, and `evaluate_geographic_inclusion`. Import these from
`borderless.eligibility`; implementation submodules are private.

D02 evaluates one explicit hiring inclusion fact for a reviewed candidate country.
The fact carries an exact evidence quote and extraction provenance. The caller
must verify evidence against canonical text and classify inclusion semantics
before invoking this seam. Alias resolution matches the whole value, tolerating
casing and whitespace only. Decisions carry stable rule IDs, policy/reference
versions, candidate, original fact and explanation. Unsupported input stays UNKNOWN.

This is the positive inclusion primitive, not the complete geography engine or a
global eligibility verdict. Exclusion precedence and contradictions remain D03/D04;
callers must not use this primitive to adjudicate a listing containing restrictions.
The M1 synthetic preview remains unchanged until the application integration task.

See [reference provenance](../../docs/geographic-reference.md),
[architecture](../../docs/architecture.md), and
[import rules](../../docs/import-boundaries.md).
Run `scripts/check-quality.sh all` from the repository root.
