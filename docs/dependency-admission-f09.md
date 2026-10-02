# F09 migration dependency admission (2026-10-02)

Scope: the optional `migration` group, consumed by `migrations/env.py` and the
explicit migration check. Neither dependency is admitted to the application runtime.

- `alembic==1.20.0`: versioned, reversible PostgreSQL migrations. A custom stdlib
  migration runner would duplicate revision ordering, history tracking, and safety
  behavior. Maintained by the SQLAlchemy project, released 2026-09-11, MIT;
  [PyPI](https://pypi.org/project/alembic/1.20.0/),
  [source](https://github.com/sqlalchemy/alembic),
  [advisories](https://github.com/sqlalchemy/alembic/security/advisories).
- `psycopg[binary]==3.3.6`: PostgreSQL connection for Alembic on the supported
  Linux platform. The binary wheel avoids relying on an unpinned system `libpq`
  installation in CI; it adds compiled code and bundled libraries that require
  deliberate patch review. Maintained by the Psycopg team, released 2026-09-18,
  LGPL-3.0-only, compatible with this project's MIT source distribution when its
  separate license and notices are preserved;
  [PyPI](https://pypi.org/project/psycopg/3.3.6/),
  [binary wheel](https://pypi.org/project/psycopg-binary/3.3.6/),
  [source](https://github.com/psycopg/psycopg),
  [advisories](https://github.com/psycopg/psycopg/security/advisories).

Review: official PyPI releases and project advisory pages checked 2026-10-02; no
published advisory was identified for these selected releases. Use only the default
index with TLS and `first-index`; no remote installer, VCS dependency, or lifecycle
hook is added. The lockfile records wheel hashes. Before accepting, compare the
complete transitive graph and verify locked installation, offline quality checks,
and an empty→head→base→head cycle against disposable PostgreSQL. The binary wheel
and any transitive native code remain residual supply-chain risks; future upgrades
must repeat this review.

Verification: `uv lock --check --offline`, locked all-package/all-group sync,
offline format/lint/type/import/test/coverage checks, and the revision-asserted
`base → 0001 → base → 0001` PostgreSQL cycle passed on 2026-10-02. The disposable
container was removed afterward. `uv audit --locked` reported no known
vulnerabilities or adverse project statuses across the 21 third-party packages
in the locked graph on 2026-10-02; this is a point-in-time check, not a guarantee
against undisclosed issues.

Locked graph review: Alembic adds SQLAlchemy 2.1.2, Mako 1.4.3, and MarkupSafe
3.0.3; Psycopg adds the matching Psycopg Binary 3.3.6 wheel. Both reuse the
existing `typing-extensions` package. `tzdata` is locked for other platforms,
not installed on the verified Linux host. Mako and Psycopg Binary introduce
compiled wheel content; no application runtime package gains a dependency.
