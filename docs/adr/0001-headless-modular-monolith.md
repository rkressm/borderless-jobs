# ADR-0001: Use a Headless Modular Monolith

Status: accepted  
Date: 2026-09-30

## Context

The product needs ingestion, extraction, deterministic rules, reporting, CLI, HTTP, and web presentation. It is built by one developer with no deployment budget, but it should be able to separate workloads later.

## Decision

Build one versioned Python codebase with deep domain and application modules. Run pipeline, API, and CLI as separate entry points. Treat FastAPI, CLI, Next.js, scheduled commands, and future MCP as adapters over the same application interfaces.

## Consequences

- Domain behavior is testable without transport or infrastructure.
- One release and one local database keep operation affordable.
- Processes can scale independently before modules become network services.
- Module seams require discipline because a monorepo does not enforce runtime isolation.
- Microservices are deferred until scaling, ownership, security, or release evidence justifies them.
