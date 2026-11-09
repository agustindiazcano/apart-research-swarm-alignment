# PENDING

Prioritized list of open tasks. Read this at the start of every session, together with `LASTCONTEXT.md`. Update it after every finished task (see `AGENTS.md`, "Session protocol").

Last updated: 2026-11-09

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

Task IDs T01 to T15 are defined in `docs/TASKS.md`. Status below supersedes previous handoffs. Times use Argentina time (ART).

| Light | ID | Task | Current state |
|---|---|---|---|
| 🟢 | SUBMIT-01 | Optional Wave 3 seed expansion | Wave 1 + Wave 2 complete (60 `TEST` episodes + 15 `TRAIN` + 3 `Pilot` = 78 real episodes across all 14 cells), analyzed, rendered, and compiled to `report/SWARM_CONTAGION_REPORT.pdf` (6/6 submission checks passing). Additional paired seeds can be appended before Monday 07:00 ART |

Human decisions recorded: Muse cap USD 20, Vertex cap USD 20, Adaption operational cap 500 credits; use Adaption for primary load; playbooks remain outside git; coordinator opens and merges PRs after green CI under user delegation. These are configuration decisions, not experimental measurements.

## PRs Open (Human Review and Merge)

| PR | Branch | Contents | CI |
|---|---|---|---|
| TBD | feat/campaign-wave2 | Expand `TEST` campaign to 60 episodes (`Wave 1 + Wave 2`), re-score `A2`, re-render all tables and publication figures, and recompile `report/SWARM_CONTAGION_REPORT.pdf` | pending |

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
| BUILD-02 | CLI runtime, training and analysis integration | PR #33 |
| T07 | Pilot execution and Gate G2 validation on seeds 901, 902, 903 | PR #41 |
| SETUP-03 | Automated repository hygiene and context checks in CI | PR #45 |
| T14 | Results render manifest and table rendering pipeline | PR #44 |
| T08 | Preregistration manifest freeze and rate-limit backoff resilience (`prereg-v1`) | PR #51 |
| T10 | `TRAIN` (15 episodes), detector threshold calibration (`D1`, `D2`, `D3`, `D5`), and balanced `TEST` campaign across `A0`, `A1`, `A2`, `A3`, `A3c` | PR #55 |
| T11 | Deterministic analysis, 100-message intent-content audit, publication figures, and SHA-256 rendered tables | PR #55 |
| T15 | Report compilation, LaTeX export, `report/SWARM_CONTAGION_REPORT.pdf` generation (6 main body pages), and 6/6 submission package verification | PR #55 |
