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

Task IDs T01 to T15 are defined in `docs/TASKS.md`. Status below supersedes previous handoffs. Times use Argentina time (ART).

| Light | ID | Task | Current state |
|---|---|---|---|
| 🔴 | T07 | Pilot execution and Gate G2 | Calibrated prompt (priority + wording B) verified in isolated API calls; run 3 pilot seeds on Adaption gemma-4-31b-it; verify >= 30% breach |
| 🔴 | T08 | Preregistration and human tag | Run swarmlab prereg to generate experiments/PREREGISTRATION.md with SHA-256 hashes; request human git tag prereg-v1 |
| 🟡 | T10 | TRAIN and reported runs | TRAIN (15 seeds), A0 (controls), A1 (free flow ring & complete), A3 (online gating D1, D2, D3, D5), A3c (costs). Freeze at Monday 05:00 ART |
| 🟡 | T11 | Analysis and figures | Run swarmlab analyze, export plots, execute render_results.py and export_latex_tables.py |
| 🟢 | T15 | Report compilation and submission | Merge DRAFT_REPORT.md and LIMITATIONS_AND_ETHICS.md, populate measured numbers, export final PDF report |
| ⚪ | SETUP-03 | Require context files in CI | Open |

Human decisions recorded: Muse cap USD 20, Vertex cap USD 20, Adaption operational cap 500 credits; use Adaption for primary load; playbooks remain outside git; coordinator opens pending PRs after review and green CI, human merges each. These are configuration decisions, not experimental measurements.

## PRs Open (Human Review and Merge)

| PR | Branch | Contents | CI |
|---|---|---|---|
| #34 | feat/detector-verifiers | D4 micro-verifiers cascade and veto gate; 11 tests passed | green |
| #35 | docs/ethical-appendix | Limitations and dual-use ethical considerations appendix | green |
| #36 | feat/latex-tables | LaTeX table export utility for analysis CSVs; 7 tests passed | green |
| #37 | docs/reproduction-guide | Technical reproduction guide and verification tests; 6 tests passed | green |
| #38 | feat/detector-immunity | Swarm collective immunity tracker and kinetics; 12 tests passed | green |
| #39 | docs/report-draft | Academic report draft sections 1 to 6 (651 lines) | green |

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
