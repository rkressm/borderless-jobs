# M1 contract workspace dependencies

Reviewed and accepted on 2026-10-04.

- **Packages, constraints, consuming code:** existing workspace packages
  `borderless-domain==0.1.0` (W03 search and W04 reporting) and
  `borderless-search==0.1.0` (W04 reporting), resolved with explicit
  `workspace = true` sources and committed `uv.lock`.
- **Purpose:** share immutable value invariants and the search specification across
  the accepted inward module boundaries. Package manifests must declare imports so
  installing reporting also installs its local application contracts.
- **Alternative:** copying the contracts into consumers would create competing
  ownership and validation. Standard-library dataclasses implement all values;
  no external validation/serialization library is needed.
- **Maintenance and releases:** maintained in this repository at version `0.1.0`;
  source and consuming code reviewed together, not fetched from a registry.
- **License:** repository [MIT license](../LICENSE), compatible with the project.
- **Provenance/security:** local workspace source paths only; existing locked
  `uv_build==0.12.22` backend unchanged. No downloaded tool, new build hook,
  credential, external package, or native component is introduced.
- **Transitive impact:** reporting now depends on search and domain; search depends
  on domain. Domain has no dependencies. Resolution remains 29 packages; all
  registry artifacts and versions are unchanged in the lockfile.
- **Verification:** offline lock resolution, locked all-package/all-group sync,
  full format/lint/strict typing/import/CI/test/coverage checks. Round-trip tests
  exercise actual imports through the public package surfaces.
- **Residual risk:** these are first-version contracts; future schema evolution
  must be explicit and retain historical decoding or add a migration path.
