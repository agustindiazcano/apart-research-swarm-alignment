# Provider billing units and execution decisions

Recorded on 2026-11-08. These are provider configuration facts and maintainer decisions,
not experimental results. The maintainer requested delegated retrieval from the local
`software-ai-eval` project and verification against official documentation.

## Adaption

The [official model catalog](https://docs.adaptionlabs.ai/inference-stacks/models/)
expresses prices in credits per million tokens. It does not establish a USD conversion.
The [credits FAQ](https://docs.adaptionlabs.ai/resources/faq/) describes balances and
estimates without defining that conversion. Checked on 2026-11-08; the pages do not
state a price effective date. USD per credit: `TODO(verify)`.

| Model | Input credits per million | Cached input credits per million | Output credits per million |
|---|---|---|---|
| `gemma-4-31b-it` | 0.09 | 0.05 | 0.34 |
| `gemma-4-26b-a4b-it` | 0.0765 | 0.0425 | 0.255 |
| `deepseek-v4-flash` | 0.04444 | 0.001414 | 0.13332 |

The local project's `docs/MODELS.md` described the Gemma rates as USD. That unit is
not supported by the official catalog and must not be transferred into USD fields.
This project uses the catalog's credit unit. Cached-input rates require separately
reported cached usage; without that breakdown, accounting uses the uncached input
rate and identifies the accounting rule in the run configuration.

The maintainer explicitly authorized a cap of 500 Adaption credits in this session.
Record `billing_unit="credits"`, `cost_credits` and `cost_usd=null`. Do not convert
credits to USD without a verified conversion. Missing caps still block calls.

Pilot candidate: `gemma-4-31b-it`. The preceding provider-check record reports text
output from that model. This does not establish propagation behavior or latency in
the swarm. The pilot determines the swarm model. D2 uses `deepseek-v4-flash` in
rubric mode with the configured output budget from `docs/MODELS.md`.

Requests/minute, tokens/minute and available provider concurrency: `TODO(verify)`.

## Muse and Vertex

The maintainer authorized separate USD caps of 20 for Muse and 20 for Vertex.
The local project's `config/credits.yaml` and `config/models.yaml` contain prices
with a recorded check date of 2026-11-06 and source URLs. They are lookup leads,
not a current provider-console verification for this project. Enter verified rates
in the execution configuration before calling either provider: `TODO(verify)`.

## Execution ordering

Use Adaption for the primary workload, as directed by the maintainer. No real
provider call was made during the review tasks. A paid pilot requires unit-aware
budget enforcement, a persisted event log, model and configuration provenance,
and the experiment deadline check. Human review and merge of implementation PRs
remain required.
