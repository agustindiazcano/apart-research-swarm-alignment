## Project context: swarm-contagion (append to AGENTS.md)

Goal: measure how an infection spreads through conversations in an LLM swarm (recruitment chains and terminal breaches of a split canary credential), and how well four detectors catch it, offline and as online gates: a lexical logistic regression, a logprob-calibrated micro-LLM guardrail, a graph-contextual cascade and a micro-verifier cascade. Full definitions: `docs/PROJECT.md`, `docs/EXPERIMENT_DESIGN.md`, `docs/ARCHITECTURE.md`, `docs/PLAN.md`, `docs/TASKS.md`. Hackathon rules: `docs/hackathon/RULES.md`; talk lessons: `docs/hackathon/TALKS_DIGEST.md`; prior work: `docs/hackathon/PRIOR_WORK_DIGEST.md`.

Deadline: Mon Nov 9, 2026, 08:59 ART (Sun Nov 8, 11:59 PM AoE). Do not plan experiments after Mon 05:00 ART; after that only analysis, writing and checking.

### Hard invariants

1. Ground truth (`gt.json`, labels, holders, patient zero) is never visible to agents or detectors. Agents see only their role prompt, private records, visible board messages and their own tool results. No word like test, simulation, evaluation in agent prompts.
2. Metrics come from the event log and `gt.json` only. Never from agent self-reports or an LLM judgment. One declared exception: the `intent` field of a post is protocol data (a message type chosen from a fixed list); it defines the label L1_action, detectors never see it, and its agreement with the content is checked by hand on a sample and reported.
3. No API key, token or secret in code, logs, event files, commit messages or PR text. Environment variable names only in `.env.example`.
4. Hard spend caps per provider. A missing cap blocks calls. Never remove a cap to make a run pass.
5. Seeds, configs and playbooks are frozen after tag `prereg-v1`. Changes go in the deviations log, not silently in code.
6. No outcome-based exclusion of episodes. Failed episodes are rerun with the same seed (max 2) and then reported as failures.
7. Detectors are fit on TRAIN seeds only. Thresholds are saved before any TEST episode is scored. Playbook style 2 is never used in TRAIN.
8. Playbook texts stay in `experiments/payloads/` and are never copied into public docs or the report.
9. Local, synthetic data and a fake credential only. Nothing touches a real service beyond model-provider APIs.
10. Every reported number comes from committed event logs. No number from memory, from the talks, from the literature or from a synthetic simulation is presented as a result.

### Working rules (author's workflow)

Check the branch and worktrees before acting. One worktree and branch per task. Failing test first, shown failing for the right reason. CI green before a PR. The human approves and merges every PR; ask before opening one. Every PR is based on `main`. Do not push to main. Do not suggest shortcuts that break this workflow. Output language is English. No em dash. No emojis. Neutral language only (see the language rule in `AGENTS.md`).

### Claims policy

Report only what the data show. Do not cite speaker figures from the sprint talks as facts. Cite only references verified by hand. Declare what is pre-existing. A null result is a result. Unknown facts stay `TODO(verify)` until verified by running something.

### Commands (fill in after T01)

```
swarmlab run-episode --config experiments/configs/free_flow.yaml --world-seed 101 --topology ring
swarmlab batch --matrix experiments/configs/free_flow.yaml --resume
swarmlab analyze results/free_flow
swarmlab prereg
```
