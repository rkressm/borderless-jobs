# Dependency admission policy

Status: active

Apply this policy to every new or updated direct runtime, development, build, AI, or
observability dependency. The [change template](dependency-change-template.md) is the
review record; complete one copy per dependency in the change description before
editing a manifest. The [worked decisions](dependency-admission-examples.md) show the
acceptance bar.

1. Name the task and the exact code or build step that consumes the package. Prefer
   the standard library or an existing dependency when either meets the need.
2. Verify the publisher, canonical source repository, maintenance and release history,
   license, and known security advisories from primary sources. Record links and the
   review date. Check the installed package manager for applicable advisories before
   installing third-party artifacts. Treat a missing or ambiguous answer as a reason
   to defer admission.
3. Inspect the proposed dependency group and the complete transitive diff, including
   build requirements and native code. Keep optional tooling out of runtime groups.
4. Use the approved package index and `first-index` resolution with TLS validation.
   Review direct URL or VCS sources separately; pin immutable revisions and verify
   archive hashes. Execute no remote installer or package hook without review.
5. Update the manifest and `uv.lock` in one change. Run `uv lock --check`,
   `uv tree --locked --all-groups`, `uv sync --locked --all-packages`, and the affected
   quality checks. Record unexpected additions and the admission decision. Automated
   update proposals follow the same review and never merge automatically.

The runtime dependency list must correspond to imports or entry points used by current
code. A future task is not enough to justify installing its libraries now. Build
requirements such as `uv_build` are reviewed separately from the `uv.lock` runtime
graph because the build frontend may resolve them in an isolated environment. Pin a
reviewed build backend to an exact version until build inputs have their own lock or
verified artifact digest.
