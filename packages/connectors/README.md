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
version `1.1.0` is independent of the source governance version. See
[Jobicy governance](../../docs/jobicy-governance.md) for the first reviewed policy.
`FixtureConnector.load(path)` reads a UTF-8 JSON recording with explicit
`FixtureProvenance` (synthetic, licensed, or transformed; origin, license, notes)
and an ordered `batches` array. Non-synthetic recordings require a reviewed reuse
license; transformation alone does not establish permission. Recordings are bounded
to 20 MB and 100 pages, must contain one complete checkpoint chain, and reject
cycles, disconnected pages, query changes, and policy changes. Fetches are stateless:
the same checkpoint replays the same page; a new instance can resume it. Validation
uses recorded fetch times, not today's clock, so fixtures remain reproducible.
Malformed/unreadable files yield `INVALID_RESPONSE`; unknown or changed checkpoints
yield `INVALID_CHECKPOINT`. Cross-page repeated jobs remain valid for catalog replay.

`tests/fixtures/connectors` contains only synthetic MIT-licensed recordings.
The live transport remains a separate future task (I06).

## Jobicy mapping

`JobicyQuery` validates page size, taxonomy slug syntax, and bounded plain-text
keywords, and derives a stable query key. `map_jobicy_response(body, metadata,
query, checkpoint)` maps an already recorded UTF-8 public Jobs API response without
I/O. Objects in `jobs` retain their exact JSON substrings, including unknown fields;
response-level metadata is retained privately in `FetchMetadata.source_metadata_json`.
Malformed JSON, duplicate keys, changed required field types, inconsistent counts,
unsupported API majors, bad pagination, and noncanonical listing URLs fail closed.
Optional fields can be absent; unknown additive metadata is preserved. No verdicts
or normalized text are emitted by the mapper.

`RawEnvelope.content_hash` is a SHA-256 fingerprint of sorted compact UTF-8 JSON,
independent of object key order and insignificant JSON whitespace. It covers unknown
source fields too; catalog identity/versioning decisions remain in the catalog.

The connector schema is now `1.1.0` because fetch metadata gained a private source
metadata field. Existing synthetic recordings were upgraded; the strict contract
rejects unsupported schemas rather than interpreting old serialized data silently.
Mapper fixtures in `tests/fixtures/jobicy` are invented MIT-licensed data matching
the [official API specification](https://jobicy.com/api/openapi.json), reviewed on
2026-10-09. Tests prove the mapper and fixture adapter exchange the same batch types,
and the mapper output passes the I04 normalization seam.
