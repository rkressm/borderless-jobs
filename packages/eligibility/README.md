# Pure eligibility decisions

Evaluate validated facts using explicit candidate, policy version, and as-of inputs. Own dimensional/global composition and rule traces. Import domain only; never extract facts or perform I/O.

Public surface: Empty until the consuming contract task; only explicitly listed `__all__` names are public. Import supported values from `borderless.eligibility`; implementation submodules are private. Public contracts use standard-library and Borderless values only.

See [architecture](../../docs/architecture.md) and [import rules](../../docs/import-boundaries.md). Run `scripts/check-quality.sh all` from the repository root.
