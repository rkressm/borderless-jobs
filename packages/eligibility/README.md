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
global eligibility verdict. Listing restrictions are composed through `evaluate_geography`;
callers must not use the isolated inclusion primitive to adjudicate restrictions.
The M1 synthetic preview remains unchanged until the application integration task.

See [reference provenance](../../docs/geographic-reference.md),
[architecture](../../docs/architecture.md), and
[import rules](../../docs/import-boundaries.md).
Run `scripts/check-quality.sh all` from the repository root.

D03 exposes `GeographicRestriction`, `RestrictionKind`, `GeographicDecision`, and
`evaluate_geography`. Exclusions name countries or reviewed regions; an allowlist
is an exhaustive set of permitted locations, not examples. Known exclusions and
allowlist omissions fail; matching allowlists pass. Unsupported restriction
values block a permissive conclusion. Missing inclusion remains UNKNOWN. All
facts retain evidence and provenance, with deterministic ordering and deduplication.
Callers validate canonical evidence and extraction semantics before evaluation.

D04 marks `annotation_candidate` and returns UNKNOWN for direct contradictory
country claims, inclusion within an explicitly excluded scope, and incompatible
allowlists. A broad inclusion covering a narrower exclusion remains FAIL. Fact
ordering and duplicates do not affect the decision or serialized fact ordering.
Annotation candidates are data for later review integration, not an I/O side effect.

D05 exposes `EngagementFact`, `EngagementKind`, `EngagementDecision`, and
`evaluate_engagement`, with policy 1.0.0. Explicit worldwide contracting or
candidate-country contractor/EOR coverage passes. EOR coverage is an evidenced
fact for the job, not a provider registry or a presumption based on its brand.
Country lists for payroll/work authorization describe exhaustive mandatory
jurisdictions; restrictions to other reviewed countries fail. Matching the
candidate country alone does not establish a supported mechanism or personal
work authorization. Visa facts are relevant only when foreign work/relocation
is explicitly required. Missing coverage or an unreviewed scope remains UNKNOWN.

Opposed facts about the same mechanism, or supported remote engagement combined
with a mandatory foreign restriction, produce UNKNOWN with an annotation
candidate. Contractor and EOR mechanisms are alternatives: prohibiting one does
not prohibit the other. Inputs describe unconditional facts for this job/version;
conditional options must be resolved by extraction before invoking the policy.
Each decision retains facts, policy/reference versions, rule ID, explanation,
and an informational, non-legal-advice disclaimer. No provider, law, payroll
service or personal immigration status is consulted or inferred.

D06–D08 will implement timezone, global composition and complete rule traces.
These dimensional seams do not change the synthetic CLI preview yet.
