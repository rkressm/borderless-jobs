# Pure eligibility decisions

Evaluate validated facts with immutable domain values. Import domain only; never
extract facts or perform I/O.

The geographic inclusion surface exposes `GEOGRAPHIC_REFERENCE`, `CountryIdentity`,
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

## Timezone and complete assessments (D06–D08)

`WorkingWindow` describes a recurring local half-open window with minute precision;
an end before the start crosses midnight. Equal endpoints are rejected as ambiguous.
`TimezoneFact` carries explicit minimum real minutes, mandatory/preference semantics,
evidence and provenance. Multiple mandatory facts must all be satisfied. Candidate
availability is supplied explicitly; no default workday is invented.

`evaluate_timezone` receives an aware `as_of` and caller-loaded IANA timezone
objects. It anchors each required window on the required zone's local date at
`as_of`, counts actual UTC minutes, and compares candidate daily availability.
Skipped minutes do not exist; repeated minutes count twice. Missing zones/windows
or vague preferences produce unknown; an established impossible mandatory overlap
fails even alongside unresolved facts. Absence is not applicable. The caller owns
timezone loading and records its tzdata version for replay; eligibility does no I/O.

`compose_verdict` checks all three dimensions: any fail gives NO, otherwise any
unknown gives UNCERTAIN, otherwise pass/not-applicable gives YES.
`evaluate_eligibility` accepts immutable `EligibilityInputs` and returns
`EligibilityAssessment` with ordered geography, engagement, timezone and global
`EligibilityRuleTrace` entries. Each entry records the selected decision rule,
policy/reference versions, complete typed inputs, outcome, explanation, missing or
contradictory facts, and annotation flag. Facts are sorted and deduplicated.
Serialization uses the domain value contract; no renderer or template is consulted.
Application wiring of these assessments replaces synthetic decisions in a later
milestone; the walking-skeleton CLI still uses its frozen synthetic adapter.

## Protected cases and quality gates (D09–D10)

The [synthetic protected corpus](../../evals/README.md) contains 12 independently
reviewed policy annotations. The offline suite checks exact dimensional/global
outcomes and annotation flags, evidence spans, strict schema, duplicate cases,
and byte-stable repeated assessments. Expected labels are separate from unit
fixtures and changes are visible in the corpus/review diff.

The coverage command enforces at least 90% eligibility branch coverage, separately
from aggregate backend coverage. Source checks reject forbidden imports, direct
I/O/dynamic execution and hidden clock calls. A runtime test preloads zones and
then disables file access, sockets and timezone loading during assessment.
Representative source mutations remove exclusion precedence or turn FAIL/UNKNOWN
composition into YES; each must fail the protected eval. These checks execute in
the existing offline backend CI through `scripts/check-quality.sh all`.
