# Clean checkout setup

Status: rehearsed on Ubuntu 24.04, 2026-10-04.

Prerequisites not installed by this repository: Git, `uv`, CPython 3.12,
Docker Engine with the Compose plugin, permission to access the Docker daemon,
and network access for the first locked dependency sync and PostgreSQL image
pull. See [runtime policy](runtime-policy.md) for the supported platform. No
feed, AI account, or application credential is needed. Review the
[dependency policy](dependency-policy.md) before changing any installer,
manifest, lockfile, or image digest.

Run the following from the root of a fresh checkout. `uv` uses an ignored
cache within this checkout, so another worktree cannot mutate it. The initial
sync must be online; later quality and migration commands run offline with
respect to Python packages.

```bash
./scripts/check-python-version.sh
uv --version
docker compose version
python3 scripts/worktree_env.py --print
UV_CACHE_DIR=.cache/uv uv sync --locked --all-packages --all-groups
UV_CACHE_DIR=.cache/uv uv run --locked --offline --package borderless-cli borderless --help
bash scripts/check-quality.sh all
bash scripts/check-migrations.sh
git diff --exit-code -- uv.lock
```

`check-migrations.sh` starts a per-worktree disposable PostgreSQL service,
checks `base → 0001 → base → 0001`, and removes that test container on exit.
It does not touch the development database or its volume. A second identical
locked sync should only check packages and leave `uv.lock` unchanged. For
security checks that need network access, see [security gates](security-gates.md).

Troubleshooting:

- Python check fails: install/select CPython 3.12 (for example,
  `uv python install 3.12`) and rerun the check. `uv` must be installed
  separately according to its official installation instructions.
- Locked sync reports a DNS/download error: permit network access to the
  package index and retry the same command. Do not remove `--locked`, switch
  indexes silently, or copy a different worktree's virtual environment.
- A `uv run --offline` command cannot find a package: complete the locked
  `--all-groups` sync in this checkout first, with `UV_CACHE_DIR=.cache/uv`.
- Docker socket access is denied: start Docker and grant the current user
  access to its daemon; then retry the migration check. A port-in-use error
  means another local process conflicts with a derived port: inspect
  `python3 scripts/worktree_env.py --print` and the other worktree before
  stopping anything. Never stop another checkout's service blindly.
- Migration check fails after a previous interrupted run: inspect the
  namespaced test service, then use `bash scripts/db.sh test-down` in this
  checkout before retrying. This removes only its disposable test container.
- Quality or migration checks fail for code reasons: diagnose the failing
  check before continuing; do not mark a plan task complete on a red state.

Rehearsal: a detached, clean Git worktree had no `.cache`, `.venv`, or
`.worktree` directory before these commands. On CPython 3.12.3, `uv` 0.12.22,
and Docker Compose v5.1.3, the first locked sync into the empty local cache
took 2.90 s; a second sync took 0.07 s; the full quality loop took 13.46 s
and passed 23 tests; the migration cycle took 16.31 s. The lockfile remained
unchanged. Times are wall-clock measurements on this machine, not budgets or
guarantees. The PostgreSQL image was already present locally, so its initial
download time is not included.
