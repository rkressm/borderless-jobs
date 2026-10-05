# Search application contracts

Own SearchSpecification, filters, explicit pagination, result ordering, and query interfaces. Hide storage and ranking implementation; expose no SQL, transport, or framework types.

Public surface: `SearchSpecification`, `ResultOrderKey`, `JobSearch`,
`SearchResultPage`, `SearchJob`, `SearchFact`, `SearchRuleTrace`, `SearchSource`, and
`SyntheticSearchAdapter`. Import supported values from `borderless.search`; implementation submodules are private. Public contracts use standard-library and Borderless values only.

See [architecture](../../docs/architecture.md) and [import rules](../../docs/import-boundaries.md). Run `scripts/check-quality.sh all` from the repository root.

`SearchSpecification` requires role, country, timezone-aware `as_of`, offset, and limit (1–100). Role text normalizes to an ASCII hyphenated phrase. Empty source/verdict filters mean unrestricted; duplicate or invalid filters fail. Filter tuples are sorted canonically. Results order by descending publication instant, then ascending unique job ID. Serialization uses the strict shared value contract.

`JobSearch.search(specification)` returns an immutable `SearchResultPage` with
ordered `SearchJob` snapshots, total before pagination, and `SearchSource` metadata.
Jobs carry typed `SearchFact` values, extraction provenance, and existing assessment
snapshots with `SearchRuleTrace` entries. The result validates pagination, unique
identities, source metadata, publication cutoffs, and assessment time.

`SyntheticSearchAdapter` implements this same interface entirely in memory. Four
invented postings use `example.org` URLs and synthetic provenance. Exact normalized
role and candidate-country coverage filters select fixtures, not geographic eligibility.
Source/verdict filters run before pagination. Publication time sorts descending and
job ID breaks ties. Source observation is fixed at `2026-10-01T00:00:00Z`; earlier
queries return no observed data. Existing fixture assessments are replayed at the
explicit query instant; they always remain `UNCERTAIN`, with missing facts visible.
These hand-built assessments are demonstration data, not an eligibility engine.
One fixture has no supporting evidence. No database, network, hidden clock, or model
is involved. Verify with `tests/test_synthetic_search.py` and the quality loop.
