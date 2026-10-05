# Command adapter

Parse arguments, invoke application interfaces, and translate results/errors into output and exit codes. No ranking, eligibility, source parsing, SQL, or provider logic.

Public surface: `build_parser` and `main`. Import supported values from `borderless.cli`; implementation submodules are private. Public contracts use standard-library and Borderless values only.

See [architecture](../../docs/architecture.md) and [import rules](../../docs/import-boundaries.md). Run `scripts/check-quality.sh all` from the repository root.

The W09 command uses `SyntheticSearchAdapter` through `ReportBuilder` and the public
renderers. It reads no database, feed, or model; its invented jobs and hand-built
`UNCERTAIN` assessments are a preview, not live eligibility results. Only the CLI
reads the clock, once, and passes that instant into the application use case.

Run from the repository root after locked installation:

```bash
uv run --locked --offline --package borderless-cli borderless search --help
uv run --locked --offline --package borderless-cli borderless search --country BO --role data-engineer --format json
uv run --locked --offline --package borderless-cli borderless search --country BO --role data-engineer --format html --output ./report
```

`--country` and `--role` are required and use the shared contract's normalization
and validation. `--format` defaults to `json`, emitted as the canonical JSON text
on stdout with no status messages. HTML requires `--output DIRECTORY`; JSON rejects
`--output` (use shell redirection instead). HTML success emits no stdout/stderr.
The artifact is `DIRECTORY/report.html`, UTF-8, directly openable offline.
Relative destinations are relative to the caller's current directory. Parent
folders are created as needed. Publication is atomic on the supported Linux
filesystem: a same-directory temporary file is fully written and flushed before
exclusive hard-link publication. Existing files and final-name symlinks are never
replaced; temporary files are removed on success and ordinary failures. A directory
may remain after an error; process crashes may leave a private `.report-*` temporary
file. This does not claim power-loss durability.

`--offset` defaults to `0`; `--limit` defaults to `10` and accepts `1..100`.
`--source` and `--verdict YES|NO|UNCERTAIN` are repeatable exact filters; duplicate
filters fail validation. Totals count matches before pagination. `--as-of` accepts
an ISO-8601 datetime with a timezone, including `Z`, no later than the passed clock;
it defaults to the current UTC instant. Historical searches retain their requested
assessment instant while report creation uses the current clock. Source observations
not yet available at `--as-of` produce an empty page.

Exit codes:

- `0`: successful report, including zero jobs or any `UNCERTAIN` results; help also
  exits successfully and prints human-readable usage on stdout.
- `2`: invalid/missing command arguments, filters, timestamp, or mode/output pairing;
  error code `invalid_arguments`.
- `3`: output failure, including inaccessible destinations, existing artifacts,
  filesystem errors, or a closed stdout pipe; error code `output_error`.
- `4`: report construction/rendering contract failure; error code `report_error`.

Errors are one JSON line on stderr, with no diagnostic text or traceback:

```json
{"error": {"code": "output_error", "message": "Unable to write report output."}}
```

Messages do not echo untrusted arguments, paths, or private exception details.
Failures before output emit no stdout; a failed stdout write can leave a partial
JSON stream, which callers must discard on a nonzero exit. Error reporting assumes
stderr remains writable. `main(argv, clock=...)` supports an explicitly injected
aware clock for offline tests; the installed entry point uses the real UTC clock.
`python -m borderless.cli` provides the same command and exit codes.

Verification: `scripts/check-quality.sh all` includes offline real-seam tests and
installed-entry-point subprocess checks in `tests/test_cli_search.py`. Workspace
imports are declared and locked; see the [W09 dependency admission](../../docs/dependency-admission-w09.md).
