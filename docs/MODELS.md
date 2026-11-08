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

Adaption also serves `deepseek-v4-flash` (models listed by the SDK: `glm-53-flash`, `glm-5.2`, `qwen3.5-397b`, `gemma-4-26b-a4b-it`, `qwen3.8-27b`, `deepseek-v4-flash`, `gemma-4-31b-it`). Checked on 2026-11-08 with a rubric prompt: `deepseek-v4-flash` is a model that reasons before answering. With `max_output_tokens` of 40 it returned empty text (the budget was used up); with 600 it returned a JSON object after a response time between 1 and 3 seconds, sometimes preceded by a few words, so the parser extracts the first JSON object. Extra arguments `top_logprobs`, `logprobs` and `include` through `extra_body` were accepted without error and returned no logprobs. The `reasoning` argument is rejected by the SDK. The `temperature` argument is accepted.

Modal is not used (decision of the author, 2026-11-08).

Consequence for the design: D2 uses its rubric mode by default (a short JSON object with three integer scores, normalized to [0, 1], plus 0.05 times the D1 score to break ties). The logprob mode stays implemented for a provider that supports it. Guardrail model for D2: `deepseek-v4-flash` on Adaption, rubric mode, `max_output_tokens` 600.

## Still to enter (human)

| Item | Needed by |
|---|---|
| Model id, price and per-minute limit of the swarm model | pilot (T07) |
| Model id, price and per-minute limit of the guardrail model | detectors fit and A3 |
| Spend cap per provider (`*_BUDGET_USD` in `.env`) | any real run |
