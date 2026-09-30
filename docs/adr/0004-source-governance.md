# ADR-0004: Encode Source Governance in Connectors

Status: accepted  
Date: 2026-09-30

## Context

Remote-job sources have different attribution, polling, retention, and redistribution rules. Treating those rules as informal documentation makes violations likely as connectors multiply.

## Decision

Every connector returns an explicit source policy with its fetched data. The catalog stores that policy and public renderers enforce its attribution and canonical-link requirements. Use Jobicy first, Remotive second, and do not scrape Wellfound.

## Consequences

- Compliance behavior is testable and source-specific.
- Raw descriptions remain private unless redistribution is clearly allowed.
- Public fixtures and demonstrations use synthetic or explicitly reusable content.
- Policy changes require review and version updates.
- Adding a connector requires both schema work and a governance decision.
