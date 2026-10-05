# Borderless Jobs agent guide

Build the smallest verified increment that advances the active milestone. Keep
domain decisions deterministic, evidence-backed, and independent of transports,
databases, model providers, and presentation frameworks.

## Start here

- Read `docs/architecture.md` before changing module boundaries or data ownership.
- Read `docs/development-plan.md` before selecting or sequencing implementation work.
- Read the relevant ADR before changing an accepted architectural decision.
- Read `.cursor/rules/supply-chain-security.mdc` before changing dependencies,
  installers, build inputs, lockfiles, or CI actions.
- Treat manifests, lockfiles, and executable help as the source of truth for commands.

## Atomic delivery loop

1. Select one ready task with a result that can be verified independently.
2. Inspect the affected interface, tests, and local conventions before editing.
3. Add or refine one behavior-focused test when the change has executable behavior.
4. Implement only enough code to satisfy that behavior through the intended seam.
5. Run the smallest relevant formatter, linter, type check, and test set.
6. Run affected integration or contract checks before declaring the task complete.
7. Update documentation, fixtures, schemas, or ADRs when their contract changed.
8. After every required check is green, change the task's status in
   `docs/development-plan.md` from `[ ] Pending` to `[x] Complete`.
9. Report the verified result, commands run, and any remaining risk.

Each step must leave the worktree coherent. Stop and diagnose a failing quality gate;
do not accumulate unrelated changes on top of a red state. Split work again when a
step cannot be implemented and verified in a focused review. An unchecked task remains
incomplete even when implementation exists.

## Architecture guardrails

- Keep eligibility pure: no I/O, model calls, framework imports, or hidden clock reads.
- Models and parsers emit typed facts with provenance; only eligibility emits verdicts.
- Keep CLI, worker, FastAPI, and Next.js thin adapters over application interfaces.
- Put `SearchSpecification` in `search` and the public `SearchReport` contract in
  `reporting`; keep shared value objects and invariants in `domain`.
- Prefer `UNCERTAIN` to an unsupported permissive conclusion.
- Preserve raw source data privately; evidence offsets target an immutable canonical
  normalized-text version.

## Readability and simplicity

- Keep functions focused on one responsibility and aim for at most 15 lines where
  practical. Allow longer functions when splitting would make the flow harder to
  follow; preserve readability over a mechanical line limit.
- Use descriptive variable and function names that reflect their domain meaning
  and purpose. Use consistent vocabulary and naming conventions across the codebase.
- Choose the simplest implementation that satisfies the current requirement.
  Introduce abstractions, configuration, and generalization only when a concrete
  need justifies them; keep complexity proportional to the problem.

## Quality and security

- Prefer the standard library or an existing dependency. Justify every new direct
  dependency by purpose, maintenance, license, provenance, and transitive impact.
- Keep runtime dependencies minimal and isolate development, AI, and observability
  extras. Commit and verify lockfile changes with manifest changes.
- Treat feeds, job HTML, model output, URLs, fixtures, and generated artifacts as
  untrusted input. Validate sizes, schemas, vocabularies, evidence, and destinations.
- Keep credentials out of source, logs, reports, browser bundles, fixtures, and tests.
- Preserve offline deterministic tests; external feeds and models are opt-in checks.
- Pin CI actions and release inputs immutably and grant each workflow minimum rights.

## Worktree discipline

- Resolve paths from the repository root; never depend on a checkout's absolute path.
- Namespace ports, containers, databases, caches, and generated output per worktree.
- Do not edit, clean, stage, or revert changes outside the current task's ownership.
- Keep commits and migrations additive so concurrent worktrees can rebase safely.
- Before pushing, follow `.cursor/rules/git-push-safety.mdc` to preserve remote history.
