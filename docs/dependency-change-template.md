# Dependency change record

Copy this section into the change description once for each proposed direct dependency
or version update. Use concrete links and observations; `unknown` is not approval.

- **Package, version constraint, group, consuming task and code:**
- **Purpose and required behavior:**
- **Standard-library or existing-dependency alternative:**
- **Maintainer and release history:** canonical repository, publisher, latest relevant
  releases, review date, and evidence links.
- **License:** declared SPDX expression, license-file source, and compatibility with
  this MIT project.
- **Provenance and security:** registry/source identity, artifact or immutable revision,
  advisory check for the package and installer, build/install hooks, and evidence links.
- **Transitive impact:** before/after `uv tree --locked --all-groups`, new packages and
  native/build requirements, and whether runtime size changes.
- **Decision:** accept or reject, reviewer, date, and unresolved risk.
- **Verification if accepted:** manifest and lockfile reviewed together; commands and
  affected checks run with results.
