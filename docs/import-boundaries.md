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
imports require a deliberate policy change. This is a static direct-import guard,
not proof of purity: dynamic imports, indirect side effects, and clock calls still
need review and behavior tests. API and worker adapters will be added to this graph
when their tasks introduce them.
