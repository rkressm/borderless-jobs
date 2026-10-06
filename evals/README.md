# Protected deterministic eligibility cases

The synthetic corpus in `cases/m2-core.jsonl` is separate from implementation
fixtures. It contains 12 policy annotations covering geographic inclusion,
exclusion precedence, exhaustive allowlists, missing/foreign engagement,
timezone daylight-saving compatibility, and contradictory evidence.

`scripts.eligibility_eval.ProtectedCase` is the strict annotation schema v1.0.0.
Every row has a unique case ID, immutable canonical text, typed eligibility inputs,
expected geography/engagement/timezone outcomes, global verdict, annotation flag,
rationale, reviewer identity and review document reference. Evidence is verified
against canonical text and must identify that exact case. Unknown/missing fields,
unreviewed cases, oversized corpora, duplicate IDs and duplicate content fail.

The review record distinguishes independent AI review from human review. Expected
labels come from the architecture policy, rather than generated engine outputs.
Changes to an expectation require updating the rationale and review record.

Run from the repository root:

```bash
UV_CACHE_DIR=.cache/uv uv run --locked --all-packages --group migration --offline python -m scripts.eligibility_eval
```

The ordinary pytest suite runs the same smoke eval twice and compares complete
serialized assessments. It also proves a changed protected expectation fails.
Thus existing backend CI protects these cases without a separate service or model.

The runner loads IANA zones outside eligibility and records the installed tzdata
version from `tzdata.zi` in every timezone assessment. Linux system tzdata is an
explicit prerequisite; no downloading or timezone lookup occurs in the pure engine.
For historical replay, callers must preserve the recorded tzdata release alongside
the rule/reference versions and typed inputs. These synthetic 2026 US DST cases
should retain their expected labels across supported system releases; a timezone
rule change produces a visible eval failure.
