# Shared immutable values and invariants

Country identities, canonical-text evidence, extraction provenance, decision vocabularies, and version identifiers. No search or report schema, policy evaluation, I/O, hidden clock, or framework types.

Public surface: `CountryCode`, `Evidence`, `FactProvenance`, `DimensionalDecision`, `GlobalVerdict`, `PolicyVersion`, `SchemaVersion`, and the shared `Value` serialization/validation base with `require_text` and `require_public_url`. Import supported values from `borderless.domain`; implementation submodules are private. Public contracts use standard-library and Borderless values only.

See [architecture](../../docs/architecture.md) and [import rules](../../docs/import-boundaries.md). Run `scripts/check-quality.sh all` from the repository root.

Values are frozen dataclasses, and sequences are tuples. `to_dict()` emits JSON-compatible data; `from_dict()` rejects extra/missing fields and incorrect types. Versions use canonical major.minor.patch syntax. Country codes normalize to ASCII alpha-2; actual ISO membership is deferred to D01. Evidence spans are half-open Unicode character offsets, limited to 2000 characters, and `verify()` checks the exact canonical text. Fact provenance records extraction method, provider, versions, model revision, and warnings; it emits no verdict.
