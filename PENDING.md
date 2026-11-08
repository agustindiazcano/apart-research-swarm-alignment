# PENDING

Prioritized list of open tasks. Read this at the start of every session, together with `LASTCONTEXT.md`. Update it after every finished task (see `AGENTS.md`, "Session protocol").

Last updated: 2026-11-08

## Traffic light

| Light | Meaning |
|---|---|
| 🔴 | Blocking or urgent. Nothing downstream can finish without it. |
| 🟡 | Next. Do it once the blockers are clear. |
| 🟢 | Later. Needed before submission but not blocking now. |
| ⚪ | Backlog. Optional; dropped first if time runs out. |

## Phase codes

| Code | Phase | Goal |
|---|---|---|
| SETUP | Repository and process | Scaffold, rules, docs, CI, handoff files |
| SCOPE | Problem definition | Title, track, research question, plan |
| BUILD | Implementation | Code, experiments, data collection |
| EVAL | Analysis | Results, figures, checks against the claims |
| REPORT | Writing | PDF report on the official template, 4 to 8 pages plus appendices |
| SUBMIT | Delivery | Final checks and upload before the deadline |

Task IDs are `<PHASE>-<number>`, for example `SCOPE-01`. Never reuse an ID. Moved or finished tasks keep their ID.

Submission deadline: Monday, November 9, 2026, 11:59 UTC (Sunday, November 8, 11:59 PM AoE), which is 08:59 in Argentina (UTC-3).

## Open tasks

Ordered by priority, top first. Task IDs T01 to T15 are defined in `docs/TASKS.md`; lanes in `docs/PLAN.md`.

| # | Light | ID | Task | Depends on | Status |
|---|---|---|---|---|---|
| 1 | 🔴 | T00 | Merge the redesign docs PR (human approves) | none | branch `docs/redesign-infected-swarm` |
| 2 | 🔴 | T01 | Package skeleton, config, CLI stub, CI (ruff, mypy, pytest) and the frozen `schema.py` contract, lane A | T00 | open |
| 3 | 🔴 | T05 | Event schema, extraction and statistics, lane B | T00 | open |
| 4 | 🔴 | T02 | LLM client with logprobs option and budget guard, lane A | T01 | open |
| 5 | 🔴 | T03 | World generator and ground-truth rules, lane A | T01 | open |
| 6 | 🔴 | T04 | Swarm core: board, ring and complete topology, agents, runner, lane A | T02, T03 | open |
| 7 | 🔴 | T06 | Detectors D1 to D3 and the online gate, lane B | T05 | open |
| 8 | 🔴 | G1 | Provider check (logprobs, temperature, model ids, limits) and `docs/MODELS.md` | T04, T05, T06 | human supplies console data |
| 9 | 🟡 | T07 | Pilot and playbook calibration (3 seeds) | G1 | open |
| 10 | 🟡 | T08 | Preregistration and tag `prereg-v1` | T07 | open |
| 11 | 🟡 | T09 | Batch runner | T04 | open |
| 12 | 🟡 | T10 | Runs: TRAIN, A0, A1, A3, A3c, A2 scoring | T08, T09, T06 | open |
| 13 | 🟡 | T11 | Analysis and figures from committed logs | T05 | open |
| 14 | 🟢 | T12 | D4 micro-verifiers with veto gate | T06 | open |
| 15 | 🟢 | T14 | Reproduction instructions and report assets | T11 | open |
| 16 | 🟢 | T15 | Final check against RULES.md, report, submission | report draft | open |
| 17 | ⚪ | T13 | Immunity arm (stretch) | T08, T11 | open |
| 18 | ⚪ | SETUP-03 | Add `PENDING.md` and `LASTCONTEXT.md` to the required-files check in CI | none | open |

## Done

| ID | Task | Closed in |
|---|---|---|
| SETUP-00 | Project scaffold (README, AGENTS, CI, PR template, docs) | PR #1 |
| SETUP-05 | `PENDING.md` and `LASTCONTEXT.md` handoff files and session rules | PR #3 |
| SETUP-07 | Local `.env` created from `.env.example` (git-ignored); `.gitignore` and `.env.example` already existed | local only, no commit |
| SETUP-01 | Rules and talks digest on `main` (PR #2 had been merged into the scaffold branch after PR #1, so it never reached `main`) | branch `docs/project-docs` |
| SETUP-06 | Project docs (`PROJECT`, `EXPERIMENT_DESIGN`, `ARCHITECTURE`, `PLAN`, `TASKS`, `REPORT_OUTLINE`, prompts) added to `docs/` | branch `docs/project-docs` |
| T00 | Verify the external stack and write `docs/VERIFICATION.md` | branch `docs/verify-external-stack` |
| REPORT-05 | Prior work named; `docs/hackathon/PRIOR_WORK_DIGEST.md` written, README pre-existing table filled, references restored | branch `docs/prior-work` |
| SETUP-11 | Multi-agent rule in `AGENTS.md`: check branch and worktrees first, assume nothing, one worktree and branch per task | branch `docs/multi-agent-rule` |
| SETUP-13 | Rule in `AGENTS.md`: every PR is based on `main`, no stacked PRs | branch `docs/pr-base-main-rule` |
| SETUP-14 | Content of stacked PRs #6 to #10 brought to `main` | PR #11 |
| SETUP-12 | Removed the Discord, help-desk and survey `TODO(link)` rows from the README links table (SETUP-04 dropped) | branch `docs/readme-remove-todo-links` |
| SETUP-09 | `PRIOR_WORK_DIGEST.md` references removed; `.env.example` reduced to Adaption, Vertex, Muse and Modal plus per-provider budget caps | branch `chore/env-prior-work` |
| SETUP-08 | Project context section (hard invariants, claims policy) appended to `AGENTS.md` | PR #4 |
