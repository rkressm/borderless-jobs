# Concurrent worktree check

Status: verified on Ubuntu, 2026-10-04.

Use two checkouts of the same committed revision. For example, from an existing
checkout, create a disposable second checkout with
`git worktree add --detach .worktrees/f12-second HEAD`. The `.worktrees/`
directory is ignored. Do not copy `.venv`, `.cache`, `.worktree`, or generated
artifacts between checkouts.

In each checkout, run:

```bash
./scripts/check-python-version.sh
python3 scripts/worktree_env.py --print
UV_CACHE_DIR=.cache/uv uv sync --locked --all-packages --all-groups
bash scripts/check-quality.sh all
bash scripts/db.sh test-up
UV_CACHE_DIR=.cache/uv uv run --locked --all-packages --group migration --offline python -m scripts.check_migration_state base
UV_CACHE_DIR=.cache/uv uv run --locked --all-packages --group migration --offline python -m scripts.migrate test upgrade head
```

The two quality loops and test databases can run concurrently. After both
migrations, stop the disposable database in one checkout with
`bash scripts/db.sh test-down`. In the other checkout, this must still pass:

```bash
UV_CACHE_DIR=.cache/uv uv run --locked --all-packages --group migration --offline python -m scripts.check_migration_state 0001
```

Stop that checkout's disposable database with `bash scripts/db.sh test-down`
when finished. Remove a disposable Git worktree only after its services are
stopped, using `git worktree remove .worktrees/f12-second` from the first
checkout. These commands affect only the named worktree and its test service.

On 2026-10-04, the original checkout and `.worktrees/f12-second` each passed
the full quality loop (23 tests), started healthy PostgreSQL test services,
and migrated from `base` to `0001`. Their Compose projects were
`bj-borderless-jobs-f47c58955e6e` and `bj-f12-second-3a259e4c4c41`, their
test databases were `bj_test_f47c58955e6e` and `bj_test_3a259e4c4c41`,
and their localhost test ports were `49845` and `43884`. Each had its own
`.cache/uv`, `.cache/worktrees/<id>`, `.artifacts/worktrees/<id>`,
`.worktree/<id>/compose.env`, `.venv`, and `.coverage`. After the first test
service was removed, revision `0001` remained reachable in the second.

Port numbers are derived from a hash, not reserved globally; check the printed
ports before concurrent startup. A rare hash collision or another process
using the port requires a different checkout path or stopping the conflicting
service. Do not edit committed Compose settings to hard-code a shared port.
