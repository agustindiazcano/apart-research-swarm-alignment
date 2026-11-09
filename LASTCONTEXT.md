# LASTCONTEXT

Last updated: 2026-11-08. All operational times use Argentina time (ART).

## Session state

The current coordinator continued the preceding session by reading AGENTS.md, the context files, design documents, provider branch record, hackathon rules and delegation instructions. The working checkout main matched origin/main at b5e0a06 when checked. No edits were made in the primary checkout or prior agents' worktrees.

The human authorized opening all pending PRs after review and green CI. Every PR targets main; the human reviews and merges. PRs #22 to #30 are open; every base is main. Swarm and prompts are combined in #30 instead of duplicate PRs. No merges were performed by this coordinator.

## Human decisions

- Spend caps: Muse USD 20, Vertex USD 20, Adaption 500 credits (explicitly approved after discovering that official prices are credit-denominated). Adaption USD conversion remains TODO(verify), so cost_usd stays null. Use Adaption for the primary workload. No real provider calls were made in this session.
- Playbooks remain outside git while the repository is public.
- All times use ART. Experiments freeze Monday 2026-11-09 at 05:00; submission deadline 08:59.
- Separate offspring means count recruited children and breached children, each divided by all infected agents, including agents without children. A child can enter both numerators. They describe a finite observed episode and do not establish an immunity threshold.

## Branches and worktrees

All paths below are siblings of the primary checkout, prefixed `apart-research-swarm-alignment-wt-`.

| Branch | Suffix | State |
|---|---|---|
| feat/world | world | Existing branch, CI passed, PR #22 open |
| feat/plots | plots | Existing branch, CI passed, PR #23 open |
| docs/provider-check | providers | Existing branch, CI passed, PR #24 open |
| chore/review-llm-core | review-llm | New coordinator-owned continuation of feat/llm-core, corrected and coordinator-validated, CI passed, PR #25 open |
| chore/review-events-extract | review-extract | New agent-owned continuation of feat/events-extract, reviewed and coordinator-validated, PR #28 open |
| chore/review-detector-lexical | review-lexical | New agent-owned continuation of feat/detector-lexical, reviewed and coordinator-validated, CI passed, PR #26 open |
| chore/review-detector-guardrail | review-guardrail | New agent-owned continuation of feat/detector-guardrail, reviewed and coordinator-validated, CI passed, PR #27 open |
| chore/review-swarm-runtime | review-runtime | New agent-owned combined continuation of world, swarm and prompts; coordinator-validated, CI passed, PR #30 open |
| feat/provider-adapters | provider-adapters | New agent-owned implementation, coordinator-validated with mocks, CI passed, PR #29 open |
| feat/billing-units | billing-units | Unit-aware caps and cost records complete; coordinator review pending |
| feat/runtime-cli | runtime-cli | Run/batch/prereg CLI integration in progress |
| feat/analysis-pipeline | analysis-pipeline | Event-log analysis and H2 integration in progress |
| feat/training-pipeline | training-pipeline | TRAIN and offline scoring integration in progress |
| docs/coordinator-state | coordinator-state | This handoff and design clarification branch |

Prior worktrees and branches remain untouched. Primary checkout has untracked add_docs_prompt.md and swarm-utils/. Prior swarm and prompts worktrees contain untracked world types. Do not delete, edit or commit those files. The mock experiment worktree is outside this task and supplies no reported results. No services were started by this coordinator.

## Audit corrections

- LLM: cost_of(result) uses each response's token counts, budget authorization rechecked before queued calls and retries, finite nonnegative caps/costs/prices, async test dependency declared. In-flight charges remain unknown until responses return; no cost reservation is implemented.
- Extraction: short fragments require exact matching, long fragments allow one edit; exclude injected patient zero from H2; join report texts with newlines; line numbers for invalid UTF-8; initial_infection=False represents clean arms; separate offspring means.
- Lexical: optional episode_ids enforces episode-disjoint model fitting and Platt calibration; production must pass it. Binary labels checked. Negative selection uses labels regardless of sender state. Unreachable raw thresholds use standard JSON null and restore infinity on load.
- Guardrail: rubric output budget defaults to configurable 600; JSON parser handles braces inside strings; test literals satisfy repository language checks. Production explicitly uses rubric mode. The specified parse-failure policy retries once then permits a message using the declared fallback.

## Integration blockers

- Real provider adapters, CLI commands, TRAIN, offline scoring and analysis are not yet integrated.
- Adaption model prices were verified in official documentation at the human request, in credits. See docs/PROVIDER_PRICING.md. RPM/TPM and USD conversion remain TODO(verify). Never place a credit amount in cost_usd.
- Use initial_infection=False for A0, A3c and clean TRAIN; infection generation and prompts must also disable the injected objective.
- Add standalone D3 detector adapter; enforce previous-round graph context; keep D5 cached scores and count actual guardrail calls separately from messages routed to it.
- Unknown retry counts remain null; extraction emits known_retries and calls_with_unknown_retries, without treating unknown as zero.
- H2 analysis uses exposed rows only (total_solicitations_received >= 1).
- Save fitted thresholds before scoring any TEST episode, and keep held-out playbook style out of TRAIN.
- Copy ignored playbooks only into the execution worktree. Never commit them or publish attacker text in report/PR bodies.

## Next actions

Open the coordinator handoff PR and remaining validated integration PRs. Human merges world first (#22), then LLM (#25) before adapters (#29); #30 includes both swarm and prompts. All reviewed branches have been pushed. Complete runtime integration with a mock end-to-end test before any pilot. Then pilot, human preregistration tag, TRAIN and reported runs. After 05:00 ART only analysis, writing and checks.
