# ADR-0005: Deliver a Canonical Report and Static Site First

Status: accepted  
Date: 2026-09-30

## Context

The MVP needs a demonstrable outcome without hosting an API or database. It should later support a dashboard, CLI, public API, and agent harnesses without duplicating business logic.

## Decision

Make a versioned `SearchReport` JSON value the canonical output. Ship CLI and static HTML renderers before the interactive dashboard. Add HTTP and MCP as adapters over the same report-building use case.

## Consequences

- The first end-to-end demo is shareable and can be hosted at no infrastructure cost.
- Reports are reproducible, snapshot-testable, and harness-friendly.
- The HTML renderer cannot own ranking or decision logic.
- Interactive features arrive later than the headless experience.
- Schema versioning becomes part of the public product contract.
