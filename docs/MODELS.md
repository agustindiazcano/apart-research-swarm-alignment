# Models and providers (gate G1 record)

Status: partial. This file records what was checked by running calls. Prices, per-minute limits and the swarm model choice are entered by the human from the provider consoles (`TODO(verify)`). No key or token appears here.

## Provider check, 2026-11-08

One small call per model (at most 16 output tokens), asking for logprobs. The request asked the model to answer `SAFE` or `UNSAFE` for a request message. Probe script: kept outside the repository; the calls used the variables listed in `.env.example`.

| Provider | Model id | Authentication | Logprobs | Notes |
|---|---|---|---|---|
| Meta Muse (`https://api.meta.ai/v1`, chat completions) | `muse-spark-1.3` | accepted | not available | HTTP 400, parameter `logprobs`: "`logprobs` is not supported with reasoning." |
| Google Vertex AI (Gemini, project and location from the environment, Application Default Credentials) | `gemini-3.8-flash` | accepted | not available | HTTP 400 INVALID_ARGUMENT: logprobs is not supported for this model |
| Google Vertex AI | `gemini-4-argon` | accepted | not available | Same error as above |
| Adaption (`adaption` SDK, Responses API) | `gemma-4-31b-it` | accepted | not available | The SDK method `responses.create` rejects the arguments `include`, `top_logprobs` and `logprobs` (TypeError: unexpected keyword argument). A call without them returned text. |
| Modal (DeepSeek, Qwen) | not checked | not checked | not checked | `TODO(verify)`: the endpoint URL and the way the token is sent are not recorded in this repository. |

Consequence for the design: D2 uses its rubric mode by default (a short JSON object with three integer scores, normalized to [0, 1], plus 0.05 times the D1 score to break ties). The logprob mode stays implemented for a provider that supports it; Modal is the candidate if its endpoint accepts logprobs for a non-reasoning model.

## Still to enter (human)

| Item | Needed by |
|---|---|
| Model id, price and per-minute limit of the swarm model | pilot (T07) |
| Model id, price and per-minute limit of the guardrail model | detectors fit and A3 |
| Modal endpoint URL and token usage | D2 decision (logprob or rubric) |
| Spend cap per provider (`*_BUDGET_USD` in `.env`) | any real run |
