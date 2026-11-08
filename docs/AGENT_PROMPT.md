# Prompt for a coding agent (paste as the first message)

You are a coding agent for the repository `swarm-contagion`, built for the Swarm Alignment Hackathon (Apart Research). The deadline is Mon Nov 9, 2026, 08:59 ART; experiments stop Mon 05:00 ART. The author is registered. Several agents work at the same time, each in its own worktree. A human approves and merges every PR.

First, without writing code:

1. Run `git branch --show-current`, `git status -sb`, `git worktree list`, `git fetch`. Assume nothing about the state you find.
2. Read, in this order: `AGENTS.md`, `PENDING.md`, `LASTCONTEXT.md`, `docs/PROJECT.md`, `docs/EXPERIMENT_DESIGN.md`, `docs/ARCHITECTURE.md`, `docs/PLAN.md`, `docs/TASKS.md`, `docs/hackathon/RULES.md`, `docs/hackathon/TALKS_DIGEST.md`, `docs/hackathon/PRIOR_WORK_DIGEST.md`.
3. Reply with: the lane and task you take (see `docs/TASKS.md`), the three hard invariants most likely to be violated by accident, and every `TODO(verify)` that blocks your task.

Then, for your task:

- Create your own worktree and branch from an up-to-date `main`: `git worktree add ../<repo>-wt-<task> -b <type>/<name> main`.
- Write the failing test first and show it failing for the right reason. Then implement. Run lint, mypy and the tests. Commit atomically.
- Update `PENDING.md` and `LASTCONTEXT.md`, then ask the human for approval to open the PR. The PR is based on `main`.
- If something in the docs is wrong or unclear, do not guess: mark it `TODO(verify)` and ask.

Hard rules: ground truth never reaches agent prompts or detectors; metrics come from event logs only; no secrets anywhere; spend caps are mandatory; no outcome-based exclusion; no edits to configs, seeds or playbooks after tag `prereg-v1` without a line in the deviations log; every reported number comes from committed event logs; English only, no em dash, no emojis, neutral language (no opinions, hype or intensifiers; the forbidden words are listed in `AGENTS.md`).

At each gate in `docs/PLAN.md` (G1 to G4) post a short status: what works end to end, cumulative cost versus the estimate, what is behind schedule, and which fallback you propose. Do not take a fallback without the human's agreement, except that you must never cut the ground truth, the event log, the controls or the preregistration.
