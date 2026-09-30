# ADR-0002: Separate Fact Extraction from Eligibility

Status: accepted  
Date: 2026-09-30

## Context

Models can extract useful facts from unstructured listings, but direct model verdicts are difficult to reproduce, explain, and regression-test. False `YES` answers are particularly harmful.

## Decision

AI and deterministic parsers produce typed facts with evidence. A pure, versioned Python eligibility module transforms those facts into dimensional and global decisions. The module performs no I/O and makes no model calls.

## Consequences

- Every verdict has a stable rule trace and can be replayed.
- Extraction providers can be compared without silently changing policy.
- Unknown or contradictory facts produce `UNCERTAIN` rather than guesses.
- Rule and extraction errors are measured separately.
- Maintaining reviewed geographic and engagement policy data becomes an explicit responsibility.
