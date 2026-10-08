# Jobicy governance review

Reviewed on 2026-10-08; policy version `1.0.0` is encoded in
`borderless.connectors.policy.JOBICY_POLICY`. Authoritative source:
[Jobicy API / RSS documentation](https://jobicy.com/jobs-rss-feed), especially
Fair use, Cursor pagination, Batch status, and Frequently asked questions.

Jobicy permits integrations, custom summaries, and discovery experiences. Preserve
Jobicy attribution and the canonical Jobicy listing URL on every displayed listing.
The current report supports a plain attribution name, notice, source URL, and each
job's canonical URL; policy tests validate that these requirements fit that contract.

Start new automated synchronization passes no more than hourly (3600 seconds).
A few passes per day suffice. Follow cursor pages sequentially with unchanged
filters; tokens expire 24 hours after traversal starts. This interval governs
new passes, not each page. Keep public access separate from commercial ATS links.

Full raw payloads stay private. Public redistribution is restricted locally to
attributed summaries and minimal decision evidence, never full raw descriptions.
The source does not specify a raw retention duration or a removal SLA in this
reviewed page. A 30-day raw retention limit and purge on removal request are local
safeguards, not claims of a Jobicy requirement. Uncertain redistribution permission
uses the private default. Public demos continue to use synthetic/reusable data.

Hide explicitly closed listings from active results. Honor removal requests by
hiding listings and purging retained source payloads and public excerpts; retain
only non-content audit metadata where appropriate. Enforcement belongs to later
catalog and report publication tasks, not these data contracts.

The feed covers only seven days. Absence from two successful feed passes does not
prove closure. Jobicy's status endpoint distinguishes active, closed, and unknown;
unknown must not become confirmed closed. Reconcile this source-specific behavior
with C06 before implementing closure; the architecture's generic absence heuristic
is not safe for this rolling-window source.

Re-review and increment the policy version when permissions or requirements change.
No live feed is fetched by tests, and this review introduces no live connector.
