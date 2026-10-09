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
The opt-in live connector is documented below.

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

## Opt-in live fetching

`JobicyConnector.live(query, state_path=...)` explicitly creates the live adapter;
ordinary imports, fixtures and tests make no network requests. Supply a path in the
current worktree's cache, and reuse the same state file for every Jobicy query.
The standard-library transport pins the public HTTPS jobs endpoint, verifies TLS
certificates and hostname, disables environment proxies and redirects, uses a
project user agent, and requests uncompressed JSON. URLs cannot select another
host, port, scheme, fragment or resource. No API key or commercial access is used.

Each attempt has a configurable 10-second default socket/read timeout and a read
loop deadline. Responses are limited to 10 MB, with both Content-Length and streamed
bytes checked. Compressed and non-JSON responses are rejected, and responses close
on success/failure. Cancellation is checked before requests, between read chunks,
and during backoff; a blocked socket operation ends at its timeout rather than
being interrupted immediately.

At most three attempts retry timeouts, transport failures, and HTTP 408/429/500/502/
503/504. Exponential delay includes bounded jitter. Numeric or HTTP-date Retry-After
is honored; delays beyond 30 seconds return a deferred failure without a long sleep.
The durable gate records server deferral for all subsequent page/pass requests.
Other statuses, bad JSON/schema, oversized responses and cancellation do not retry.
Errors expose only typed codes and retry delay, never response bodies or credentials.

The gate uses Linux file locking, bounded reads, private permissions and a symlink
check. It reserves a new pass before its first network attempt (including failed
passes), and enforces the hourly source policy across connector instances and process
restarts. Sequential cursor pages do not consume another pass reservation. Keep the
file intact and use one ingestion runner per worktree; deleting or choosing another
state file loses the guard. Later catalog persistence can replace this local gate.
The connector validates checkpoint source, query and expiry before I/O, preserves
traversal expiry and rejects out-of-order pages and cursor cycles. Restarted instances
can resume a persisted checkpoint. Do not share a connector instance between threads.

Manual smoke test from the repository root (one requested job, no raw payload logged):

```bash
uv run --locked --all-packages --offline python -m scripts.jobicy_smoke --help
uv run --locked --all-packages --offline python -m scripts.jobicy_smoke --live
```

`--offline` controls dependency resolution; `--live` explicitly permits the feed
request. This check requires network access and is excluded from mandatory CI.
It stores only the polling reservation in the per-worktree cache and prints counts,
status and schema version. All automated transport tests use synthetic responses.
