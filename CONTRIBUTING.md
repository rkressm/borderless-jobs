# Contributing to Borderless Jobs

The project is currently in its implementation-foundation phase. Work is organized as
small, independently verified tasks from
[`docs/development-plan.md`](docs/development-plan.md).

## Before making a change

1. Read [`AGENTS.md`](AGENTS.md) for the atomic delivery loop and repository rules.
2. Read [the architecture](docs/architecture.md) and the ADR relevant to the change.
3. Select one ready task whose dependencies are complete.
4. Use a dedicated branch and worktree; keep its files and generated state isolated.
5. State the intended result, owned files, and verification before implementation.

## Change discipline

- Keep one observable behavior per change and split work that cannot be verified alone.
- Add or refine a behavior-focused test before or with executable behavior.
- Run focused checks first, then every affected package-level quality gate.
- Stop on a failing gate; do not stack unrelated work on a red worktree.
- Justify each new direct dependency and commit its reviewed lockfile change.
- Update contracts, fixtures, documentation, and ADRs when their meaning changes.
- Keep credentials, private source payloads, model weights, and generated local reports
  out of Git.

## Submitting work

Describe the completed plan task, the behavior changed, the exact verification performed,
and any residual risk. Keep dependency updates separate from unrelated product changes
when practical. Do not merge automated dependency updates without normal review and
tests.

The project license has not yet been selected. Review [`LICENSE.md`](LICENSE.md) before
redistributing or accepting external contributions.
