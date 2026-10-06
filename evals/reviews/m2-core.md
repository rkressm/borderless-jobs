# Independent review of the M2 protected corpus

Review date: 2026-10-06. Reviewer: `/root/review_m2_cases`.
This was an independent AI agent review, not a human review. The reviewer did not
implement the eligibility rules and derived the expected labels from
`docs/architecture.md` sections 7.1–7.5 and accepted ADR-0002, without using
implementation outputs as an oracle.

Reviewed corpus: `evals/cases/m2-core.jsonl`, case IDs `m2-01` through `m2-12`.
All twelve expected dimensional outcomes, global verdicts, and annotation flags
were accepted. No label changes were made. The m2-08 rationale was clarified
to refer to a candidate based in BO rather than implying an evidenced compatible
BO engagement mechanism.

## Evidence and label checks

Every evidence quote was checked against its exact half-open character slice in
the immutable canonical text. All slices matched, with valid bounds, case-specific
job-version identities, normalization version 1.0.0, and synthetic source URLs.
The synthetic fixtures contain no source claims about an actual employer.

- `m2-01`: explicit Bolivia and worldwide contractor evidence support YES.
- `m2-02`: reviewed LATAM membership covers Bolivia; explicit BO EOR evidence
  establishes the mechanism, supporting YES.
- `m2-03`: worldwide geographic permission plus worldwide contractor evidence
  supports YES.
- `m2-04`: the specific Bolivia exclusion overrides broad worldwide inclusion,
  supporting NO without a contradiction annotation.
- `m2-05`: the explicitly exhaustive US/CA allowlist omits Bolivia, supporting NO
  despite a broader worldwide statement.
- `m2-06`: remote marketing alone cannot authorize a country, so geography is
  UNKNOWN and the global verdict UNCERTAIN despite contractor permission.
- `m2-07`: Bolivia geography passes, but absent mechanism evidence leaves
  engagement UNKNOWN and the verdict UNCERTAIN.
- `m2-08`: mandatory US payroll fails engagement for the BO candidate; geographic
  inclusion does not establish a compatible mechanism. The verdict is NO, with
  no inference about citizenship or personal work authorization.
- `m2-09`: EOR evidence scoped to US does not establish BO coverage, leaving
  engagement UNKNOWN and the verdict UNCERTAIN.
- `m2-10`: on 2026-03-08, New York 09:00–10:00 and La Paz 09:00–10:00 both map
  to 13:00–14:00 UTC, so the mandatory 60-minute overlap passes and yields YES.
- `m2-11`: on 2026-03-07, New York 09:00–10:00 maps to 14:00–15:00 UTC, while
  La Paz availability maps to 13:00–14:00 UTC. Half-open windows have zero
  overlap, so the timezone fails and the verdict is NO.
- `m2-12`: explicit Bolivia inclusion and exclusion at equal scope are
  irreconcilable, yielding UNKNOWN geography, UNCERTAIN globally, and an
  annotation candidate.

For cases without timezone facts, NOT_APPLICABLE is non-blocking as specified.
The global labels independently follow: any FAIL yields NO; otherwise a required
UNKNOWN yields UNCERTAIN; otherwise PASS/NOT_APPLICABLE yields YES.

## DST verification and limits

DST calculations were checked directly with Python standard-library `zoneinfo`
for America/New_York and America/La_Paz, independently of eligibility functions.
The New York spring transition is 2026-03-08; its 09:00 offset is UTC−04:00,
versus UTC−05:00 on the preceding date. La Paz remains UTC−04:00 on both dates.

The corpus records `system-IANA`, not a pinned tzdb release or content digest.
The DST labels therefore rely on the host IANA data retaining these rules; missing
zones or later timezone-data revisions can affect portability. These cases protect
policy over typed facts and synthetic evidence, not real-world extraction accuracy,
ongoing employer coverage, legal advice, or future timezone-law changes.
