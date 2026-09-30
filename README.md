# Borderless Jobs

Borderless Jobs is a planned local-first product that turns remote job listings into evidence-backed answers to a concrete question:

> Can I actually work here from Bolivia?

Instead of trusting a generic `remote` label, the system evaluates geographic restrictions, engagement mechanisms, and timezone requirements. It returns `YES`, `NO`, or `UNCERTAIN` together with the source evidence and exact rule trace.

## Current status

The project is in the architecture and delivery-planning stage. No product implementation has been generated yet.

## Planning documents

- [Architecture](docs/architecture.md) — product scope, module interfaces, runtime and data design, AI extraction, eligibility semantics, testing, security, CI/CD, and evolution path.
- [Delivery roadmap](docs/roadmap.md) — dependency-driven milestones and release gates.
- [Step-by-step development plan](docs/development-plan.md) — atomic tasks with
  dependencies, estimates, observable results, and verification criteria.
- [Architecture decision records](docs/adr/) — concise records of the decisions that should not be rediscovered during implementation.

## Project governance

- [Contribution guide](CONTRIBUTING.md) — atomic changes, worktree discipline, and
  verification expectations.
- [License status](LICENSE.md) — no open-source license has been selected yet.

## Core decisions

- Headless modular monolith with independently runnable pipeline, API, and CLI entry points.
- PostgreSQL as the operational system of record.
- Jobicy as the first live source, with source-specific governance encoded in its connector.
- Deterministic eligibility rules separated from fallible fact extraction.
- Deterministic parsers first, Laya for bounded classification, and optional ChatGPT plan or Ollama extraction adapters.
- Canonical versioned JSON report with a static HTML rendering as the first complete user journey.
- Offline, deterministic CI; external feeds and models are never required for pull-request validation.
- No-cost static demonstration through GitHub Pages before any hosted API deployment.

## Intended first command

```bash
borderless search --country BO --role data-engineer --format html --output ./report
```

Implementation should begin with the first ready foundation task in the development plan.
Every task must leave the worktree green and preserve the accepted ADRs unless new
evidence justifies superseding one.
