# Supply-chain and secret gates

The security workflow uses only repository read permission. Pull requests run the
official dependency-review action (all dependency scopes; fail at low severity).
Every pull request and main-branch push also runs the tracked-file secret scanner,
locks and installs the workspace, audits all locked dependency groups against OSV,
and writes a complete registry-package license inventory. The inventory is uploaded
as a short-lived CI artifact. Feed, model, and application credentials are not used.

Local checks after `uv sync --locked --all-packages --all-groups`:

```bash
python3 -m scripts.check_secrets
UV_CACHE_DIR=.cache/uv python3 -m scripts.check_vulnerabilities
uv run --locked --all-packages --group migration --offline python -m scripts.license_inventory
scripts/check-quality.sh all
```

The quality loop remains offline; OSV auditing requires network access. The secret
scanner checks tracked text files for common key and credential shapes, omits the
matched value from diagnostics, and fails on oversized tracked files rather than
silently skipping them. It cannot prove that arbitrary credentials are absent.
The license gate fails closed on unknown or unapproved licenses. Exact-version
overrides for Windows-only `colorama` and `tzdata` are reviewed from their upstream
license records and must be revisited if the lockfile changes.

Dependabot proposes weekly `uv` and GitHub Actions updates with no auto-merge
configuration. Review each PR's full lockfile, action pins, licenses, and test results;
the `uv` CI wheel hash and PostgreSQL digest require separate manual reviews.
Synthetic in-memory tests exercise secret, vulnerability, and license failures
without committing a usable credential or vulnerable runtime dependency.
For F11 verification, a temporary ignored lock-only fixture for `jinja2==2.10`
was audited without installation: OSV reported 12 known vulnerabilities and the
audit exited nonzero. The fixture and its lockfile were then removed.
