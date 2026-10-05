# M1 deterministic preview verification

The W10 journey in `tests/test_preview_journey.py` invokes the actual CLI adapter
with `search --country BO --role data-engineer --as-of 2026-10-05T00:00:00+00:00`.
The supported injected clock is frozen at that same instant. Nothing replaces the
search adapter, application use case, canonical contracts, or renderers. Network
socket creation is blocked in this journey; there is no database setup.

The test saves JSON stdout as a UTF-8 file and invokes HTML/output mode with a
relative destination. It decodes JSON through `SearchReport.from_dict()` and parses
the HTML artifact using the standard library. It compares every visible field with
its corresponding canonical value, including nested trace/evidence/provenance,
source link destinations, disclaimer, pagination, versions, and job order. Missing
values and empty evidence retain their explicit presentation. Two independent
executions must yield identical JSON and HTML bytes, matching the reviewed W07/W08
synthetic golden artifacts. Generated files stay in pytest's temporary directory.

Run the focused journey and all M1 contract/security behavior checks from the
repository root, after locked installation:

```bash
UV_CACHE_DIR=.cache/uv uv run --locked --all-packages --group migration --offline pytest tests/test_preview_journey.py tests/test_cli.py tests/test_cli_search.py tests/test_html_renderer.py tests/test_json_renderer.py tests/test_report_builder.py tests/test_report_contract.py tests/test_synthetic_search.py tests/test_search_contract.py tests/test_domain_values.py
scripts/check-quality.sh all
```

M1 exit evidence:

- The target synthetic search works through the real CLI and application seams:
  `test_preview_journey.py` and installed-entry-point checks in `test_cli_search.py`.
- Dimensional verdicts, ordered trace, evidence, missing facts, source freshness,
  attribution, and policy/schema versions survive both artifacts: the full-field
  journey comparison plus immutable contract and builder tests.
- JSON and HTML render the same `SearchReport` deterministically: repeated CLI
  invocations, semantic comparison, and complete golden-byte comparison.
- Unsafe source content is escaped, URL destinations fail closed, and offline
  artifacts need no resources: `test_html_renderer.py`. CLI contracts cover valid,
  empty, uncertain, invalid, write-failure, symlink, and closed-pipe cases in
  `test_cli_search.py`, including actual subprocess exit codes.

Clean-worktree rehearsal:

```bash
git worktree add --detach .worktrees/w10-preview HEAD
cd .worktrees/w10-preview
git status --short
UV_CACHE_DIR=.cache/uv uv sync --locked --all-packages --all-groups
scripts/check-quality.sh all
git status --short
```

Use a fresh directory and its own `.venv`, `.cache/uv`, coverage file, and generated
output; do not copy environments or caches from another checkout. Installation may
access the approved package index. Tests then run offline without application
secrets, Docker, models, or feeds. The linked checkout is kept until verification
finishes; remove only this disposable checkout using `git worktree remove` after
checking its clean status. See [worktree isolation](worktree-isolation.md).

The installed command intentionally reads the real UTC clock; freezing the Python
entry point's explicitly supported clock makes the journey reproducible without
adding a test-only public CLI flag. W09 independently tests the installed console
script. This does not claim live ingestion or production eligibility: all preview
jobs and facts are synthetic, and unsupported conclusions remain `UNCERTAIN`.
