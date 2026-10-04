# Search application contracts

Own SearchSpecification, filters, explicit pagination, result ordering, and query interfaces. Hide storage and ranking implementation; expose no SQL, transport, or framework types.

Public surface: `SearchSpecification` and `ResultOrderKey`. Import supported values from `borderless.search`; implementation submodules are private. Public contracts use standard-library and Borderless values only.

See [architecture](../../docs/architecture.md) and [import rules](../../docs/import-boundaries.md). Run `scripts/check-quality.sh all` from the repository root.

`SearchSpecification` requires role, country, timezone-aware `as_of`, offset, and limit (1–100). Role text normalizes to an ASCII hyphenated phrase. Empty source/verdict filters mean unrestricted; duplicate or invalid filters fail. Filter tuples are sorted canonically. Results order by descending publication instant, then ascending unique job ID. Serialization uses the strict shared value contract.
