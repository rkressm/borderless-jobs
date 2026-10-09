# Borderless Jobs

Borderless Jobs is a planned local-first product that turns remote job listings into evidence-backed answers to a concrete question:

> Can I actually work here from Bolivia?

Instead of trusting a generic `remote` label, the system evaluates geographic restrictions, engagement mechanisms, and timezone requirements. It returns `YES`, `NO`, or `UNCERTAIN` together with the source evidence and exact rule trace.

## Current status

The reproducible Python foundation is in place. Product behavior remains intentionally
absent until the headless walking-skeleton milestone.

## Development setup

The exact fresh-checkout procedure, prerequisites, timings, and failure paths
are in the [clean setup guide](docs/clean-setup.md). The
[concurrent worktree check](docs/worktree-isolation.md) shows how to verify
isolated quality loops and disposable databases.

Install every workspace member from the reviewed lockfile:

```bash
uv sync --locked --all-packages
```

Check the CLI and run the fast offline quality loop:

```bash
uv run --frozen --package borderless-cli borderless --help
scripts/check-quality.sh all
```

`scripts/check-quality.sh` also accepts `format`, `lint`, `type`, `imports`, `test`,
and `coverage` for focused checks. The [import-boundary rules](docs/import-boundaries.md)
guard the pure core and adapter direction. The loop uses locked development dependencies and runs
offline after the initial sync. The workspace has no third-party runtime dependency;
the [F05 admission record](docs/dependency-admission-f05.md) documents the development
tools. See the repository supply-chain rule before changing a manifest, lockfile,
installer, build input, or CI action.

`python scripts/worktree_env.py --print` shows the deterministic, shell-safe local
resource names for this checkout. `python scripts/worktree_env.py` creates an ignored
Compose environment file and namespaced cache/artifact directories. No absolute
checkout path is written into that file.

For local PostgreSQL, run `bash scripts/db.sh dev-up` and later
`bash scripts/db.sh dev-down`. The disposable database uses
`bash scripts/db.sh test-up` and `bash scripts/db.sh test-down`; stopping or removing
it does not delete the development volume. Both services bind only to localhost,
with distinct derived ports and randomly generated, ignored credentials in a
mode-`0600` worktree file. Read the port and database name with
`python scripts/worktree_env.py --print`; do not publish the credential file.
The PostgreSQL image is an official Docker Hub image pinned to an immutable digest;
review and update that digest deliberately when patching the development database.

The optional `migration` dependency group owns Alembic and Psycopg. Run
`uv sync --locked --all-packages --all-groups` before
`bash scripts/check-migrations.sh` to test the empty baseline migration against
a disposable database. For a running development database, use
`uv run --locked --all-packages --group migration python -m scripts.migrate dev upgrade head`.
The [F09 admission record](docs/dependency-admission-f09.md) documents the added
packages. No catalog tables exist yet.

The backend CI runs the same offline quality loop and disposable migration cycle
on Ubuntu 24.04. The workflow grants only repository read access, uses official
actions pinned by full SHA, and installs a hash-checked `uv` wheel before the
locked workspace sync. `scripts/check-quality.sh ci` verifies the action pins and
minimum-rights markers locally. The [security gates](docs/security-gates.md) add
dependency review, OSV auditing, tracked-file secret detection, a reviewed license
inventory, and weekly review-only Dependabot PRs.

## Planning documents

- [Architecture](docs/architecture.md) — product scope, module interfaces, runtime and data design, AI extraction, eligibility semantics, testing, security, CI/CD, and evolution path.
- [Delivery roadmap](docs/roadmap.md) — dependency-driven milestones and release gates.
- [Step-by-step development plan](docs/development-plan.md) — atomic tasks with
  dependencies, estimates, observable results, and verification criteria.
- [Runtime support policy](docs/runtime-policy.md) — supported Python and verified
  development platform.
- [Dependency policy](docs/dependency-policy.md) — admission and review of new packages.
- [Architecture decision records](docs/adr/) — concise records of the decisions that should not be rediscovered during implementation.

## Project governance

- [Contribution guide](CONTRIBUTING.md) — atomic changes, worktree discipline, and
  verification expectations.
- [MIT License](LICENSE.md) — use, modification, and redistribution terms.

## Core decisions

- Headless modular monolith with independently runnable pipeline, API, and CLI entry points.
- PostgreSQL as the operational system of record.
- Jobicy as the first live source, with source-specific governance encoded in its connector.
- Deterministic eligibility rules separated from fallible fact extraction.
- Deterministic parsers first; optional OpenAI extraction via locally authorized ChatGPT Plus plan usage.
- Paid OpenAI API usage is deferred; Ollama requires a separately approved experiment.
- Canonical versioned JSON report with a static HTML rendering as the first complete user journey.
- Offline, deterministic CI; external feeds and models are never required for pull-request validation.
- No-cost static demonstration through GitHub Pages before any hosted API deployment.

ChatGPT Plus is the planned local optional inference path, subject to account access
and usage limits; the adapter is not implemented yet. Standard API billing is separate
and no paid fallback is enabled. See [the provider decision](docs/adr/0006-chatgpt-plan-extraction.md).

## Target first product command

```bash
borderless search --country BO --role data-engineer --format html --output ./report
```

Implementation should begin with the first ready foundation task in the development plan.
Every task must leave the worktree green and preserve the accepted ADRs unless new
evidence justifies superseding one.
