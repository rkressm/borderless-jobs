# Connectors ownership

`borderless.connectors` owns source policies and the source-neutral ingestion seam.
It depends only on shared domain values and the standard library. It does not own
catalog writes, canonical text normalization, extracted facts, or verdicts.

`Connector.fetch(checkpoint=None)` returns one `ConnectorBatch` or raises a
`ConnectorError` with a serializable `ConnectorFailure`. Transport clients and
exceptions do not cross this boundary. Cancellation, invalid responses, timeouts,
rate limits, and invalid cursors have distinct failure codes. Only transient
failures can provide a retry delay; retry behavior belongs to the future transport.

Each successful batch carries its versioned `SourcePolicy`, `FetchMetadata`, and
immutable `RawEnvelope` records. Raw UTF-8 JSON strings preserve exact source bytes
rather than exposing mutable dictionaries; they are private and untrusted. Their
`to_dict()` serialization is for private catalog/fixture storage, never public
reports or logs. Payloads and opaque cursor tokens are excluded from `repr`.
Metadata URLs must not contain credentials; adapters must also omit secrets in
query parameters and headers. URL syntax validation does not authorize network
access: destination/TLS checks belong to the future live transport.

Contract limits are 1 MB per raw job, 10 MB per response/page, 1000 jobs per page,
64 JSON nesting levels, and 2048 characters per identifier/cursor. Limits count
UTF-8 bytes. Source adapters can apply stricter limits (Jobicy allows 200 jobs per
page). Response bytes describe the full uncompressed response and must cover all
job payload bytes. Raw payloads are JSON objects with finite numbers.

`None` begins a new traversal. `next_checkpoint=None` ends it, including an empty
terminal page. A checkpoint binds the opaque token to a source and an adapter-defined
stable query key (filters and page size, excluding the cursor). Pages must preserve
that key and traversal expiry, use valid unexpired checkpoints, and advance tokens.
There is no redundant `has_more` flag. Duplicate source identities within a page
are rejected; repeats across pages/passes are the catalog's idempotency concern.
Adapters must reject mismatched/expired input before I/O and track older cursor
cycles across pages; the batch can detect only an immediate repeated token.

Datetime inputs require explicit timezones; validation has no hidden clock reads.
All values support strict `to_dict()` / `from_dict()` round trips. Connector schema
version `1.0.0` is independent of the source governance version. See
[Jobicy governance](../../docs/jobicy-governance.md) for the first reviewed policy.
The fixture connector and live transport are separate future tasks (I03 and I06).
