# LASTCONTEXT

Last updated: 2026-11-08. All operational times use Argentina time (ART).

## Session state

The coordinator updated main from origin/main to commit 370bfdd. PRs #22 through #32 are merged. The working tree on main is clean apart from untracked developer notes and utils which remain untouched.

Work continued on the integration branch `chore/integration-check` in `apart-research-swarm-alignment-wt-integration-check`. The branch combined `feat/runtime-cli`, `feat/analysis-pipeline`, and `feat/training-pipeline` on top of current `main`.

All 6 CLI commands (`run-episode`, `batch`, `prereg`, `analyze`, `train-detectors`, `score`) are registered in `cli.py` and callable via `swarmlab.cli` and `python -m swarmlab`. Full test suite passes: 400 passed, 1 skipped. Ruff and mypy pass with zero warnings across 45 source files.

No paid real provider calls were performed. The integration is ready for PR against main pending human approval.

## Human decisions

- Spend caps: Muse USD 20, Vertex USD 20, Adaption 500 credits (explicitly approved after discovering that official prices are credit-denominated). Adaption USD conversion remains TODO(verify), so cost_usd stays null. Use Adaption for the primary workload. No real provider calls were made in this session.
- Playbooks remain outside git while the repository is public.
- All times use ART. Experiments freeze Monday 2026-11-09 at 05:00; submission deadline 08:59.
- Separate offspring means count recruited children and breached children, each divided by all infected agents, including agents without children. A child can enter both numerators. They describe a finite observed episode and do not establish an immunity threshold.

## Branches and worktrees

All paths below are siblings of the primary checkout, prefixed `apart-research-swarm-alignment-wt-`.

| Branch | Suffix | State |
|---|---|---|
| feat/world | world | Merged in PR #22 |
| feat/plots | plots | Merged in PR #23 |
| docs/provider-check | providers | Merged in PR #24 |
| chore/review-llm-core | review-llm | Merged in PR #25 |
| chore/review-detector-lexical | review-lexical | Merged in PR #26 |
| chore/review-detector-guardrail | review-guardrail | Merged in PR #27 |
| chore/review-events-extract | review-extract | Merged in PR #28 |
| feat/provider-adapters | provider-adapters | Merged in PR #29 |
| chore/review-swarm-runtime | review-runtime | Merged in PR #30 |
| feat/billing-units | billing-units | Merged in PR #31 |
| docs/coordinator-state | coordinator-state | Merged in PR #32 |
| chore/integration-check | integration-check | Combined CLI runtime, training pipeline, analysis pipeline; 400 tests passing, ruff/mypy clean; ready for PR |

Prior worktrees and branches remain untouched. Primary checkout has untracked add_docs_prompt.md and swarm-utils/. Prior swarm and prompts worktrees contain untracked world types. Do not delete, edit or commit those files. The mock experiment worktree is outside this task and supplies no reported results. Docker Desktop was stopped and verified stopped.

## Current integration work

- PersistentBudgetGuard in llm/ledger.py shares charges across CLI processes and factories. It locks and atomically updates a campaign ledger, preserves billing units, rejects cap increases and corrupt/missing initialized state, and keeps returned charges even when a cap aborts.
- GuardedClient exposes on_result(result, call_stats, cost_record) before recording cost against the cap. Runtime integration writes provider_calls.jsonl per attempt; it is the authoritative billing source, separate from runner action/parse events. Analysis does not double count.
- RuntimeFactory accepts an injected guard and limiter. The final integration supplies the persistent guard, with a campaign path shared by swarm, guardrail, pilot, TRAIN and TEST.
- Training and scoring commands (train-detectors, score) are integrated into CLI with strict type-safety and support for rubric guardrails.
- Analysis pipeline handles log loading, kinetics, McNemar test, bootstrap intervals, H2 regression on exposed agents, defense plots, and summary CSVs.
- Draft matrices for pilot, TRAIN (clean/infected, ring/complete), controls (A0), A1 free flow, A3 gating, and A3c gate cost are prepared and verified.

## Next actions

1. Ask human approval to open PR for `chore/integration-check` against `main`.
2. Upon approval, push branch and open PR using `gh pr create --base main`.
3. Human reviews and merges the PR into `main`.
4. Pull `main` in primary checkout.
5. Copy the 3 playbooks (`playbook_0.txt`, `playbook_1.txt`, `playbook_2.txt`) into the working checkout `experiments/payloads/`.
6. Run the pilot on candidate model (Adaption `gemma-4-31b-it` or `deepseek-v4`).
7. Run `swarmlab prereg` to generate preregistration manifest SHA-256, and request the human to create the `prereg-v1` tag.
8. Execute TRAIN, fit detectors, freeze thresholds, and execute reported experimental runs before Monday 05:00 ART.
