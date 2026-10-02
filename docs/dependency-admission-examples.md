# Dependency admission examples

These records exercise the [change template](dependency-change-template.md) against
the workspace on 2026-10-02. The accepted record updates an existing build requirement
to match the installed build tool; it adds no runtime package. The rejected record is
a proposal only.

## Accepted: `uv_build` for existing pure-Python packages

- **Package, version constraint, group, consuming task and code:**
  `uv_build==0.12.22` in the eight workspace members' `[build-system]` sections;
  F04 package builds after the local `uv` upgrade.
- **Purpose and required behavior:** produce installable wheels for the CLI and module
  namespaces.
- **Standard-library or existing-dependency alternative:** the standard library has
  no PEP 517 build backend for this workspace; `uv` already supplies the compatible
  backend for its own builds.
- **Maintainer and release history:** Astral maintains the
  [canonical repository](https://github.com/astral-sh/uv); the
  [0.12.22 release](https://github.com/astral-sh/uv/releases/tag/0.12.22)
  records its 2026-10-01 release. Reviewed 2026-10-02.
- **License:** upstream `uv_build` declares `MIT OR Apache-2.0` and ships both license
  files in its [package metadata](https://github.com/astral-sh/uv/blob/main/crates/uv-build/pyproject.toml);
  the MIT option matches this project's license.
- **Provenance and security:** the
  [documented bundled backend](https://docs.astral.sh/uv/concepts/build-backend/)
  is used by matching `uv` builds; the source is Astral's repository. The installed
  `uv` is now 0.12.22, beyond the patched versions in
  [GHSA-4gg8-gxpx-9rph](https://github.com/astral-sh/uv/security/advisories/GHSA-4gg8-gxpx-9rph)
  and [GHSA-2cv4-cqwr-gwf7](https://github.com/astral-sh/uv/security/advisories/GHSA-2cv4-cqwr-gwf7).
  This comparison does not replace advisory review for a future release. The exact
  backend version avoids silently selecting a later release outside `uv.lock`.
- **Transitive impact:** `uv.lock` lists only the eight local workspace members. No
  third-party runtime package enters that graph; another build frontend may install
  `uv_build` and its isolated build requirements separately. The before/after
  `uv tree --locked --all-groups` remains the eight local members.
- **Decision:** accept the exact 0.12.22 build requirement; project review,
  2026-10-02. Remaining risk: another build frontend may resolve isolated build
  requirements, so release builds must inspect their artifacts.
- **Verification if accepted:** `uv lock --check`,
  `uv tree --locked --all-groups`, `uv sync --locked --all-packages`, an offline
  `uv build --all-packages`, and the existing CLI test all pass with an
  isolated worktree cache.

## Rejected: HTTP client for the current CLI placeholder

- **Package, version constraint, group, consuming task and code:** proposed third-party
  HTTP client in `borderless-cli` runtime dependencies; no version selected and no
  consuming code in F04.
- **Purpose and required behavior:** hypothetical future feed fetching, outside the
  current CLI's `--help` behavior.
- **Standard-library or existing-dependency alternative:** no HTTP behavior is needed
  now; assess `urllib.request` and connector needs when ingestion begins.
- **Maintainer and release history:** no package or publisher selected, so no canonical
  source or release evidence can be reviewed.
- **License:** unknown without a concrete package and artifact.
- **Provenance and security:** registry identity, artifact, package advisories, and
  install behavior are unknown. The installed frontend was checked against its
  published advisories, which does not establish the proposed client's safety.
- **Transitive impact:** unknown; adding an unused client would expand the runtime graph.
- **Decision:** reject for F04; project review, 2026-10-02. Reopen against a
  consuming ingestion task with a concrete package and completed evidence.
- **Verification if accepted:** not applicable; no manifest or lockfile change.
