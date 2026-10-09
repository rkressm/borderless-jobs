# ADR-0006: Prefer OpenAI via Local ChatGPT Plan Usage

Status: accepted\
Date: 2026-10-09\
Supersedes: [ADR-0003](0003-local-first-ai.md)

Laya cannot be integrated on the available development machine. The maintainer chooses
local ChatGPT Plus usage with no API budget. Keep deterministic parsers first and the
provider-neutral extraction seam; prefer optional OpenAI candidate-fact extraction via
an independently authorized ChatGPT profile in an eligible local open-source app.
Only the pure eligibility engine emits verdicts.

## Consequences

- Remove the Laya runtime and former L01–L04 spike from the active plan without claiming
  they were implemented or evaluated. No existing code or locked dependency needs removal.
- Retain Python 3.12; provider choice does not change catalog, domain, or report ownership.
- Verify account/workspace permission and actual access; a Plus subscription alone does
  not establish entitlement. Unavailable access or usage limits preserve deterministic
  operation and are reported explicitly.
- Local execution still sends approved source text to a remote provider. Record that
  disclosure and verify source permissions before enabling enrichment.
- Standard OpenAI API billing is separate and deferred. Do not automatically fall back
  to paid calls. Ollama remains deferred pending a distinct, resource-gated experiment.
- Implement optional authorization, inference, and frozen-case evals in M5; this roadmap
  revision does not implement an adapter or verify the maintainer's account.
- Keep credentials local, dependencies optional and locked at their consuming task,
  and mandatory CI offline using fake providers.

## Sources

Reviewed on 2026-10-09:

- [OpenAI local open-source plan usage](https://developers.openai.com/siwc/token-sharing-open-source)
- [Registration and sign-in](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Subscription and API pricing distinction](https://learn.chatgpt.com/docs/pricing)
