# Python import boundaries

Run `scripts/check-quality.sh imports` (included in `all`) after adding or changing
package imports. The stdlib-only checker parses every Python file under
`apps/*/src/borderless/` and `packages/*/src/borderless/` without importing it.
Unknown `borderless` modules fail until their ownership and rule are reviewed.

Internal dependencies point inward:

- `domain` imports no other Borderless module.
- `eligibility` imports only `domain`.
- `connectors` imports only `domain`; it cannot write to `catalog` directly.
- `catalog` imports `domain` and `connectors`.
- `extraction` imports `domain` and `catalog`.
- `search` imports `domain`, `catalog`, `eligibility`, and `extraction`.
- `reporting` imports `domain`, `eligibility`, and `search`.
- `cli` is an outer adapter and may import the application modules; none of those
  modules may import `cli`.

The pure `domain` and `eligibility` modules may import only the restricted
standard-library set in `scripts/check_imports.py`; third-party,
filesystem, network, process, database, and framework imports fail. New legitimate
imports require a deliberate policy change. The same AST gate rejects direct
`open`, `exec`, `eval`, `__import__`, `now`, `utcnow` and `today` calls,
including attribute calls and clock class aliases. This is a static guard rather
than a general proof: indirect side effects and arbitrary supplied callbacks still
need review. The eligibility runtime test disables file access, sockets and zone
loading after inputs and IANA zones have been loaded by the caller. Timezone rules
only consume those objects and the explicit `as_of`. API and worker adapters will
be added to this graph when their tasks introduce them.
