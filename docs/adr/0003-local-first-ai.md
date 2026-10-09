# ADR-0003: Use Local-First, Provider-Neutral AI

Status: superseded by [ADR-0006](0006-chatgpt-plan-extraction.md) on 2026-10-09\
Date: 2026-09-30

## Context

The MVP has no API budget. The available development machine can run small classifiers but is not suitable for high-quality, high-throughput generative inference. ChatGPT plan usage is available to eligible local open-source tools through user authorization.

## Decision

Define a provider-neutral extraction interface. Use deterministic parsers first, Laya only for bounded decisions, ChatGPT plan usage as an optional authorized provider, and Ollama/Qwen as an experimental local baseline. Mandatory operation and CI do not require any model.

## Consequences

- The product remains usable and testable without paid inference.
- Provider quality is selected through evals rather than branding.
- OAuth credentials and model runtimes add optional setup paths.
- Laya cannot be represented as a general structured extractor.
- A future paid provider is an adapter change, not a domain redesign.
