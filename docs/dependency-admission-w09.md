# W09 CLI workspace dependencies

Reviewed and accepted on 2026-10-05.

- **Packages and consumer:** `borderless-domain`, `borderless-search`, and
  `borderless-reporting`, existing version `0.1.0` workspace packages imported by
  `apps/cli/src/borderless/cli`. Explicit `workspace = true` sources keep resolution
  local; manifests and lockfile change together.
- **Purpose:** invoke existing validated search/report interfaces and renderers.
  Copying contracts or business behavior into CLI would violate module ownership.
  Parsing, JSON errors, clocks, and file publication use the standard library;
  no third-party CLI framework is needed.
- **Maintenance, release, license, provenance:** maintained and reviewed in this
  repository, same current `0.1.0` sources and [MIT license](../LICENSE) as the
  [M1 contract admission](dependency-admission-m1-contracts.md). No registry lookup,
  downloaded installer, new build hook, or native component is introduced.
  The pinned `uv_build==0.12.22` build backend is unchanged.
- **Transitive impact:** CLI now declares imports of reporting, search, and domain.
  Reporting already depends on search/domain and search on domain. There are no
  new resolved packages, registry versions, hashes, or third-party dependencies.
- **Verification:** offline lock resolution and lock check, locked workspace sync
  and dependency tree review, license/secret/vulnerability gates, strict quality
  checks and offline CLI behavior tests, then remote CI verification.
- **Decision and residual risk:** accepted for W09; the adapter uses explicitly
  synthetic jobs and cannot claim production eligibility or live-feed coverage.
