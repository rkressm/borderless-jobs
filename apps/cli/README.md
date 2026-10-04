# Command adapter

Parse arguments, invoke application interfaces, and translate results/errors into output and exit codes. No ranking, eligibility, source parsing, SQL, or provider logic.

Public surface: `build_parser` and `main`. Import supported values from `borderless.cli`; implementation submodules are private. Public contracts use standard-library and Borderless values only.

See [architecture](../../docs/architecture.md) and [import rules](../../docs/import-boundaries.md). Run `scripts/check-quality.sh all` from the repository root.
